"""确定性数据质量检查（不改库、不依赖 LLM）。

第一条规则：实验声明类型与识别字段的一致性提示。
来源：2026-09-23 §4 观察 1（RES-20260921-003 声明 batch 但数据含 BV 列），
2026-09-24 遗留待办 #3。

规则刻意保守：只对「类型特征字段」做禁止性检查
（batch 不应出现床体积 BV / 电位 / 电流，column 不应出现电位 / 电流……），
不做「应当出现某字段」的正向断言，避免对缺列场景误报。
"""

from __future__ import annotations

from typing import Any

# 各实验类型的「特征字段」：出现即可作为该类型的判别证据
TYPE_DISTINCTIVE_FIELDS: dict[str, set[str]] = {
    "column": {"bed_volume"},
    "electrochemical": {"potential_v", "current_a"},
}

# 各声明类型「不应出现」的字段（= 其他类型特征字段的并集）
TYPE_FORBIDDEN_FIELDS: dict[str, set[str]] = {
    "batch": {"bed_volume", "potential_v", "current_a"},
    "column": {"potential_v", "current_a"},
    "electrochemical": {"bed_volume"},
}

_TYPE_LABELS = {
    "batch": "静态批次",
    "column": "动态柱",
    "electrochemical": "电化学",
    "regeneration": "再生",
}

# 低于此置信度的命中不提示（与幻觉探针的高置信阈值一致）
CONF_THRESHOLD = 0.8


def _iter_columns(recognized: dict | None):
    if not recognized:
        return
    for region in recognized.get("regions") or []:
        for block in region.get("blocks") or []:
            block_id = block.get("id") or region.get("id") or ""
            for col in block.get("columns") or []:
                yield block_id, col


def _field_owner_type(field: str) -> str | None:
    for exp_type, fields in TYPE_DISTINCTIVE_FIELDS.items():
        if field in fields:
            return exp_type
    return None


def check_type_consistency(experiment_type: str | None, recognized: dict | None) -> list[dict]:
    """声明类型 vs 高置信识别字段的一致性检查。

    返回 warning 列表（可为空）。每条 warning 结构：
    {code, declared_type, suggested_type, field, columns[], max_conf, message}
    """
    declared = (experiment_type or "").strip().lower()
    if not declared or declared not in TYPE_FORBIDDEN_FIELDS:
        return []

    forbidden = TYPE_FORBIDDEN_FIELDS[declared]
    hits: dict[str, list[dict]] = {}
    for block_id, col in _iter_columns(recognized):
        field = col.get("target")
        conf = col.get("conf") or 0.0
        if field in forbidden and conf >= CONF_THRESHOLD:
            hits.setdefault(field, []).append(
                {"where": f"{block_id}:{col.get('col')}", "conf": round(conf, 3), "raw": col.get("raw")}
            )

    warnings: list[dict] = []
    for field, cols in sorted(hits.items()):
        suggested = _field_owner_type(field)
        max_conf = max(c["conf"] for c in cols)
        declared_label = _TYPE_LABELS.get(declared, declared)
        suggested_label = _TYPE_LABELS.get(suggested, suggested) if suggested else None
        message = (
            f"声明类型为「{declared_label}({declared})」，但高置信识别出特征字段 "
            f"{field}（{len(cols)} 列，最高 conf {max_conf:.2f}）"
        )
        if suggested:
            message += f"，建议核对实验类型是否应为「{suggested_label}({suggested})」"
        warnings.append(
            {
                "code": "type_field_mismatch",
                "declared_type": declared,
                "suggested_type": suggested,
                "field": field,
                "columns": [c["where"] for c in cols],
                "max_conf": max_conf,
                "message": message,
            }
        )
    return warnings


def experiment_warnings(experiment: dict[str, Any]) -> list[dict]:
    """对一条 experiment 记录（store.get_experiment 的返回）计算全部警告。"""
    processed = experiment.get("processed") or {}
    return check_type_consistency(
        experiment.get("experiment_type"),
        processed.get("recognized_data"),
    )
