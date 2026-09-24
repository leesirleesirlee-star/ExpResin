"""ExpResin 规范表格构建（W7：规范表格）。

职责：
  1. 从 Raw 原始文件重读**完整数值列**（L1 画像只保留 5 个样本值，不足以计算）；
  2. 用识别快照提供的字段语义（calibration / sample_measurement 等）对齐列；
  3. 调用 compute.py 完成标定拟合、浓度反算、单位换算与交叉验证；
  4. 产出**规格化长表**（一行一个观测），可直接转 CSV / Markdown / 入库。

标定归属（重要）：
  真实实验表里通常**没有**声明"某样本块使用哪条标定曲线"。本模块因此：
    - 对同工作表、同分析物的**所有候选标定曲线**分别复算；
    - 选与表内自算值平均偏差最小的作为 primary（selection_method="best_agreement"）；
    - 把全部候选的偏差写入 calculations，供人工核验；
    - 若样本信号超出所选标定的标定范围，行上标注 extrapolated=True。
  绝不把这一推断伪装成原始记录。

科学不变量：
  - 只读 Raw，不写 Raw；
  - 每一行都带 `row_index`（Excel 原始行号）、`calibration_block` 与 `method`，可回溯核对；
  - 输入不足的量（容量/去除率）标注原因，绝不填猜测值。
"""

from __future__ import annotations

import csv
import io
import re
from pathlib import Path
from typing import Any

import openpyxl

from compute import (
    CALCULATION_VERSION,
    DILUTE_AQUEOUS_ASSUMPTION,
    adsorption_capacity_mg_g,
    canonical_ion,
    linear_fit,
    median,
    mg_l_to_mol_l,
    molar_mass,
    relative_deviation,
    removal_rate,
    summarize_deviations,
)
from l1_structure import parse_sheet

CANONICAL_SCHEMA = "canonical_table_v1"

# 规范长表的固定列（顺序稳定，便于后续 Evidence Package / 推送复用）
CANONICAL_COLUMNS: list[str] = [
    "experiment_id",
    "sheet",
    "region",
    "block",
    "kind",
    "analyte",
    "row_index",
    "sample_number",
    "bed_volume",
    "volume_ml",
    "signal_area",
    "dilution_factor",
    "conc_ppm_reported",
    "conc_ppm_computed",
    "conc_mg_l_computed",
    "conc_mol_reported",
    "conc_mol_computed",
    "conc_mol_computed_diluted",
    "deviation_ppm",
    "removal_rate",
    "calibration_block",
    "extrapolated",
    "method",
    "confidence",
    "source",
]

# 字段语义 -> 长表列名
_FIELD_TO_COLUMN: dict[str, str] = {
    "sample_number": "sample_number",
    "bed_volume": "bed_volume",
    "volume": "volume_ml",
    "signal_area": "signal_area",
    "corrected_area": "signal_area",
    "concentration_ppm": "conc_ppm_reported",
    "concentration_mol": "conc_mol_reported",
}

# 元数据中可能承载"容量/去除率"所需输入的键（找不到就不算，不猜）
_META_KEYS: dict[str, list[str]] = {
    "initial_concentration": ["initial_concentration", "c0", "inlet_concentration", "初始浓度"],
    "equilibrium_concentration": ["equilibrium_concentration", "ce", "平衡浓度"],
    "solution_volume_ml": ["solution_volume", "volume_ml", "solution_volume_ml", "溶液体积"],
    "resin_mass_mg": ["resin_mass", "resin_mass_mg", "mass", "树脂质量"],
}

_DILUTION_RE = re.compile(r"稀释\s*(\d+(?:\.\d+)?)\s*倍")


# --------------------------------------------------------------------------- #
# 读取
# --------------------------------------------------------------------------- #


def _to_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _read_column(ws, col_index: int, start_row: int, end_row: int) -> list[Any]:
    """按行区间读取整列原始值（不跳过空行，保证行号与 Excel 一致）。"""
    return [ws.cell(row=row, column=col_index).value for row in range(start_row, end_row + 1)]


def _field_columns(block: dict) -> dict[str, str]:
    """从识别快照取出 {字段语义: 列字母}。"""
    mapping: dict[str, str] = {}
    for col in block.get("columns") or []:
        field = col.get("field") or col.get("target")
        letter = col.get("col")
        if field and letter and field not in mapping:
            mapping[field] = letter
    return mapping


