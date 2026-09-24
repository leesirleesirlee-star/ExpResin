"""在真实 Excel 上运行 L1 -> L3/L4/L5 完整映射链路，输出结果与成本统计。

用法:
    python expresin-pipeline/scripts/run_mapping.py [sheet_name ...]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "expresin-pipeline" / "src"))

from l1_structure import parse_workbook  # noqa: E402
from llm import LLMClient, LLMConfig  # noqa: E402
from mapping import load_schema, map_block, mapping_to_dict, validate_mapping  # noqa: E402

WORKSPACE = ROOT
OUT_DIR = WORKSPACE / ".deepworks" / "tmp"
XLSX = WORKSPACE / "20250528 DHT Cl SO4.xlsx"
SCHEMA_PATH = WORKSPACE / "expresin-pipeline" / "config" / "standard_schema.json"

DEFAULT_SHEETS = ["0305-600"]


def main() -> None:
    targets = sys.argv[1:] or DEFAULT_SHEETS

    schema = load_schema(SCHEMA_PATH)
    workbook = parse_workbook(XLSX)
    sheet_map = {s.sheet_name.strip(): s for s in workbook.sheets}

    config = LLMConfig.from_env(WORKSPACE / ".env")
    results = []
    lines = []

    with LLMClient(config) as client:
        for name in targets:
            sheet = sheet_map.get(name.strip())
            if not sheet:
                print(f"跳过：未找到 Sheet {name!r}")
                continue
            lines.append("=" * 92)
            lines.append(f"SHEET [{sheet.sheet_name}] regions={sheet.region_count}")
            for region in sheet.regions:
                for block in region.col_blocks:
                    mapping = map_block(client, block, region, schema, sheet.sheet_name)
                    issues = validate_mapping(mapping, block, schema)
                    record = mapping_to_dict(mapping)
                    record["issues"] = issues
                    record["region_kind_hint"] = region.region_kind
                    record["region_title"] = region.title
                    results.append(record)

                    lines.append("-" * 92)
                    lines.append(
                        f"[{block.block_id}] kind={mapping.block_kind} "
                        f"({mapping.block_kind_confidence:.2f}) analyte={mapping.analyte} "
                        f"region_hint={region.region_kind}"
                    )
                    for cm in mapping.columns:
                        block_col = next(
                            (c for c in block.columns if c.col_letter == cm.col_letter), None
                        )
                        header = block_col.raw_header if block_col else "?"
                        flag = "!" if cm.confidence < 0.8 else " "
                        lines.append(
                            f"  {flag} {cm.col_letter}: {header!r:28} -> "
                            f"{cm.target_field or '<未映射>':26} conf={cm.confidence:.2f}"
                        )
                    if issues:
                        lines.append(f"  ISSUES: {'; '.join(issues)}")
                    if mapping.trace_notes:
                        lines.append(f"  trace: {mapping.trace_notes[:160]}...")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "mapping_result.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT_DIR / "mapping_summary.txt").write_text("\n".join(lines), encoding="utf-8")

    total_tokens = sum(r["usage"].get("total_tokens", 0) for r in results)
    print(f"blocks mapped: {len(results)}")
    print(f"total tokens: {total_tokens}")
    print(f"WROTE {OUT_DIR / 'mapping_summary.txt'}")


if __name__ == "__main__":
    main()