"""运行 L1 结构解析并输出 JSON 摘要（开发期验证脚本）。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from l1_structure import parse_workbook, summarize, to_dict  # noqa: E402

WORKSPACE = Path(__file__).resolve().parents[2]
OUT_DIR = WORKSPACE / ".deepworks" / "tmp"

FILES = ["materials/data/20250528 DHT Cl SO4.xlsx", "materials/data/2 Data for Figures.xlsx"]


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    collected = []
    summary_lines = []
    for name in FILES:
        path = WORKSPACE / name
        if not path.exists():
            print(f"SKIP (not found): {name}")
            continue
        structure = parse_workbook(path)
        collected.append(to_dict(structure))
        summary_lines.append(summarize(structure))

    out = OUT_DIR / "l1_output.json"
    out.write_text(json.dumps(collected, ensure_ascii=False, indent=2), encoding="utf-8")

    summary_path = OUT_DIR / "l1_summary.txt"
    summary_path.write_text("\n\n".join(summary_lines), encoding="utf-8")

    print(f"WROTE {out}")
    print(f"WROTE {summary_path}")


if __name__ == "__main__":
    main()