def _extract_dilution(block: dict) -> float | None:
    """从列名里提取稀释倍数（如 "稀释100倍(mol/L)" -> 100）。"""
    for col in block.get("columns") or []:
        hit = _DILUTION_RE.search(str(col.get("raw") or ""))
        if hit:
            try:
                return float(hit.group(1))
            except ValueError:
                continue
    return None


def _pick_metadata(metadata: dict | None, key: str) -> float | None:
    if not metadata:
        return None
    for alias in _META_KEYS[key]:
        value = _to_float(metadata.get(alias))
        if value is not None:
            return value
    return None


def _sheet_of(region_id: str) -> str:
    return str(region_id).split("#")[0].strip()


def _locate(ws, l1_regions: dict, region_id: str, block: dict):
    """定位 L1 中的 region/block，返回 (region, l1_block, {列字母: 列序号})。"""
    l1_region = l1_regions.get(region_id)
    if l1_region is None:
        return None
    l1_block = next((b for b in l1_region.col_blocks if b.block_id == block.get("id")), None)
    if l1_block is None:
        return None
    indices = {c.col_letter: c.col_index for c in l1_block.columns}
    return l1_region, l1_block, indices


# --------------------------------------------------------------------------- #
# 构建
# --------------------------------------------------------------------------- #


def build_canonical(
    raw_path: str | Path,
    recognized: dict,
    experiment_id: str,
    metadata: dict | None = None,
) -> dict:
    """把一次识别结果 + Raw 数据整理为规范长表。

    返回结构（写入 Processed 层）：
        {
          "schema": "canonical_table_v1",
          "version": CALCULATION_VERSION,
          "columns": [...],
          "rows": [...],
          "calculations": [...],   # 标定拟合与标定归属推断过程
          "verification": [...],   # 引擎复算 vs 表内自算 的一致性
          "summary": {...},        # 偏差汇总
          "assumptions": [...],    # 所用物理假设
          "notes": [...],          # 未计算项及原因
        }
    """
    regions = recognized.get("regions") or []
    sheets_needed = {_sheet_of(r.get("id")) for r in regions if r.get("id")}
    notes: list[str] = []

    wb = openpyxl.load_workbook(Path(raw_path), data_only=True)
    try:
        structures: dict[str, tuple[Any, Any]] = {}
        for index, ws in enumerate(wb.worksheets):
            name = ws.title.strip()
            if name in sheets_needed:
                structures[name] = (ws, parse_sheet(ws, index))

        rows: list[dict] = []
        calculations: list[dict] = []
        verification: list[dict] = []
        # 离子 -> [ {block, fit} ...]（同一工作表内可能有多个候选标定曲线）
        candidates: dict[tuple[str, str], list[dict]] = {}

        # ---- 第一轮：建立所有标定曲线 ----
        for region in regions:
            region_id = region.get("id")
            sheet_name = _sheet_of(region_id)
            entry = structures.get(sheet_name)
            if entry is None:
                notes.append(f"工作表 {sheet_name} 未在 Raw 文件中找到，跳过")
                continue
            ws, structure = entry
            l1_regions = {r.region_id: r for r in structure.regions}
            for block in region.get("blocks") or []:
                if block.get("kind") != "calibration":
                    continue
                built = _build_calibration(ws, structure, l1_regions, region_id, block, experiment_id)
                calculations.extend(built["calculations"])
                rows.extend(built["rows"])
                notes.extend(built["notes"])
                if built["fit"] is not None:
                    key = (sheet_name, canonical_ion(block.get("analyte")))
                    candidates.setdefault(key, []).append(
                        {
                            "block": block.get("id"),
                            "fit": built["fit"],
                            "zero_signal_ppm": built.get("zero_signal_concentration_ppm"),
                        }
                    )

        # ---- 第二轮：样本块反算 + 单位换算 + 交叉验证 ----
        for region in regions:
            region_id = region.get("id")
            sheet_name = _sheet_of(region_id)
            entry = structures.get(sheet_name)
            if entry is None:
                continue
            ws, structure = entry
            l1_regions = {r.region_id: r for r in structure.regions}
            for block in region.get("blocks") or []:
                if block.get("kind") != "sample_measurement":
                    continue
                ion = canonical_ion(block.get("analyte"))
                pool = candidates.get((sheet_name, ion), []) if ion else []
                built = _build_samples(
                    ws, l1_regions, region_id, block, experiment_id, sheet_name,
                    pool, ion, metadata, notes,
                )
                rows.extend(built["rows"])
                verification.extend(built["verification"])
                calculations.extend(built["calculations"])
    finally:
        wb.close()

    if not rows:
        notes.append("未能从识别结果与 Raw 数据中提取任何数值行")

    return {
        "schema": CANONICAL_SCHEMA,
        "version": CALCULATION_VERSION,
        "columns": CANONICAL_COLUMNS,
        "rows": rows,
        "calculations": calculations,
        "verification": verification,
        "summary": summarize_deviations(
            [v["deviation_ppm"] for v in verification if v.get("deviation_ppm") is not None]
        ),
        "assumptions": [DILUTE_AQUEOUS_ASSUMPTION],
        "notes": notes,
    }


