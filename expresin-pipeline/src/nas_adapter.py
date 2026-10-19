"""NAS 汇总适配器（nas_adapter_v1）。

导师要求：识别归档后的实验数据要"汇总到 NAS 服务器"。
实现：本地目录镜像（默认/过渡）+ SMB 直连（NAS_MODE=smb，smbprotocol）+ 其余远程模式接口预留。

每个实验发布为一个目录：
    <NAS_ROOT>/<experiment_id>/
        raw/<原始文件名>     # 原始数据文件（只读副本）
        processed.json        # 规范文档（metadata + recognized + canonical）
        canonical.csv         # 规范长表（有数据行时）
        manifest.json         # 文件清单 + 校验值 + 发布时间（可追溯）

配置（环境变量，可写入根目录 .env 或进程环境）：
    NAS_MODE = local | smb | http   （默认 local）
    NAS_ROOT = 镜像根目录           （默认 expresin-pipeline/data/nas_mirror）

过渡路径（NAS 连接信息未补齐时）：
    - NAS_MODE=local + NAS_ROOT 指向已映射的盘符或 UNC 路径（如 Z:/share 或
      \\\\192.168.x.x\\share）即可让 LocalDirAdapter 直接写局域网共享；
      Windows 需先 net use 映射或保证进程账号对 UNC 有写权限。
    - NAS_MODE=smb 走 smbprotocol 直连（见 SmbAdapter），不依赖系统映射。
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

DEFAULT_ROOT = Path(__file__).resolve().parent.parent / "data" / "nas_mirror"
ADAPTER_VERSION = "nas_adapter_v1"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fp:
        for chunk in iter(lambda: fp.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


class NasAdapter(Protocol):
    """NAS 发布适配器接口。NAS 信息补齐后新增远程实现（SMB / HTTP / rsync）。"""

    def publish_experiment(
        self,
        experiment_id: str,
        *,
        raw_path: Path | None = None,
        raw_name: str | None = None,
        processed: dict | None = None,
    ) -> dict:
        ...


class LocalDirAdapter:
    """本地目录镜像：把实验产物复制/写入 NAS_ROOT/<experiment_id>/。"""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    def publish_experiment(
        self,
        experiment_id: str,
        *,
        raw_path: Path | None = None,
        raw_name: str | None = None,
        processed: dict | None = None,
    ) -> dict:
        target = self.root / experiment_id
        target.mkdir(parents=True, exist_ok=True)
        files: list[dict[str, Any]] = []

        if raw_path is not None and Path(raw_path).exists():
            raw_target = target / "raw" / (raw_name or Path(raw_path).name)
            raw_target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(raw_path, raw_target)
            files.append(
                {"path": f"raw/{raw_target.name}", "size": raw_target.stat().st_size, "sha256": _sha256(raw_target)}
            )

        if processed is not None:
            processed_target = target / "processed.json"
            processed_target.write_text(
                json.dumps(processed, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            files.append(
                {"path": "processed.json", "size": processed_target.stat().st_size, "sha256": _sha256(processed_target)}
            )

            canonical = (processed or {}).get("canonical") or {}
            if canonical.get("rows"):
                from canonical import render_csv  # 局部导入，避免 server 侧循环依赖

                csv_target = target / "canonical.csv"
                csv_target.write_text(render_csv(canonical), encoding="utf-8")
                files.append(
                    {"path": "canonical.csv", "size": csv_target.stat().st_size, "sha256": _sha256(csv_target)}
                )

        manifest = {
            "adapter_version": ADAPTER_VERSION,
            "adapter": "local",
            "experiment_id": experiment_id,
            "published_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "files": files,
        }
        (target / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return manifest


class SmbAdapter:
    """SMB 远程发布（NAS_MODE=smb）：经 smbprotocol 直连，无需系统映射盘。

    每个实验发布为 <server>/<share>/<path_prefix>/<experiment_id>/ 目录，
    目录结构与 manifest 格式与 LocalDirAdapter 完全一致。

    环境变量：
        NAS_SMB_SERVER       服务器主机名或 IP（必填）
        NAS_SMB_SHARE        共享名（必填）
        NAS_SMB_USERNAME     账号（可空，匿名/来客共享时留空）
        NAS_SMB_PASSWORD     密码（可空）
        NAS_SMB_PORT         端口（默认 445）
        NAS_SMB_PATH_PREFIX  共享内子目录前缀（默认 ""）

    依赖：pip install smbprotocol；未安装时抛出带安装提示的 RuntimeError。
    注意：尚未在真实 NAS 上联调（连接信息待补），目录写入语义与本地镜像对齐。
    """

    def __init__(
        self,
        server: str,
        share: str,
        *,
        username: str | None = None,
        password: str | None = None,
        port: int = 445,
        path_prefix: str = "",
    ) -> None:
        self.server = server
        self.share = share
        self.username = username or None
        self.password = password or None
        self.port = port
        self.path_prefix = path_prefix.strip("/\\")

    def _unc(self, *parts: str) -> str:
        return "\\\\" + "\\".join(
            p.replace("/", "\\")
            for p in (self.server, self.share, self.path_prefix, *parts)
            if p
        )

    def publish_experiment(
        self,
        experiment_id: str,
        *,
        raw_path: Path | None = None,
        raw_name: str | None = None,
        processed: dict | None = None,
    ) -> dict:
        try:
            import smbclient
        except ImportError as exc:
            raise RuntimeError(
                "NAS_MODE=smb 需要 smbprotocol 依赖：pip install smbprotocol"
            ) from exc

        smbclient.register_session(
            self.server, username=self.username, password=self.password, port=self.port
        )
        target = self._unc(experiment_id)
        smbclient.makedirs(target, exist_ok=True)

        files: list[dict[str, Any]] = []

        def _write(rel: str, data: bytes) -> None:
            dest = self._unc(experiment_id, rel.replace("/", "\\"))
            parent = dest.rsplit("\\", 1)[0]
            if parent != target:
                smbclient.makedirs(parent, exist_ok=True)
            with smbclient.open_file(dest, mode="wb") as fp:
                fp.write(data)
            files.append(
                {"path": rel, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()}
            )

        if raw_path is not None and Path(raw_path).exists():
            _write(f"raw/{raw_name or Path(raw_path).name}", Path(raw_path).read_bytes())

        if processed is not None:
            _write(
                "processed.json",
                json.dumps(processed, ensure_ascii=False, indent=2).encode("utf-8"),
            )
            canonical = (processed or {}).get("canonical") or {}
            if canonical.get("rows"):
                from canonical import render_csv  # 局部导入，避免 server 侧循环依赖

                _write("canonical.csv", render_csv(canonical).encode("utf-8"))

        manifest = {
            "adapter_version": ADAPTER_VERSION,
            "adapter": "smb",
            "server": self.server,
            "share": self.share,
            "path_prefix": self.path_prefix,
            "experiment_id": experiment_id,
            "published_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "files": files,
        }
        _write("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8"))
        return manifest


class _RemoteAdapterStub:
    """远程适配器占位：等待 NAS 连接信息（HTTP / rsync 等）后实现。"""

    def __init__(self, mode: str) -> None:
        self.mode = mode

    def publish_experiment(self, *args: Any, **kwargs: Any) -> dict:
        raise NotImplementedError(f"NAS_MODE={self.mode} 远程适配器尚未实现（等待 NAS 配置补齐）")


def get_adapter() -> NasAdapter:
    """按环境变量选择适配器；未配置时使用本地目录镜像。"""
    mode = (os.environ.get("NAS_MODE") or "local").strip().lower()
    if mode == "local":
        root = os.environ.get("NAS_ROOT") or str(DEFAULT_ROOT)
        return LocalDirAdapter(Path(root))
    if mode == "smb":
        server = (os.environ.get("NAS_SMB_SERVER") or "").strip()
        share = (os.environ.get("NAS_SMB_SHARE") or "").strip()
        if not server or not share:
            raise RuntimeError("NAS_MODE=smb 需要配置 NAS_SMB_SERVER 与 NAS_SMB_SHARE")
        return SmbAdapter(
            server,
            share,
            username=os.environ.get("NAS_SMB_USERNAME"),
            password=os.environ.get("NAS_SMB_PASSWORD"),
            port=int(os.environ.get("NAS_SMB_PORT") or "445"),
            path_prefix=os.environ.get("NAS_SMB_PATH_PREFIX") or "",
        )
    return _RemoteAdapterStub(mode)
