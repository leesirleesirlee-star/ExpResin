"""ExpResin 模板填充（template_fill_v1）。

把「识别结果 + 原始文件 + 实验元数据 + 引擎复算」组织成老师提供的三套实验模板
（Batch / Column / Electrochemical），供 template_export 导出 Excel。

数据来源与口径（重要）：
  - B 区逐行数据**从 Raw 原始文件重读**：识别快照只含列映射，不存数据值；
  - 浓度优先取引擎复算值（canonical.rows 的 conc_mg_l_computed，按「块 + Excel 行号」对齐），
    缺失时回退原始表记录值，实际口径写入 provenance.fills；
  - C 区派生量由 derive.py 计算，输入不足时带 reason（绝不臆造）；
  - A 区元数据来自实验前表单 / 识别元数据，缺失留空。

单位约定：
  内部统一 时间=秒、浓度=mg/L（derive 约定）；
  B/C 区输出按模板声明的单位换算（batch/column 时间用 min，electrochemical 用 s）。
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import openpyxl

from canonical import _field_columns, _locate, _read_column, _sheet_of, _to_float
from derive import DERIVE_VERSION, derive_all
from l1_structure import parse_sheet

FILL_VERSION = "template_fill_v1"

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "config" / "templates"
TEMPLATE_FILES = {
    "batch": "batch_template_v1.json",
    "column": "column_template_v1.json",
    "electrochemical": "electrochemical_template_v1.json",
}

# 不参与 B 区时序数据的块类型（标定表/容量汇总表不是测量序列）
EXCLUDED_KINDS = {"calibration", "capacity"}

# 模板 B 区「角色」→ 识别字段候选名（按优先级）
FIELD_CANDIDATES: dict[str, list[str]] = {
    "time": ["contact_time", "time", "run_time", "elapsed_time"],
    "concentration": ["concentration_mg_l", "concentration_ppm"],
    "ph": ["ph", "effluent_ph"],
    "potential": ["potential_v", "voltage_v", "potential"],
    "current": ["current_a", "current"],
}

# 时间单位 → 秒
_TIME_FACTORS = {
    "s": 1.0,
    "sec": 1.0,
    "secs": 1.0,
    "second": 1.0,
    "seconds": 1.0,
    "min": 60.0,
    "mins": 60.0,
    "minute": 60.0,
    "minutes": 60.0,
    "h": 3600.0,
    "hr": 3600.0,
    "hour": 3600.0,
    "hours": 3600.0,
    "d": 86400.0,
    "day": 86400.0,
    "days": 86400.0,
}

# A 区元数据候选键（模板 from: ["meta.xxx"] → 实际 metadata 别名）
META_ALIASES: dict[str, list[str]] = {
    "experiment_id": ["experiment_id", "id"],
    "date_start": ["date_start", "date", "experiment_date"],
    "date": ["date", "date_start"],
    "operator": ["operator", "researcher", "experimenter"],
    "researcher": ["researcher", "operator"],
    "resin_type": ["resin_type", "adsorbent", "material"],
    "adsorbent": ["adsorbent", "resin_type", "material"],
    "target_analyte": ["target_analyte", "analyte", "adsorbate", "target"],
    "adsorbate": ["adsorbate", "target_analyte", "analyte", "target"],
    "initial_concentration": ["initial_concentration", "c0", "influent_concentration"],
    "solution_volume": ["solution_volume", "solution_volume_ml", "volume_ml", "volume"],
    "resin_mass": ["resin_mass", "resin_mass_mg", "adsorbent_mass", "mass_mg"],
    "adsorbent_mass": ["adsorbent_mass", "resin_mass", "resin_mass_mg", "mass_mg"],
    "temperature": ["temperature", "temp"],
    "objective": ["objective", "purpose", "experiment_objective"],
    "matrix": ["matrix", "background"],
    "flow_rate": ["flow_rate", "flowrate", "flow_ml_min"],
    "bed_volume": ["bed_volume", "bed_volume_ml", "bv"],
    "bed_volume_ml": ["bed_volume_ml", "bed_volume", "bv"],
    "flow_direction": ["flow_direction", "direction"],
    "technique": ["technique", "method"],
    "working_electrode": ["working_electrode", "we"],
    "reference_electrode": ["reference_electrode", "re"],
    "counter_electrode": ["counter_electrode", "ce"],
    "electrolyte": ["electrolyte", "supporting_electrolyte"],
    "cell_configuration": ["cell_configuration", "cell"],
    "electrode_area": ["electrode_area", "area_cm2", "electrode_area_cm2"],
}


# --------------------------------------------------------------------------- #
# 模板加载
# --------------------------------------------------------------------------- #


def load_template(experiment_type: str) -> dict:
    """按实验类型加载模板配置；未知类型抛 ValueError（由调用方决定如何提示）。"""
    key = (experiment_type or "").strip().lower()
    filename = TEMPLATE_FILES.get(key)
    if filename is None:
        raise ValueError(f"未知实验类型：{experiment_type!r}（可选：{', '.join(TEMPLATE_FILES)}）")
    with open(TEMPLATE_DIR / filename, encoding="utf-8") as fp:
        return json.load(fp)


def _section(template: dict, section_id: str) -> dict | None:
    return next((s for s in template.get("sections") or [] if s.get("id") == section_id), None)


# --------------------------------------------------------------------------- #
# 元数据取值
# --------------------------------------------------------------------------- #


def _normalize_metadata(metadata: dict | None) -> dict[str, Any]:
    """兼容两种元数据结构，归一化为 {key: value}：

    1) 扁平 `{key: value}`（如 services.build_processed 的 flat_meta）；
    2) 嵌套 `{sheet_id: {key: {label, value, unit}}}`（processed.metadata 原样）。
    """
    out: dict[str, Any] = {}
    if not metadata:
        return out
    for key, value in metadata.items():
        if isinstance(value, dict) and "value" not in value:
            for sub_key, sub_value in value.items():
                leaf = sub_value.get("value") if isinstance(sub_value, dict) else sub_value
                if leaf not in (None, "") and sub_key not in out:
                    out[sub_key] = leaf
        else:
            leaf = value.get("value") if isinstance(value, dict) else value
            if leaf not in (None, "") and key not in out:
                out[key] = leaf
    return out


def _pick_text(normalized: dict, key: str) -> Any:
    """按别名顺序取元数据原值（保留字符串形态，不做数值转换）。"""
    for alias in META_ALIASES.get(key, [key]):
        value = normalized.get(alias)
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return value
    return None


def _meta_context(normalized: dict) -> dict:
    """derive 需要的数值型上下文。"""
    def num(key: str) -> float | None:
        return _to_float(_pick_text(normalized, key))

    return {
        "initial_concentration": num("initial_concentration"),
        "solution_volume": num("solution_volume"),
        "resin_mass": num("resin_mass"),
        "bed_volume": num("bed_volume"),
        "flow_rate": num("flow_rate"),
        "electrode_area": num("electrode_area"),
    }


# --------------------------------------------------------------------------- #
# 块分组（多离子 → 多 sheet）
# --------------------------------------------------------------------------- #


def _blocks_of(recognized: dict | None) -> list[dict]:
    """把识别快照摊平为 [{region_id, region_title, block}]，排除标定/容量块。"""
    out: list[dict] = []
    for region in (recognized or {}).get("regions") or []:
        for block in region.get("blocks") or []:
            if (block.get("kind") or "").strip().lower() in EXCLUDED_KINDS:
                continue
            if block.get("degraded"):
                continue
            out.append(
                {
                    "region_id": region.get("id"),
                    "region_title": region.get("title"),
                    "block": block,
                }
            )
    return out


def _group_by_analyte(items: list[dict]) -> list[tuple[str | None, str | None, list[dict]]]:
    """按目标离子分组，保持首次出现顺序（多离子 → 多个 Excel sheet）。

    返回 [(分组键, 展示名, items)]：分组键大写仅用于合并大小写变体，
    展示名一律保留原始表写法（"Cl" 不写成 "CL"）。
    """
    groups: dict[str | None, list[dict]] = {}
    display: dict[str | None, str | None] = {}
    for item in items:
        raw = (item["block"].get("analyte") or "").strip()
        key = raw.upper() or None
        groups.setdefault(key, []).append(item)
        display.setdefault(key, raw or None)
    return [(key, display[key], groups[key]) for key in groups]


# --------------------------------------------------------------------------- #
# B 区数据（从 Raw 重读）
# --------------------------------------------------------------------------- #


def _read_series(
    items: list[dict], raw_path: str | Path
) -> tuple[dict[str, dict[int, dict]], dict[str, str | None], list[str]]:
    """读取一组的列数据。

    返回 ({field: {excel_row: {"value": v, "block": block_id}}}, {field: 单位文本}, notes)
    """
    series: dict[str, dict[int, dict]] = {}
    units: dict[str, str | None] = {}
    notes: list[str] = []

    sheets_needed = {_sheet_of(i["region_id"]) for i in items if i.get("region_id")}
    workbook = openpyxl.load_workbook(Path(raw_path), data_only=True)
    try:
        structures: dict[str, tuple[Any, Any]] = {}
        for index, ws in enumerate(workbook.worksheets):
            name = ws.title.strip()
            if name in sheets_needed:
                structures[name] = (ws, parse_sheet(ws, index))

        for item in items:
            region_id = item.get("region_id")
            block = item.get("block") or {}
            sheet_name = _sheet_of(region_id)
            entry = structures.get(sheet_name)
            if entry is None:
                notes.append(f"工作表 {sheet_name} 未在 Raw 文件中找到，跳过块 {block.get('id')}")
                continue
            ws, structure = entry
            l1_regions = {r.region_id: r for r in structure.regions}
            located = _locate(ws, l1_regions, region_id, block)
            if located is None:
                notes.append(f"块 {block.get('id')} 未能在 Raw 中定位，跳过")
                continue
            l1_region, _l1_block, indices = located
            for field, letter in _field_columns(block).items():
                index = indices.get(letter)
                if index is None:
                    continue
                values = _read_column(ws, index, l1_region.data_start_row, l1_region.data_end_row)
                bucket = series.setdefault(field, {})
                for offset, value in enumerate(values):
                    if value is None or value == "":
                        continue
                    bucket[l1_region.data_start_row + offset] = {
                        "value": value,
                        "block": block.get("id"),
                    }
                if field not in units:
                    unit = None
                    for col in block.get("columns") or []:
                        if (col.get("field") or col.get("target")) == field:
                            unit = col.get("unit") or col.get("raw")
                            break
                    units[field] = unit
        return series, units, notes
    finally:
        workbook.close()


def _first_field(series: dict[str, dict[int, dict]], role: str) -> str | None:
    for name in FIELD_CANDIDATES.get(role, []):
        if series.get(name):
            return name
    return None


def _time_unit_token(unit_text: str | None) -> str | None:
    """从单位文本提取已知的时间单位词（不猜测，只认词表命中）。

    可识别形态：`min` / `Time (min)` / `time,min` / `time/h` / `time/s`。
    """
    if not unit_text:
        return None
    text = str(unit_text).strip().lower()
    if text in _TIME_FACTORS:
        return text
    for token in re.split(r"[()\[\],;/\s]+", text):
        if token in _TIME_FACTORS:
            return token
    return None


def _time_factor(unit_text: str | None) -> float | None:
    """单位文本 → 秒的换算系数；无法识别返回 None（由调用方降级并提示）。"""
    token = _time_unit_token(unit_text)
    return _TIME_FACTORS[token] if token else None


def _engine_conc_index(canonical: dict | None) -> dict[tuple[str, int], float]:
    """引擎复算浓度索引：{(block_id, excel_row): mg/L}。"""
    index: dict[tuple[str, int], float] = {}
    for row in (canonical or {}).get("rows") or []:
        value = row.get("conc_mg_l_computed")
        if value is None:
            continue
        try:
            index[(row.get("block"), int(row.get("row_index")))] = float(value)
        except (TypeError, ValueError):
            continue
    return index


# --------------------------------------------------------------------------- #
# 主入口
# --------------------------------------------------------------------------- #


def build_template_data(
    *,
    experiment_type: str,
    recognized: dict | None,
    raw_path: str | Path,
    experiment_id: str,
    metadata: dict | None = None,
    canonical: dict | None = None,
) -> dict:
    """生成模板填充结果（尚未导出为 Excel）。"""
    template = load_template(experiment_type)
    items = _blocks_of(recognized)
    groups = _group_by_analyte(items)
    engine_conc = _engine_conc_index(canonical)
    normalized_meta = _normalize_metadata(metadata)
    meta_ctx = _meta_context(normalized_meta)

    fills: dict[str, str] = {}
    sheets: list[dict] = []
    global_notes: list[str] = []

    if not groups:
        global_notes.append("未找到可用于模板填充的测量块（标定/容量块不参与 B 区）")

    for _analyte_key, analyte, group_items in groups:
        sheet, sheet_notes = _fill_group(
            template=template,
            experiment_type=experiment_type,
            analyze=analyte,
            group_items=group_items,
            raw_path=raw_path,
            experiment_id=experiment_id,
            metadata=normalized_meta,
            meta_ctx=meta_ctx,
            engine_conc=engine_conc,
            fills=fills,
        )
        sheets.append(sheet)
        global_notes.extend(f"{analyte or '未知离子'}：{n}" for n in sheet_notes)

    return {
        "experiment_id": experiment_id,
        "experiment_type": template.get("experiment_type"),
        "template_id": template.get("template_id"),
        "template_title": template.get("title"),
        "template_version": template.get("version"),
        "fill_version": FILL_VERSION,
        "derive_version": DERIVE_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "rules": template.get("rules") or [],
        "sheets": sheets,
        "notes": global_notes,
        "provenance": {
            "raw_path": str(raw_path),
            "concentration_policy": (template.get("data_policy") or {}).get("concentration"),
            "fills": fills,
            "engine_rows": len((canonical or {}).get("rows") or []),
        },
    }


def _fill_group(
    *,
    template: dict,
    experiment_type: str,
    analyze: str | None,
    group_items: list[dict],
    raw_path: str | Path,
    experiment_id: str,
    metadata: dict | None,
    meta_ctx: dict,
    engine_conc: dict[tuple[str, int], float],
    fills: dict[str, str],
) -> tuple[dict, list[str]]:
    notes: list[str] = []
    series, units, read_notes = _read_series(group_items, raw_path)
    notes.extend(read_notes)

    # ---- 角色 → 数据字段 ----
    cols = _section(template, "B").get("columns") or []
    role_fields: dict[str, str | None] = {c.get("role"): _first_field(series, c.get("role")) for c in cols}
    for col in cols:
        if role_fields.get(col.get("role")) is None:
            notes.append(f"未在识别结果中找到「{col.get('label')}」对应的数据列，已留空")

    # ---- 统一行号 ----
    row_numbers = sorted({r for f in role_fields.values() if f for r in series.get(f, {})})

    # ---- 时间换算到秒（内部单位）----
    time_field = role_fields.get("time")
    time_unit_text = units.get(time_field)
    time_token = _time_unit_token(time_unit_text)
    time_factor = _TIME_FACTORS[time_token] if time_token else None
    time_unit_known = time_factor is not None
    if time_field and not time_unit_known:
        # 单位不明时按原值使用，并明确记录（不静默假设）
        time_factor = 1.0
        notes.append(f"时间列单位未能识别（{time_unit_text!r}），按原值处理且不做任何换算，请人工核对")
    elif time_token and str(time_unit_text).strip().lower() != time_token:
        # 单位是从复合表头里推断出来的（如 "time/h" → h），明确留痕
        notes.append(
            f"时间列单位由表头 {time_unit_text!r} 推断为 {time_token}（1 {time_token} = {time_factor:g} s）"
        )

    def raw_of(role: str, row_no: int) -> Any:
        field = role_fields.get(role)
        if not field:
            return None
        hit = series.get(field, {}).get(row_no)
        return hit.get("value") if hit else None

    def block_of(role: str, row_no: int) -> str | None:
        field = role_fields.get(role)
        if not field:
            return None
        hit = series.get(field, {}).get(row_no)
        return hit.get("block") if hit else None

    # ---- 浓度序列（引擎复算优先，回退原表记录值）----
    conc_series: list[float | None] = []
    time_values_s: list[float | None] = []
    ph_values: list[float | None] = []
    potential_values: list[float | None] = []
    current_values: list[float | None] = []

    # ppm 回退路径需要显式标注"稀水溶液 ≈ mg/L"假设（不静默等同）
    conc_field = role_fields.get("concentration") or ""
    reported_tag = "reported(ppm≈mg/L)" if "ppm" in conc_field else "reported"

    for row_no in row_numbers:
        t = _to_float(raw_of("time", row_no))
        time_values_s.append(None if t is None else t * time_factor)

        conc = None
        engine_hit = engine_conc.get((block_of("concentration", row_no), row_no))
        if engine_hit is not None:
            conc = engine_hit
            fills["concentration"] = "engine"
        else:
            raw_conc = _to_float(raw_of("concentration", row_no))
            if raw_conc is not None:
                conc = raw_conc
                fills.setdefault("concentration", reported_tag)
        conc_series.append(conc)

        ph_values.append(_to_float(raw_of("ph", row_no)))
        potential_values.append(_to_float(raw_of("potential", row_no)))
        current_values.append(_to_float(raw_of("current", row_no)))

    series_internal = {
        "time_s": time_values_s,
        "concentration_mg_l": conc_series,
        "ph": ph_values,
        "potential_v": potential_values,
        "current_a": current_values,
    }

    # ---- A 区 ----
    a_rows: list[dict] = []
    for field in (_section(template, "A") or {}).get("fields") or []:
        value = None
        for path in field.get("from") or []:
            if path.startswith("meta."):
                value = _pick_text(metadata, path.split(".", 1)[1])
            if value is not None:
                break
        if value is None and field.get("key") == "experiment_id":
            value = experiment_id
        a_rows.append(
            {"key": field.get("key"), "label": field.get("label"), "value": value, "unit": field.get("unit")}
        )

    # ---- B 区（按模板单位换算时间；输入单位未知时原样传递，不换算）----
    b_rows: list[list] = []
    time_col = next((c for c in cols if c.get("role") == "time"), None)
    out_factor = _time_factor(time_col.get("unit")) if time_col else None
    if not time_unit_known:
        out_factor = None
    for i, row_no in enumerate(row_numbers):
        row: list[Any] = []
        for col in cols:
            role = col.get("role")
            if role == "time":
                seconds = time_values_s[i]
                row.append(None if seconds is None else seconds / (out_factor or 1.0))
            elif role == "concentration":
                row.append(conc_series[i])
            elif role == "ph":
                row.append(ph_values[i])
            elif role == "potential":
                row.append(potential_values[i])
            elif role == "current":
                row.append(current_values[i])
            else:
                row.append(None)
        b_rows.append(row)

    # ---- C 区（派生计算）----
    derived = derive_all(experiment_type, series_internal, meta_ctx)
    c_rows: list[dict] = []
    for field in (_section(template, "C") or {}).get("fields") or []:
        item = derived.get(field.get("derive")) or {}
        value = item.get("value")
        # 时间类派生量：内部秒 → 模板单位
        if value is not None and item.get("unit") == "s":
            value = round(value / (out_factor or 1.0), 6)
        c_rows.append(
            {
                "key": field.get("key"),
                "label": field.get("label"),
                "value": value,
                "unit": field.get("unit") or item.get("unit"),
                "reason": item.get("reason"),
                "method": item.get("method"),
            }
        )

    sheet_name = (analyze or "Data")[:31]
    return (
        {
            "analyte": analyze,
            "sheet_name": sheet_name,
            "sections": {
                "A": {"label": (_section(template, "A") or {}).get("label"), "kind": "fields", "rows": a_rows},
                "B": {
                    "label": (_section(template, "B") or {}).get("label"),
                    "kind": "series",
                    "columns": [
                        {"key": c.get("key"), "label": c.get("label"), "unit": c.get("unit")} for c in cols
                    ],
                    "rows": b_rows,
                },
                "C": {"label": (_section(template, "C") or {}).get("label"), "kind": "derived", "rows": c_rows},
            },
            "row_count": len(b_rows),
        },
        notes,
    )
