"""把已归档实验（重新）发布到 NAS 镜像目录。

用途：归档时发布失败、NAS_ROOT 变更、或需要补发的历史实验。
默认使用本地目录镜像（NAS_MODE=local），远程适配器待 NAS 信息补齐后实现。

用法:
    python expresin-pipeline/scripts/publish_nas.py RES-20260929-003 [RES-... ...]
    python expresin-pipeline/scripts/publish_nas.py --all
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[2]
PIPELINE = ROOT / "expresin-pipeline"
for extra in (PIPELINE / "src", PIPELINE / "server"):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

from nas_adapter import get_adapter  # noqa: E402
from store import Store  # noqa: E402

DB_PATH = PIPELINE / "data" / "expresin.db"
RAW_DIR = PIPELINE / "data" / "raw"


def resolve_raw_file(store: Store, experiment: dict) -> tuple[Path | None, str | None]:
    """优先使用 raw 资产 payload.uri（新版 sha 前缀命名），并兼容旧版路径。"""
    session_id = experiment.get("session_id")
    raw_name = experiment.get("raw_file")
    raw_asset = store.latest_asset(session_id, "raw_file") if session_id else None
    if raw_asset and raw_asset.get("name"):
        raw_name = raw_asset["name"]

    candidates: list[Path] = []
    uri = ((raw_asset or {}).get("payload") or {}).get("uri")
    if uri:
        candidates.append(Path(uri))
    if session_id and raw_name:
        candidates.append(RAW_DIR / f"{session_id}__{raw_name}")

    raw_root = RAW_DIR.resolve()
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
            resolved.relative_to(raw_root)
        except (OSError, ValueError):
            continue
        if resolved.is_file():
            return resolved, raw_name
    return None, raw_name


def publish_one(store: Store, experiment_id: str) -> dict:
    experiment = store.get_experiment(experiment_id)
    if not experiment:
        return {"error": f"实验不存在：{experiment_id}"}

    raw_path, raw_name = resolve_raw_file(store, experiment)

    return get_adapter().publish_experiment(
        experiment_id,
        raw_path=raw_path,
        raw_name=raw_name,
        processed=experiment.get("processed") or {},
    )


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 1

    store = Store(DB_PATH)
    if argv[0] == "--all":
        targets = [item["id"] for item in store.list_experiments(limit=1000)]
    else:
        targets = argv

    failures = 0
    for experiment_id in targets:
        result = publish_one(store, experiment_id)
        if "files" in result:
            raw_label = "含 raw" if any(f["path"].startswith("raw/") for f in result["files"]) else "无 raw"
            print(f"{experiment_id}: OK（{len(result['files'])} 个文件，{raw_label}）-> {result['files'][0]['path'] if result['files'] else '—'}")
        else:
            failures += 1
            print(f"{experiment_id}: FAILED - {result.get('error')}")

    if failures:
        print(f"==== {failures}/{len(targets)} failed ====")
        return 1
    print(f"==== {len(targets)} published ====")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
