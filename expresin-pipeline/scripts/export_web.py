"""把 L1→L5 的真实分析结果导出为前端可消费的 JSON。

复用已缓存的 mapping_result.json（避免重复消耗 LLM 额度），
再用 L1 重新解析出的列样本值与标准 Schema，合并成 PortalJarvis 所需的结构。

用法:
    python expresin-pipeline/scripts/export_web.py [sheet_name ...]
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "expresin-pipeline" / "src"))

from l1_structure import parse_workbook  # noqa: E402
from mapping import load_schema  # noqa: E402

TMP = ROOT / ".deepworks" / "tmp"
OUT = ROOT / "expresin-portal" / "public" / "data" / "analysis.json"
XLSX = ROOT / "materials" / "data" / "20250528 DHT Cl SO4.xlsx"
SCHEMA_PATH = ROOT / "expresin-pipeline" / "config" / "standard_schema.json"

DEFAULT_SHEETS = ["0305-600", "0121", "0212", "0312-600", "0326-C104", "0512-C104", "0528-C104"]

KIND_LABELS = {
    "calibration": "标定曲线",
    "sample_measurement": "样品测量",
    "capacity": "交换容量",
    "ph_curve": "pH 曲线",
}

_NUM_RE = re.compile(r"^[+-]?\d+(\.\d+)?([eE][+-]?\d+)?$")


def fmt(value) -> str:
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def first_value(col) -> str:
    if col is None:
        return ""
    for v in col.sample_values:
        if v is None:
            continue
        s = fmt(v).strip()
        if s:
            return s
    return ""


def field_spec(schema: dict, kind: str, key: str | None) -> dict:
    spec = schema["block_kinds"].get(kind)
    if not spec or not key:
        return {}
    for f in spec["target_fields"]:
        if f["key"] == key:
            return f
    return {}


def ion_aliases(schema: dict) -> set[str]:
    spec = schema["block_kinds"].get("calibration", {})
    for f in spec.get("target_fields", []):
        if f["key"] == "analyte":
            return {a.lower() for a in f.get("aliases", [])}
    return set()


def main() -> None:
    sheets = sys.argv[1:] or DEFAULT_SHEETS

    records = json.loads((TMP / "mapping_result.json").read_text(encoding="utf-8"))
    by_block = {r["block_id"]: r for r in records}
    schema = load_schema(SCHEMA_PATH)
    aliases = ion_aliases(schema)
    workbook = parse_workbook(XLSX)
    sheet_map = {s.sheet_name.strip(): s for s in workbook.sheets}

    experiments = []
    total_cols = 0

    for name in sheets:
        sheet = sheet_map.get(name.strip())
        if sheet is None:
            print(f"跳过：未找到 Sheet {name!r}")
            continue

        regions_out = []
        for region in sheet.regions:
            blocks_out = []
            for block in region.col_blocks:
                rec = by_block.get(block.block_id)
                if rec is None:
                    continue
                kind = rec["block_kind"]

                cols_out = []
                for cm in rec["columns"]:
                    prof = next(
                        (c for c in block.columns if c.col_letter == cm["col_letter"]), None
                    )
                    raw = (prof.raw_header if prof else "") or ""
                    key = cm["target_field"]

                    if key:
                        label = field_spec(schema, kind, key).get("label") or key
                    elif not raw.strip():
                        label = None
                    elif raw.strip().lower() in aliases:
                        label = "离子标签列"
                    else:
                        label = "未映射"

                    cols_out.append(
                        {
                            "col": cm["col_letter"],
                            "raw": raw,
                            "target": key,
                            "field": label,
                            "value": first_value(prof),
                            "samples": [fmt(v) for v in (prof.sample_values[:4] if prof else [])],
                            "conf": round(float(cm["confidence"]), 2),
                            "unit": prof.unit if prof else None,
                            "unitStd": field_spec(schema, kind, key).get("unit"),
                            "evidence": cm["evidence"],
                        }
                    )

                total_cols += len(cols_out)
                blocks_out.append(
                    {
                        "id": block.block_id,
                        "kind": kind,
                        "analyte": rec["analyte"],
                        "confidence": round(float(rec["block_kind_confidence"]), 2),
                        "columns": cols_out,
                    }
                )

            if not blocks_out:
                continue

            kind_label = KIND_LABELS.get(blocks_out[0]["kind"], blocks_out[0]["kind"])
            regions_out.append(
                {
                    "id": region.region_id,
                    "title": region.title or "",
                    "kind": blocks_out[0]["kind"],
                    "kindLabel": kind_label,
                    "headerRows": region.header_rows,
                    "rowCount": region.row_count,
                    "blocks": blocks_out,
                }
            )

        if not regions_out:
            continue

        experiments.append(
            {
                "id": f"DHT-{sheet.sheet_name.strip()}",
                "project": "DHT 动态离子交换",
                "sourceFile": XLSX.name,
                "sheet": sheet.sheet_name.strip(),
                "status": "reviewing",
                "lastSaved": "尚未保存",
                "regions": regions_out,
            }
        )

    payload = {
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "source": {
            "file": XLSX.name,
            "sheets": [e["sheet"] for e in experiments],
            "pipeline": "L1 结构解析 → L3/L4 LLM 语义映射 → L5 规则校验",
        },
        "experiments": experiments,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # 同步模板 Schema 给前端（单一数据源：config/experiment_template_v1.json）
    tpl_src = ROOT / "expresin-pipeline" / "config" / "experiment_template_v1.json"
    tpl_dst = OUT.parent / "experiment_template_v1.json"
    tpl_dst.write_text(tpl_src.read_text(encoding="utf-8"), encoding="utf-8")

    blocks = sum(len(r["blocks"]) for e in experiments for r in e["regions"])
    print(f"experiments={len(experiments)} blocks={blocks} columns={total_cols}")
    print(f"WROTE {OUT}")


if __name__ == "__main__":
    main()