def _build_calibration(ws, structure, l1_regions: dict, region_id: str, block: dict, experiment_id: str) -> dict:
    located = _locate(ws, l1_regions, region_id, block)
    if located is None:
        return {"fit": None, "rows": [], "calculations": [], "notes": [f"标定块 {block.get('id')} 未能对齐 L1 结构"]}
    l1_region, _l1_block, indices = located

    fields = _field_columns(block)
    col_x = indices.get(fields.get("concentration_standard", ""))
    col_y = indices.get(fields.get("signal_area", ""))
    if col_x is None or col_y is None:
        return {
            "fit": None,
            "rows": [],
            "calculations": [],
            "notes": [f"标定块 {block.get('id')} 缺少浓度标准或信号面积列，无法拟合"],
        }

    xs = [_to_float(v) for v in _read_column(ws, col_x, l1_region.data_start_row, l1_region.data_end_row)]
    ys = [_to_float(v) for v in _read_column(ws, col_y, l1_region.data_start_row, l1_region.data_end_row)]
    fit, reason = linear_fit(xs, ys)

    calc = {
        "id": f"calibration:{block.get('id')}",
        "type": "calibration_fit",
        "analyte": block.get("analyte"),
        "block": block.get("id"),
        "x_field": "concentration_standard",
        "y_field": "signal_area",
        "ok": fit is not None,
        "reason": reason,
        "n_points": sum(1 for x, y in zip(xs, ys) if x is not None and y is not None),
    }
    zero_signal_ppm = None
    if fit is not None:
        calc["fit"] = fit.to_dict()
        # 截距非零 ⇒ 零信号会被反算成非零浓度（"幻影浓度"）。穿透曲线尾端对此最敏感，
        # 也是近检出限点位相对偏差极大的根因，必须显式暴露而非静默沿用。
        if fit.slope:
            zero_signal_ppm = -fit.intercept / fit.slope
            calc["zero_signal_concentration_ppm"] = round(zero_signal_ppm, 6)

    rows = []
    for offset, (x, y) in enumerate(zip(xs, ys)):
        if x is None and y is None:
            continue
        row = {name: None for name in CANONICAL_COLUMNS}
        row.update(
            {
                "experiment_id": experiment_id,
                "sheet": structure.sheet_name.strip(),
                "region": region_id,
                "block": block.get("id"),
                "kind": "calibration",
                "analyte": block.get("analyte"),
                "row_index": l1_region.data_start_row + offset,
                "conc_ppm_reported": x,
                "signal_area": y,
                "method": "calibration_standard" if fit else None,
                "confidence": block.get("confidence"),
                "source": "raw",
            }
        )
        rows.append(row)

    block_notes: list[str] = []
    if not fit:
        block_notes.append(f"标定块 {block.get('id')}：{reason}")
    return {
        "fit": fit,
        "rows": rows,
        "calculations": [calc],
        "notes": block_notes,
        "zero_signal_concentration_ppm": zero_signal_ppm,
    }


NEAR_ZERO_FRACTION = 0.01  # 参考浓度峰值 1% 以下的点不参与相对偏差评分


