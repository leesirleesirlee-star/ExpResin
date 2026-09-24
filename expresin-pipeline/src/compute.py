"""ExpResin 科学计算引擎（W7：自动计算）。

设计约束（对应《项目宪法》科学不变量）：
  - LLM 只做语义理解，**数值一律由本模块用 Python 计算**；
  - 任何输入不足的计算必须返回失败原因，绝不猜测或补全；
  - 每个结果都携带方法名与输入，保证 Processed 层可追溯；
  - 只消费 Raw 派生出的数值，绝不改写 Raw。

本模块不做任何 IO，可独立单元测试。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

# --------------------------------------------------------------------------- #
# 离子摩尔质量（g/mol）
# --------------------------------------------------------------------------- #

# 使用 IUPAC 常用原子量：S 32.06 / O 15.999 / Cl 35.45 / N 14.007 / F 18.998
# Li 6.94 / Na 22.99 / Ca 40.078 / H 1.008
ION_MOLAR_MASS: dict[str, float] = {
    "SO4": 96.06,
    "Cl": 35.45,
    "NO3": 62.00,
    "F": 19.00,
    "PO4": 94.97,
    "HPO4": 96.06,
    "NH4+": 18.04,
    "Li+": 6.94,
    "Na": 22.99,
    "Ca": 40.08,
}

# 离子写法归一（与后端 ANALYTE_OPTIONS / _ANALYTE_ALIASES 保持同一套语义）
_ION_ALIASES: dict[str, str] = {
    "so4": "SO4", "so42-": "SO4", "so4-2": "SO4", "硫酸根": "SO4", "硫酸盐": "SO4",
    "cl": "Cl", "cl-": "Cl", "氯": "Cl", "氯离子": "Cl",
    "no3": "NO3", "no3-": "NO3", "硝酸根": "NO3",
    "f": "F", "f-": "F", "氟": "F", "氟离子": "F",
    "po4": "PO4", "po43-": "PO4", "磷酸根": "PO4",
    "hpo4": "HPO4", "hpo4 2-": "HPO4", "hpo42-": "HPO4", "磷酸氢根": "HPO4",
    "nh4": "NH4+", "nh4+": "NH4+", "铵": "NH4+", "铵根": "NH4+", "氨氮": "NH4+",
    "li": "Li+", "li+": "Li+", "锂": "Li+", "锂离子": "Li+",
    "na": "Na", "na+": "Na", "钠": "Na", "钠离子": "Na",
    "ca": "Ca", "ca2+": "Ca", "钙": "Ca", "钙离子": "Ca",
}


def canonical_ion(name: str | None) -> str | None:
    """把各种离子写法归一为 ION_MOLAR_MASS 的键；无法识别返回 None。"""
    if not name:
        return None
    key = str(name).strip().lower().replace(" ", "")
    if key in _ION_ALIASES:
        return _ION_ALIASES[key]
    for candidate in ION_MOLAR_MASS:
        if candidate.lower() == key:
            return candidate
    return None


def molar_mass(analyte: str | None) -> tuple[float | None, str | None]:
    """返回 (摩尔质量 g/mol, 失败原因)。"""
    ion = canonical_ion(analyte)
    if ion is None:
        return None, f"未识别的离子/组分：{analyte!r}，无法进行摩尔换算"
    return ION_MOLAR_MASS[ion], None


# --------------------------------------------------------------------------- #
# 单位换算
# --------------------------------------------------------------------------- #

# ppm 与 mg/L 的等价建立在"稀水溶液、密度≈1 g/mL"这一假设上。
# 高盐或高有机质基质下该假设不成立，必须把假设写进结果，让研究者可判断。
DILUTE_AQUEOUS_ASSUMPTION = "假定稀水溶液密度≈1 g/mL，故 1 ppm ≈ 1 mg/L"


def ppm_to_mg_l(ppm: float) -> tuple[float, str]:
    """ppm -> mg/L（返回结果与所用假设，供溯源）。"""
    return float(ppm), DILUTE_AQUEOUS_ASSUMPTION


def mg_l_to_mol_l(mg_l: float, analyte: str) -> tuple[float | None, str | None]:
    """mg/L -> mol/L。mol/L = (mg/L) / M / 1000。"""
    mass, reason = molar_mass(analyte)
    if mass is None:
        return None, reason
    return float(mg_l) / mass / 1000.0, None


def mol_l_to_mg_l(mol_l: float, analyte: str) -> tuple[float | None, str | None]:
    """mol/L -> mg/L。mg/L = (mol/L) * M * 1000。"""
    mass, reason = molar_mass(analyte)
    if mass is None:
        return None, reason
    return float(mol_l) * mass * 1000.0, None


def mg_l_to_ppm(mg_l: float) -> tuple[float, str]:
    return float(mg_l), DILUTE_AQUEOUS_ASSUMPTION


# --------------------------------------------------------------------------- #
# 线性拟合（标定曲线）
# --------------------------------------------------------------------------- #


@dataclass
class LinearFit:
    """标定曲线拟合结果（y = slope * x + intercept）。"""

    slope: float
    intercept: float
    r2: float | None
    n: int
    x_range: list[float]
    y_range: list[float]
    method: str = "ordinary_least_squares"

    def predict(self, x: float) -> float:
        return self.slope * float(x) + self.intercept

    def to_dict(self) -> dict[str, Any]:
        return {
            "slope": self.slope,
            "intercept": self.intercept,
            "r2": self.r2,
            "n": self.n,
            "x_range": self.x_range,
            "y_range": self.y_range,
            "method": self.method,
            "equation": f"y = {self.slope:.6g} x + {self.intercept:.6g}",
        }


def linear_fit(
    xs: Sequence[float | None],
    ys: Sequence[float | None],
    min_points: int = 3,
) -> tuple[LinearFit | None, str | None]:
    """对成对数据做普通最小二乘拟合。

    返回 (fit, 失败原因)。有效点少于 min_points、或自变量无变化时返回 None，
    并给出可直接展示给研究者的原因——不猜、不外推。
    """
    pairs = [
        (float(x), float(y))
        for x, y in zip(xs, ys)
        if x is not None and y is not None
    ]
    if len(pairs) < min_points:
        return None, f"有效标定点仅 {len(pairs)} 个，少于最少要求 {min_points} 个，不做拟合"

    n = len(pairs)
    mean_x = sum(x for x, _ in pairs) / n
    mean_y = sum(y for _, y in pairs) / n
    sxx = sum((x - mean_x) ** 2 for x, _ in pairs)
    if sxx == 0:
        return None, "标定浓度全部相同，自变量无变化，无法拟合"

    sxy = sum((x - mean_x) * (y - mean_y) for x, y in pairs)
    slope = sxy / sxx
    intercept = mean_y - slope * mean_x

    ss_tot = sum((y - mean_y) ** 2 for _, y in pairs)
    ss_res = sum((y - (slope * x + intercept)) ** 2 for x, y in pairs)
    r2 = round(1 - ss_res / ss_tot, 6) if ss_tot > 0 else None

    xs_clean = [x for x, _ in pairs]
    ys_clean = [y for _, y in pairs]
    return (
        LinearFit(
            slope=slope,
            intercept=intercept,
            r2=r2,
            n=n,
            x_range=[min(xs_clean), max(xs_clean)],
            y_range=[min(ys_clean), max(ys_clean)],
        ),
        None,
    )


# --------------------------------------------------------------------------- #
# 偏离与效率
# --------------------------------------------------------------------------- #


def relative_deviation(reference: float, measured: float) -> tuple[float | None, str | None]:
    """相对偏差 (measured - reference) / reference，返回比值（不是百分比）。"""
    if reference is None or measured is None:
        return None, "缺少对比所需的任一数值"
    if float(reference) == 0:
        return None, "参考值为 0，相对偏差无定义"
    return (float(measured) - float(reference)) / float(reference), None


def removal_rate(initial: float | None, current: float | None) -> tuple[float | None, str | None]:
    """去除率 = (C0 - Ct) / C0。"""
    if initial is None or current is None:
        return None, "缺少初始浓度或当前浓度"
    if float(initial) <= 0:
        return None, "初始浓度须为正数，去除率无定义"
    return (float(initial) - float(current)) / float(initial), None


def adsorption_capacity_mg_g(
    initial_mg_l: float | None,
    equilibrium_mg_l: float | None,
    volume_ml: float | None,
    mass_mg: float | None,
) -> tuple[float | None, str | None]:
    """吸附容量 q = (C0 - Ce) * V / m，输入用 mg/L、mL、mg 时结果即 mg/g。"""
    if None in (initial_mg_l, equilibrium_mg_l, volume_ml, mass_mg):
        return None, "缺少初始浓度/平衡浓度/溶液体积/树脂质量，不计算容量"
    if float(mass_mg) <= 0:
        return None, "树脂质量须为正数，容量无定义"
    if float(volume_ml) <= 0:
        return None, "溶液体积须为正数，容量无定义"
    c0 = float(initial_mg_l)
    ce = float(equilibrium_mg_l)
    if c0 <= 0:
        return None, "初始浓度须为正数，容量无定义"
    if ce < 0:
        return None, "平衡浓度为负值（信号低于基线），无法给出有物理意义的容量"
    if ce >= c0:
        return None, "平衡浓度不低于初始浓度，未见吸附，容量无定义"
    return (c0 - ce) * float(volume_ml) / float(mass_mg), None


def median(values: Sequence[float]) -> float | None:
    """中位数（抗离群，用于浓度接近检出限时的稳健评分）。"""
    clean = sorted(float(v) for v in values if v is not None)
    if not clean:
        return None
    mid = len(clean) // 2
    if len(clean) % 2:
        return clean[mid]
    return (clean[mid - 1] + clean[mid]) / 2


def summarize_deviations(values: Sequence[float]) -> dict[str, Any] | None:
    """给一组相对偏差做汇总统计，用于判断"实验员自算值 vs 引擎复算值"是否一致。

    均值会被"浓度接近检出限"的点支配（分母趋零导致相对偏差爆炸），
    因此这里同时给出中位数与平均绝对相对偏差作为更稳健的一致性指标。
    """
    clean = [float(v) for v in values if v is not None]
    if not clean:
        return None
    n = len(clean)
    mean = sum(clean) / n
    variance = sum((v - mean) ** 2 for v in clean) / n
    abs_values = [abs(v) for v in clean]
    return {
        "n": n,
        "mean_relative_deviation": round(mean, 6),
        "median_relative_deviation": round(median(clean), 6),
        "mean_absolute_relative_deviation": round(sum(abs_values) / n, 6),
        "median_absolute_relative_deviation": round(median(abs_values), 6),
        "max_abs_relative_deviation": round(max(abs_values), 6),
        "std_relative_deviation": round(variance**0.5, 6),
    }


CALCULATION_VERSION = "compute_v1"