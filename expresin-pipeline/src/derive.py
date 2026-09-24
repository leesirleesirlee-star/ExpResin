"""ExpResin 模板派生计算（derive_v1）。

模板 C 区（Optional Results / Automatically Calculated Data）里的自动计算量在此实现。

科学不变量：
  - 只做确定性计算，不调用 LLM（LLM 不参与数值计算）；
  - 任何一项缺输入、或物理上无定义时，返回 value=None + reason，**绝不臆造**；
  - 每项带 `method`，写明所用判据/公式，便于人工复核；
  - 判据阈值集中定义在下方常量，便于评审与版本化。

内部单位约定（由 template_fill 在调用前统一换算）：
  时间 s | 浓度 mg/L | 体积 mL | 质量 mg | 电位 V | 电流 A
导出时的单位换算（如 s → min）由 template_export 负责。
"""

from __future__ import annotations

from typing import Any, Sequence

from compute import adsorption_capacity_mg_g, removal_rate

DERIVE_VERSION = "derive_v1"

# ---- 判据阈值（集中定义，便于评审与版本化）----
BREAKTHROUGH_THRESHOLD = 0.05  # 穿透时间：Cₜ/C₀ 首次 ≥ 5%
EXHAUSTION_THRESHOLD = 0.95  # 耗尽时间：Cₜ/C₀ 首次 ≥ 95%
EQUILIBRIUM_REL_CHANGE = 0.05  # 平衡时间：相邻点相对变化 < 5%
EQUILIBRIUM_CONSECUTIVE = 2  # 平衡时间：需连续满足的区间数


def _item(value: Any, unit: str | None = None, reason: str | None = None, method: str | None = None) -> dict:
    return {"value": value, "unit": unit, "reason": reason, "method": method}


def _pairs(times: Sequence[Any] | None, values: Sequence[Any] | None) -> list[tuple[float, float]]:
    """按时间升序返回两侧都有值的 (t, v) 列表（None 一律跳过）。"""
    if not times or not values:
        return []
    out: list[tuple[float, float]] = []
    for t, v in zip(times, values):
        if t is None or v is None:
            continue
        try:
            out.append((float(t), float(v)))
        except (TypeError, ValueError):
            continue
    out.sort(key=lambda p: p[0])
    return out


def _last_valid(values: Sequence[Any] | None) -> float | None:
    if not values:
        return None
    for v in reversed(values):
        if v is None:
            continue
        try:
            return float(v)
        except (TypeError, ValueError):
            continue
    return None


def _threshold_time(
    pairs: list[tuple[float, float]], initial: float | None, threshold: float, label: str
) -> dict:
    """首个 C/C₀ ≥ threshold 的时间点（时间单位与输入一致）。"""
    if not pairs:
        return _item(None, "s", "无有效浓度测量点")
    if initial is None or float(initial) <= 0:
        return _item(None, "s", "缺少有效初始浓度 C₀，无法判定 " + label)
    c0 = float(initial)
    for t, c in pairs:
        if c / c0 >= threshold:
            return _item(round(t, 6), "s", None, f"first time C/C₀ ≥ {threshold:g}")
    return _item(None, "s", f"整条序列未达到 C/C₀ ≥ {threshold:g}")


def _integrate(times: Sequence[Any] | None, values: Sequence[Any] | None, absolute: bool = True) -> dict:
    """梯形积分 ∫v dt（缺值处不插补，两侧都有值才计入）。"""
    pairs = _pairs(times, values)
    if len(pairs) < 2:
        return _item(None, None, "有效数据点少于 2 个，无法积分")
    total = 0.0
    for (t0, v0), (t1, v1) in zip(pairs, pairs[1:]):
        dt = t1 - t0
        if dt <= 0:
            continue
        a = abs(v0) if absolute else v0
        b = abs(v1) if absolute else v1
        total += (a + b) / 2.0 * dt
    method = "trapezoidal integration of |v| over time" if absolute else "trapezoidal integration of v over time"
    return _item(round(total, 6), None, None, method)