def _score_candidate(fit, areas: list[float | None], reported: list[float | None]) -> dict | None:
    """用稳健指标评价一条标定曲线与表内自算值的一致性。

    浓度接近检出限时相对偏差会因分母趋零而爆炸（实测可达 780 倍），
    故先剔除近零点，再用中位数做主判据——否则评分会被个别近零点完全支配。
    """
    pairs = [(a, r) for a, r in zip(areas, reported) if a is not None and r is not None]
    if not pairs or not fit.slope:
        return None
    peak = max(abs(r) for _, r in pairs)
    tolerance = peak * NEAR_ZERO_FRACTION

    deviations: list[float] = []
    excluded = 0
    extrapolated = 0
    for area, rep in pairs:
        if abs(rep) <= tolerance:
            excluded += 1
            continue
        computed = (area - fit.intercept) / fit.slope
        dev, _err = relative_deviation(rep, computed)
        if dev is None:
            continue
        deviations.append(dev)
        if area < fit.y_range[0] or area > fit.y_range[1]:
            extrapolated += 1
    if not deviations:
        return None

    abs_devs = [abs(d) for d in deviations]
    total = len(deviations) + excluded
    return {
        "r2": fit.r2,
        "n_scored": len(deviations),
        "n_excluded_near_zero": excluded,
        "median_abs_relative_deviation": round(median(abs_devs), 6),
        "mean_abs_relative_deviation": round(sum(abs_devs) / len(abs_devs), 6),
        "extrapolated_points": extrapolated,
        "extrapolation_ratio": round(extrapolated / total, 3) if total else None,
    }


def _select_fit(
    areas: list[float | None], reported: list[float | None], pool: list[dict]
) -> tuple[dict | None, dict]:
    """在多条候选标定曲线中选与表内自算值最一致的一条。"""
    if not pool:
        return None, {"selection_method": "none", "candidates": []}

    scored: list[dict] = []
    for candidate in pool:
        metrics = _score_candidate(candidate["fit"], areas, reported)
        scored.append({"block": candidate["block"], **(metrics or {"n_scored": 0})})

    usable = [s for s in scored if s.get("median_abs_relative_deviation") is not None]
    if not usable:
        # 没有可对照的自算值：无法用一致性判断，取第一条并如实标注
        chosen = pool[0]
        return chosen, {
            "selection_method": "first_candidate_no_reference",
            "candidates": scored,
            "note": "表内无可用自算浓度可供对照，按顺序取用第一条标定曲线，需人工确认归属",
        }

    best = min(
        usable,
        key=lambda item: (item["median_abs_relative_deviation"], item.get("extrapolation_ratio") or 0.0),
    )
    chosen = next(c for c in pool if c["block"] == best["block"])
    method = "best_agreement" if len(pool) > 1 else "only_candidate"
    return chosen, {"selection_method": method, "candidates": scored, "chosen": best["block"]}


