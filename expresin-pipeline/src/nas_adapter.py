"""NAS 汇总适配器（nas_adapter_v1）。

导师要求：识别归档后的实验数据要"汇总到 NAS 服务器"。
当前阶段（NAS 连接信息未补齐）：本地目录镜像实现 + 远程适配器接口预留。

每个实验发布为一个目录：
    <NAS_ROOT>/<experiment_id>/
        raw/<原始文件名>     # 原始数据文件（只读副本）
        processed.json        # 规范文档（metadata + recognized + canonical）
        canonical.csv         # 规范长表（有数据行时）
        manifest.json         # 文件清单 + 校验值 + 发布时间（可追溯）

配置（环境变量，可写入根目录 .env 或进程环境）：
    NAS_MODE = local | smb | http   （默认 local）
    NAS_ROOT = 镜像根目录           （默认 expresin-pipeline/data/nas_mirror）
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


class _RemoteAdapterStub:
    """远程适配器占位：等待 NAS 连接信息（SMB / HTTP 等）后实现。"""

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
    return _RemoteAdapterStub(mode)