# ---------------------------------------------------------------- batch


def _equilibrium_time(pairs: list[tuple[float, float]]) -> dict:
    """浓度趋于稳定的首个时间点：相邻点相对变化 < 阈值且连续满足 N 个区间。"""
    if len(pairs) < EQUILIBRIUM_CONSECUTIVE + 1:
        return _item(None, "s", "有效测量点不足，无法判断平衡")
    stable = 0
    for i in range(1, len(pairs)):
        prev, cur = pairs[i - 1][1], pairs[i][1]
        if prev == 0:
            stable = 0
            continue
        if abs(cur - prev) / abs(prev) < EQUILIBRIUM_REL_CHANGE:
            stable += 1
            if stable >= EQUILIBRIUM_CONSECUTIVE:
                start = pairs[i - EQUILIBRIUM_CONSECUTIVE][0]
                return _item(
                    round(start, 6),
                    "s",
                    None,
                    f"first time where |ΔC|/C < {EQUILIBRIUM_REL_CHANGE:.0%} for {EQUILIBRIUM_CONSECUTIVE} consecutive intervals",
                )
        else:
            stable = 0
    return _item(None, "s", f"未观察到连续 {EQUILIBRIUM_CONSECUTIVE} 次相对变化 < {EQUILIBRIUM_REL_CHANGE:.0%} 的稳定平台")


def derive_batch(series: dict, meta: dict) -> dict:
    """Batch：Cₑ / 去除率 / qₑ / 平衡时间。"""
    pairs = _pairs(series.get("time_s"), series.get("concentration_mg_l"))
    c0 = meta.get("initial_concentration")
    volume = meta.get("solution_volume")
    mass = meta.get("resin_mass")

    if pairs:
        ce = pairs[-1][1]
        ce_item = _item(round(ce, 6), "mg/L", None, "last valid concentration point")
    else:
        ce = None
        ce_item = _item(None, "mg/L", "无有效浓度测量点")

    rate, rate_reason = removal_rate(c0, ce)
    removal_item = _item(
        None if rate is None else round(rate * 100, 2),
        "%",
        rate_reason,
        "(C₀ - Cₑ) / C₀ × 100",
    )

    q, q_reason = adsorption_capacity_mg_g(c0, ce, volume, mass)
    capacity_item = _item(
        None if q is None else round(q, 6),
        "mg/g",
        q_reason,
        "(C₀ - Cₑ) × V / m",
    )

    return {
        "equilibrium_concentration": ce_item,
        "removal_efficiency": removal_item,
        "adsorption_capacity": capacity_item,
        "equilibrium_time": _equilibrium_time(pairs),
    }


# ---------------------------------------------------------------- column


def derive_column(series: dict, meta: dict) -> dict:
    """Column：处理体积 / BV 倍数 / 最终 Cₜ/C₀ / 穿透时间 / 耗尽时间。"""
    pairs = _pairs(series.get("time_s"), series.get("concentration_mg_l"))
    c0 = meta.get("initial_concentration")
    flow_rate = meta.get("flow_rate")  # mL/min
    bed_volume = meta.get("bed_volume")  # mL

    last_t = pairs[-1][0] if pairs else None

    # 处理体积 = 流速 × 运行时间（流速单位 mL/min，时间内部为 s）
    if flow_rate is None:
        treated_item = _item(None, "mL", "缺少流速（Flow rate），无法计算处理体积")
        treated = None
    elif last_t is None:
        treated_item = _item(None, "mL", "无有效时间序列，无法计算处理体积")
        treated = None
    else:
        treated = float(flow_rate) * (last_t / 60.0)
        treated_item = _item(round(treated, 6), "mL", None, "flow rate × elapsed time")

    if treated is None:
        bv_item = _item(None, "BV", "处理体积不可得，无法折算床体积倍数")
    elif bed_volume is None or float(bed_volume) <= 0:
        bv_item = _item(None, "BV", "缺少有效床体积（Bed volume），无法折算")
    else:
        bv_item = _item(round(treated / float(bed_volume), 6), "BV", None, "treated volume / bed volume")

    if pairs and c0 is not None and float(c0) > 0:
        ct_c0 = pairs[-1][1] / float(c0)
        ct_item = _item(round(ct_c0, 6), "—", None, "final Cₜ / C₀")
    else:
        reason = "无有效浓度测量点" if not pairs else "缺少有效初始浓度 C₀，无法计算 Cₜ/C₀"
        ct_item = _item(None, "—", reason)

    return {
        "treated_volume": treated_item,
        "bed_volumes_treated": bv_item,
        "ct_c0": ct_item,
        "breakthrough_time": _threshold_time(pairs, c0, BREAKTHROUGH_THRESHOLD, "穿透时间"),
        "exhaustion_time": _threshold_time(pairs, c0, EXHAUSTION_THRESHOLD, "耗尽时间"),
    }