def _build_samples(
    ws,
    l1_regions: dict,
    region_id: str,
    block: dict,
    experiment_id: str,
    sheet_name: str,
    pool: list[dict],
    ion: str | None,
    metadata: dict | None,
    notes: list[str],
) -> dict:
    located = _locate(ws, l1_regions, region_id, block)
    if located is None:
        return {"rows": [], "verification": [], "calculations": []}
    l1_region, _l1_block, indices = located

    fields = _field_columns(block)
    columns: dict[str, list[Any]] = {}
    for field, letter in fields.items():
        index = indices.get(letter)
        if index is None:
            continue
        columns[field] = _read_column(ws, index, l1_region.data_start_row, l1_region.data_end_row)

    area_series = columns.get("signal_area") or columns.get("corrected_area")
    if area_series is None:
        notes.append(f"样本块 {block.get('id')} 未识别到信号面积列，跳过浓度反算")
        return {"rows": [], "verification": [], "calculations": []}

    areas = [_to_float(v) for v in area_series]
    reported_ppms = [_to_float(v) for v in (columns.get("concentration_ppm") or [])]
    chosen, selection = _select_fit(areas, reported_ppms, pool)
    fit = chosen["fit"] if chosen else None
    calibration_block = chosen["block"] if chosen else None

    selection_calc = {
        "id": f"calibration_selection:{block.get('id')}",
        "type": "calibration_attribution",
        "block": block.get("id"),
        "analyte": block.get("analyte"),
        "has_explicit_declaration": False,
        **selection,
    }
    if fit is not None:
        selection_calc["chosen_fit"] = fit.to_dict()
    calculations = [selection_calc]

    if chosen is not None:
        chosen_metrics = next(
            (c for c in selection.get("candidates") or [] if c.get("block") == calibration_block), {}
        )
        scored_n = chosen_metrics.get("n_scored")
        # 归属判定若只靠极少数点，结论本身就不稳，必须如实标注而非当作定论
        if selection.get("selection_method") == "best_agreement" and scored_n is not None and scored_n < 3:
            notes.append(
                f"样本块 {block.get('id')}：标定归属仅在 {scored_n} 个可对照点上判定"
                f"（其余点信号接近检出限而被剔除），建议人工确认"
            )
        # 截距非零的标定曲线会把零信号反算成非零浓度，尾端低浓度点因此不可靠
        zero_signal_ppm = chosen.get("zero_signal_ppm")
        positives = [abs(r) for r in reported_ppms if r is not None and r != 0]
        if zero_signal_ppm and positives and abs(zero_signal_ppm) > min(positives):
            notes.append(
                f"样本块 {block.get('id')}：所用标定曲线（{calibration_block}）截距非零，"
                f"零信号会被反算成约 {abs(zero_signal_ppm):.3g} ppm，"
                f"而表内最小非零浓度仅 {min(positives):.3g} ppm，尾端低浓度点不可靠"
            )

    dilution = _extract_dilution(block)
    # 容量/去除率所需输入（来自实验前元数据；缺失则不计算，绝不猜）
    c0 = _pick_metadata(metadata, "initial_concentration")
    declared_ce = _pick_metadata(metadata, "equilibrium_concentration")
    volume_ml = _pick_metadata(metadata, "solution_volume_ml")
    resin_mg = _pick_metadata(metadata, "resin_mass_mg")
    mass, mass_reason = molar_mass(ion)
    if ion and mass is None:
        notes.append(f"样本块 {block.get('id')}：{mass_reason}")

    rows: list[dict] = []
    verification: list[dict] = []

    for offset in range(len(areas)):
        def value_of(field: str) -> float | None:
            series = columns.get(field) or []
            return _to_float(series[offset]) if offset < len(series) else None

        area = areas[offset]
        reported_ppm = value_of("concentration_ppm")
        reported_mol = value_of("concentration_mol")
        sample_no = value_of("sample_number")

        computed_ppm = None
        extrapolated = None
        if fit is not None and area is not None and fit.slope:
            computed_ppm = (area - fit.intercept) / fit.slope
            extrapolated = bool(area < fit.y_range[0] or area > fit.y_range[1])

        computed_mol = None
        computed_mol_diluted = None
        if computed_ppm is not None and mass is not None:
            computed_mol, _err = mg_l_to_mol_l(computed_ppm, ion or "")
            if computed_mol is not None and dilution:
                computed_mol_diluted = computed_mol * dilution

        deviation = None
        if computed_ppm is not None and reported_ppm is not None:
            deviation, _err = relative_deviation(reported_ppm, computed_ppm)

        removal = None
        if c0 is not None:
            reference = reported_ppm if reported_ppm is not None else computed_ppm
            if reference is not None:
                removal, _err = removal_rate(c0, reference)

        if area is None and reported_ppm is None:
            continue

        row = {name: None for name in CANONICAL_COLUMNS}
        row.update(
            {
                "experiment_id": experiment_id,
                "sheet": sheet_name,
                "region": region_id,
                "block": block.get("id"),
                "kind": "sample_measurement",
                "analyte": block.get("analyte"),
                "row_index": l1_region.data_start_row + offset,
                "sample_number": sample_no,
                "bed_volume": value_of("bed_volume"),
                "volume_ml": value_of("volume"),
                "signal_area": area,
                "dilution_factor": dilution,
                "conc_ppm_reported": reported_ppm,
                "conc_ppm_computed": round(computed_ppm, 6) if computed_ppm is not None else None,
                "conc_mg_l_computed": round(computed_ppm, 6) if computed_ppm is not None else None,
                "conc_mol_reported": reported_mol,
                "conc_mol_computed": computed_mol,
                "conc_mol_computed_diluted": computed_mol_diluted,
                "deviation_ppm": round(deviation, 6) if deviation is not None else None,
                "removal_rate": round(removal, 6) if removal is not None else None,
                "calibration_block": calibration_block,
                "extrapolated": extrapolated,
                "method": "calibration_back_calculation" if computed_ppm is not None else "insufficient_input",
                "confidence": block.get("confidence"),
                "source": "raw",
            }
        )
        rows.append(row)

        if deviation is not None:
            verification.append(
                {
                    "row_index": row["row_index"],
                    "sample_number": sample_no,
                    "reported_ppm": reported_ppm,
                    "computed_ppm": round(computed_ppm, 6),
                    "deviation_ppm": round(deviation, 6),
                    "calibration_block": calibration_block,
                }
            )

    if fit is None:
        notes.append(f"样本块 {block.get('id')} 无可用标定曲线，仅保留原始数值，未反算浓度")
    if any(row.get("extrapolated") for row in rows):
        notes.append(f"样本块 {block.get('id')} 存在超出标定范围的信号，已标注 extrapolated=True，请谨慎使用")

    # 吸附容量：文件通常不显式给出平衡浓度，此时以最后一个有效样本浓度作为 Ce，
    # 并在结果里写明该假设来源，交由研究者确认（绝不伪装成原始记录）。
    equilibrium = declared_ce
    equilibrium_source = "declared_in_metadata" if declared_ce is not None else None
    equilibrium_extrapolated = None
    if equilibrium is None:
        # 只接受正浓度：穿透末端信号常低于基线而给出负值，负的 Ce 没有物理意义
        for row in reversed(rows):
            candidate = row.get("conc_ppm_reported")
            used_computed = False
            if candidate is None or candidate <= 0:
                computed = row.get("conc_ppm_computed")
                if computed is not None and computed > 0:
                    candidate = computed
                    used_computed = True
            if candidate is not None and candidate > 0:
                equilibrium = candidate
                equilibrium_source = (
                    "last_sample_computed" if used_computed else "last_sample_as_equilibrium"
                )
                equilibrium_extrapolated = row.get("extrapolated")
                break
        if equilibrium is None:
            equilibrium_source = "none_available"

    missing_inputs = [
        name
        for name, value in (("初始浓度", c0), ("溶液体积", volume_ml), ("树脂质量", resin_mg))
        if value is None
    ]
    if missing_inputs or equilibrium is None:
        detail = "、".join(missing_inputs + (["平衡浓度"] if equilibrium is None else []))
        notes.append(f"样本块 {block.get('id')}：吸附容量未计算（缺少{detail}）")
        if c0 is None:
            notes.append(f"样本块 {block.get('id')}：去除率未计算（缺少初始浓度）")
    else:
        capacity, err = adsorption_capacity_mg_g(c0, equilibrium, volume_ml, resin_mg)
        calculations.append(
            {
                "id": f"adsorption_capacity:{block.get('id')}",
                "type": "adsorption_capacity",
                "block": block.get("id"),
                "analyte": block.get("analyte"),
                "formula": "q = (C0 - Ce) * V / m",
                "ok": capacity is not None,
                "reason": err,
                "inputs": {
                    "C0_mg_l": c0,
                    "Ce_mg_l": equilibrium,
                    "volume_ml": volume_ml,
                    "resin_mass_mg": resin_mg,
                },
                "equilibrium_source": equilibrium_source,
                "equilibrium_extrapolated": equilibrium_extrapolated,
                "q_mg_g": round(capacity, 6) if capacity is not None else None,
                "note": "文件未显式给出平衡浓度，故以最后一个有效样本浓度作为 Ce；请人工确认后再引用",
            }
        )
        if equilibrium_extrapolated:
            notes.append(
                f"样本块 {block.get('id')}：Ce 取自超出标定范围的信号点，容量结果偏差风险高，请人工核对"
            )

    return {"rows": rows, "verification": verification, "calculations": calculations}


# --------------------------------------------------------------------------- #
# 导出
# --------------------------------------------------------------------------- #


def render_csv(canonical: dict) -> str:
    """规范长表转 CSV（utf-8-sig 便于 Excel 直接打开）。"""
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=CANONICAL_COLUMNS, extrasaction="ignore")
    writer.writeheader()
    for row in canonical.get("rows") or []:
        writer.writerow({name: ("" if row.get(name) is None else row.get(name)) for name in CANONICAL_COLUMNS})
    return buffer.getvalue()


def render_markdown(canonical: dict, max_rows: int = 40) -> str:
    """规范长表转 Markdown（超长时截断并提示下载 CSV）。"""
    rows = canonical.get("rows") or []
    if not rows:
        return "_（本次归档未生成规范表格行）_"

    shown = rows[:max_rows]
    header = "| " + " | ".join(CANONICAL_COLUMNS) + " |"
    divider = "| " + " | ".join("---" for _ in CANONICAL_COLUMNS) + " |"
    body = [
        "| " + " | ".join("" if row.get(name) is None else str(row.get(name)) for name in CANONICAL_COLUMNS) + " |"
        for row in shown
    ]
    lines = [header, divider, *body]
    if len(rows) > max_rows:
        lines.append(f"\n_（共 {len(rows)} 行，此处仅展示前 {max_rows} 行，完整数据见 CSV 导出）_")
    return "\n".join(lines)