# ---------------------------------------------------------------- electrochemical


def derive_electrochemical(series: dict, meta: dict) -> dict:
    """Electrochemical：电流密度 / 终浓度 / 去除率 / 电荷量 / 能耗。"""
    currents = series.get("current_a")
    potentials = series.get("potential_v")
    times = series.get("time_s")
    conc = series.get("concentration_mg_l")

    c0 = meta.get("initial_concentration")
    area = meta.get("electrode_area")  # cm²（模板 A 区未含，缺省时给出原因）

    mean_i = None
    valid_i = [abs(float(v)) for v in (currents or []) if v is not None]
    if valid_i:
        mean_i = sum(valid_i) / len(valid_i)

    if mean_i is None:
        density_item = _item(None, "A/cm²", "无有效电流数据")
    elif area is None or float(area) <= 0:
        density_item = _item(None, "A/cm²", "缺少电极面积输入（模板 A 区未含该字段），无法计算电流密度")
    else:
        density_item = _item(round(mean_i / float(area), 8), "A/cm²", None, "mean |I| / electrode area")

    final_c = _last_valid(conc)
    final_item = _item(
        None if final_c is None else round(final_c, 6),
        "mg/L",
        None if final_c is not None else "无有效浓度测量点",
        "last valid concentration point",
    )

    rate, rate_reason = removal_rate(c0, final_c)
    removal_item = _item(
        None if rate is None else round(rate * 100, 2),
        "%",
        rate_reason,
        "(C₀ - C_final) / C₀ × 100",
    )

    charge_item = _integrate(times, currents, absolute=True)
    charge_item["unit"] = "C"
    charge_item["method"] = "trapezoidal integration of |I| over time"

    # 能耗 ∫|U·I| dt：需要同一时刻同时有 U 与 I
    if not times or not potentials or not currents:
        energy_item = _item(None, "J", "缺少电位或电流序列，无法计算能耗")
    else:
        power = []
        for u, i in zip(potentials, currents):
            if u is None or i is None:
                power.append(None)
                continue
            power.append(abs(float(u) * float(i)))
        energy_item = _integrate(times, power, absolute=False)
        energy_item["unit"] = "J"
        energy_item["method"] = "trapezoidal integration of |U·I| over time"

    return {
        "current_density": density_item,
        "final_concentration": final_item,
        "removal_efficiency": removal_item,
        "charge_passed": charge_item,
        "energy_consumption": energy_item,
    }


DERIVERS = {
    "batch": derive_batch,
    "column": derive_column,
    "electrochemical": derive_electrochemical,
}


def derive_all(experiment_type: str, series: dict, meta: dict) -> dict:
    """按实验类型分发；未知类型返回空 dict（由调用方决定如何提示）。"""
    fn = DERIVERS.get((experiment_type or "").strip().lower())
    if fn is None:
        return {}
    return fn(series, meta)
