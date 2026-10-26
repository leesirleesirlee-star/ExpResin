"""PortalJarvis 服务层：字段抽取、缺失项追问、单位校验、规范文档生成。

对应 PRD 功能需求：
  FR-16 自然语言字段抽取
  FR-17 缺失项追问
  FR-18 单位与范围初检
  FR-19 字段级溯源
  FR-07 Raw / Processed 分层（规范文档产出）
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

PIPELINE_SRC = Path(__file__).resolve().parents[1] / "src"
if str(PIPELINE_SRC) not in sys.path:
    sys.path.insert(0, str(PIPELINE_SRC))

from canonical import build_canonical, render_csv, render_markdown as render_canonical_markdown  # noqa: E402
from llm import LLMClient  # noqa: E402

TEMPLATE_PATH = Path(__file__).resolve().parents[1] / "config" / "experiment_template_v1.json"

# 语言里常见的单位写法 -> 规范单位
UNIT_ALIASES = {
    "mg": "mg", "毫克": "mg", "g": "g", "克": "g",
    "ml": "mL", "毫升": "mL", "l": "L", "升": "L",
    "mg/l": "mg/L", "mgl": "mg/L", "ppm": "ppm", "mg/liter": "mg/L",
    "mol/l": "mol/L", "mmol/l": "mmol/L", "umol/l": "umol/L",
    "min": "min", "分钟": "min", "h": "h", "小时": "h", "hr": "h",
    "day": "day", "天": "day", "d": "day",
    "c": "degC", "℃": "degC", "°c": "degC", "摄氏度": "degC",
    "bv": "BV", "ph": "pH",
}


# --------------------------------------------------------------------------- #
# 模板
# --------------------------------------------------------------------------- #


def load_template(path: str | Path | None = None) -> dict:
    return json.loads(Path(path or TEMPLATE_PATH).read_text(encoding="utf-8"))


def field_index(template: dict) -> dict[str, dict]:
    index: dict[str, dict] = {}
    for sheet in template["sheets"]:
        for field in sheet["fields"]:
            item = dict(field)
            item["sheet_id"] = sheet["id"]
            item["stage"] = sheet.get("stage", "pre")
            index[field["path"]] = item
    return index


def field_catalog(template: dict, stage: str | None = None) -> list[dict]:
    """给 LLM 看的字段清单（排除文件与派生字段）。"""
    out = []
    for path, f in field_index(template).items():
        if f.get("type") in ("file", "derived"):
            continue
        if stage and f["stage"] != stage:
            continue
        out.append(
            {
                "field_path": path,
                "label": f["label"],
                "type": f.get("type"),
                "unit": f.get("unit"),
                "options": f.get("options"),
            }
        )
    return out


# --------------------------------------------------------------------------- #
# 单位初检（FR-18）
# --------------------------------------------------------------------------- #


def normalize_unit(raw: str | None) -> str | None:
    if not raw:
        return None
    key = raw.strip().lower()
    return UNIT_ALIASES.get(key, raw.strip())


def check_unit(field: dict, unit: str | None) -> str:
    """返回 'ok' 或 'unit_error'。"""
    canonical = field.get("canonical_unit") or field.get("unit")
    if not canonical or not unit:
        return "ok"
    return "ok" if normalize_unit(unit) == canonical else "unit_error"


# --------------------------------------------------------------------------- #
# 自然语言字段抽取（FR-16）
# --------------------------------------------------------------------------- #

EXTRACT_SYSTEM = (
    "你是 ExpResin 的实验记录助手 PortalJarvis。"
    "你的职责是把实验员的中文口述整理成结构化字段。"
    "只抽取明确提到的信息，绝对不要猜测或补全。"
    "必须严格输出 JSON。"
)


def _extract_prompt(catalog: list[dict], text: str) -> str:
    lines = []
    for f in catalog:
        unit = f"（单位 {f['unit']}）" if f.get("unit") else ""
        options = f" 可选值: {f['options']}" if f.get("options") else ""
        lines.append(f"- {f['field_path']} | {f['label']}{unit}{options}")
    fields = "\n".join(lines)
    example = {
        "fields": [
            {
                "field_path": "02_Method_Materials.resin_mass",
                "value": "120",
                "unit": "mg",
                "confidence": 0.95,
                "raw_text": "120 mg 的 A600 树脂",
            }
        ]
    }
    return f"""请从下面这段实验员的话里抽取字段。

【可用字段】
{fields}

【实验员的话】
{text}

【要求】
1. 只抽取话里明确出现的信息，未提到的字段不要输出。
2. 数值只保留数字本身，单位单列到 unit 字段。
3. confidence 表示"这句话确实给出了该字段"的把握；模糊表述请低于 0.8。
4. 输出格式：
{json.dumps(example, ensure_ascii=False)}

只输出 JSON。"""


def extract_fields(
    client: LLMClient, text: str, template: dict, stage: str = "pre"
) -> tuple[list[dict], dict]:
    """返回 (字段列表, usage)。"""
    catalog = field_catalog(template, stage)
    index = field_index(template)
    parsed, resp = client.chat_json(
        [
            {"role": "system", "content": EXTRACT_SYSTEM},
            {"role": "user", "content": _extract_prompt(catalog, text)},
        ],
        # 字段抽取是结构化任务：实测 flash 的 reasoning 仅约 56 tokens（pro 约 1323），
        # 输出质量一致但更快更省，因此这里按任务复杂度做模型路由（PRD FR-25）。
        tier="flash",
        max_tokens=4096,
    )
    if not isinstance(parsed, dict):
        parsed = {}

    results: list[dict] = []
    for item in parsed.get("fields", []) or []:
        path = str(item.get("field_path", "")).strip()
        field = index.get(path)
        if not field:
            continue
        value = item.get("value")
        if value is None or str(value).strip() == "":
            continue
        unit = normalize_unit(item.get("unit"))
        confidence = float(item.get("confidence", 0.5) or 0.5)

        status = "pending"
        if confidence < 0.8:
            status = "low_confidence"
        if check_unit(field, unit) == "unit_error":
            status = "unit_error"

        results.append(
            {
                "field_path": path,
                "value": str(value).strip(),
                "unit": unit,
                "confidence": round(confidence, 2),
                "status": status,
                "source_type": "conversation",
                "raw_text": item.get("raw_text") or text,
            }
        )
    return results, resp.usage


# --------------------------------------------------------------------------- #
# 缺失项与追问（FR-17）
# --------------------------------------------------------------------------- #


def compute_missing(template: dict, drafts: dict[str, dict], stage: str = "pre") -> list[dict]:
    missing = []
    for path, field in field_index(template).items():
        if field["stage"] != stage or not field.get("required"):
            continue
        draft = drafts.get(path) or {}
        if str(draft.get("value") or "").strip():
            continue
        if draft.get("status") == "deferred":
            continue
        missing.append(
            {
                "field_path": path,
                "label": field["label"],
                "reason": "必填项尚未填写",
                "required": True,
            }
        )
    return missing


def compose_reply(extracted: list[dict], missing: list[dict], index: dict[str, dict]) -> str:
    parts = []
    if extracted:
        names = "、".join(index[e["field_path"]]["label"] for e in extracted[:6] if e["field_path"] in index)
        parts.append(f"已记录：{names}。")
    else:
        parts.append("这次描述里没有识别到可填写的字段。")

    if missing:
        labels = "、".join(m["label"] for m in missing[:5])
        more = f" 等 {len(missing)} 项" if len(missing) > 5 else ""
        parts.append(f"还缺：{labels}{more}。可以在右侧表单补充，或告诉我「稍后补」。")
    else:
        parts.append("必填信息已齐全，确认无误后即可归档。")
    return "".join(parts)


# --------------------------------------------------------------------------- #
# 规范文档生成（FR-07 / FR-19）
# --------------------------------------------------------------------------- #


def build_processed(
    experiment_id: str,
    template: dict,
    drafts: dict[str, dict],
    recognized: dict | None,
    raw_file: str | None,
    raw_path: str | Path | None = None,
) -> dict:
    index = field_index(template)
    meta: dict[str, Any] = {}
    provenance: dict[str, Any] = {}
    # 扁平化的元数据（key 不带 sheet 前缀），供计算引擎识别"初始浓度/溶液体积/树脂质量"等输入
    flat_meta: dict[str, Any] = {}

    for path, draft in drafts.items():
        field = index.get(path)
        if not field:
            continue
        value = draft.get("value")
        if value in (None, ""):
            continue
        bucket = meta.setdefault(field["sheet_id"], {})
        key = path.split(".", 1)[-1]
        bucket[key] = {
            "label": field["label"],
            "value": value,
            "unit": draft.get("unit") or field.get("unit"),
        }
        flat_meta[key] = value
        provenance[path] = {
            "source_type": draft.get("source_type") or "manual",
            "source_ref": draft.get("source_ref"),
            "raw_text": draft.get("raw_text"),
            "confidence": draft.get("confidence"),
            "status": draft.get("status"),
        }

    # 科学计算：从 Raw 重读数值 -> 标定拟合 -> 浓度/单位换算 -> 规范长表。
    # 计算失败绝不阻断归档（与识别阶段的降级策略一致），而是把失败原因写进 docs。
    canonical: dict | None = None
    if raw_path and (recognized or {}).get("regions"):
        try:
            canonical = build_canonical(raw_path, recognized or {}, experiment_id, flat_meta)
        except Exception as exc:  # noqa: BLE001
            canonical = {
                "schema": "canonical_table_v1",
                "error": f"规范表格生成失败：{str(exc)[:200]}",
                "columns": [],
                "rows": [],
                "calculations": [],
                "verification": [],
                "notes": ["计算链路异常，已保留识别数据供人工核对"],
            }

    return {
        "schema": "canonical_v1",
        "template_id": template["template_id"],
        "template_version": template["version"],
        "experiment_id": experiment_id,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "raw_file": raw_file,
        "metadata": meta,
        "recognized_data": recognized or None,
        "canonical": canonical,
        "provenance": provenance,
    }


def render_markdown(doc: dict) -> str:
    lines = [f"# 实验规范文档 {doc['experiment_id']}", ""]
    lines.append(f"- 模板：{doc['template_id']} v{doc['template_version']}")
    lines.append(f"- 生成时间：{doc['generated_at']}")
    lines.append(f"- 原始文件：{doc.get('raw_file') or '（未上传）'}")
    lines.append("")

    for sheet_id, fields in (doc.get("metadata") or {}).items():
        lines.append(f"## {sheet_id}")
        lines.append("")
        lines.append("| 字段 | 值 | 单位 |")
        lines.append("| --- | --- | --- |")
        for key, item in fields.items():
            lines.append(f"| {item['label']} | {item['value']} | {item.get('unit') or '—'} |")
        lines.append("")

    recognized = doc.get("recognized_data") or {}
    regions = recognized.get("regions") or []
    if regions:
        lines.append("## 识别数据")
        lines.append("")
        for region in regions:
            lines.append(f"### {region.get('kindLabel') or region.get('kind')}")
            lines.append("")
            for block in region.get("blocks") or []:
                lines.append(f"- 列块 `{block.get('id')}`，目标离子 {block.get('analyte') or '—'}")
                for col in block.get("columns") or []:
                    lines.append(
                        f"  - {col.get('col')}: {col.get('raw') or '（空）'} → "
                        f"{col.get('field') or '未映射'}（置信度 {col.get('conf')}）"
                    )
            lines.append("")

    canonical = doc.get("canonical") or {}
    if canonical.get("error"):
        lines.append("## 规范表格")
        lines.append("")
        lines.append(f"- {canonical['error']}")
        lines.append("")

    if canonical.get("rows"):
        lines.append("## 规范表格")
        lines.append("")
        lines.append(f"- 表结构：{canonical.get('schema')} / {canonical.get('version')}")
        lines.append(f"- 观测行数：{len(canonical.get('rows') or [])}")
        lines.append("")
        lines.append(render_canonical_markdown(canonical, max_rows=30))
        lines.append("")

    calculations = canonical.get("calculations") or []
    if calculations:
        lines.append("## 自动计算与推导")
        lines.append("")
        for item in calculations:
            kind = item.get("type")
            block = item.get("block") or ""
            if kind == "calibration_fit":
                fit = item.get("fit") or {}
                if item.get("ok"):
                    lines.append(
                        f"- 标定拟合 `{block}`（{item.get('analyte') or '—'}）："
                        f"{fit.get('equation')}，R² = {fit.get('r2')}，n = {fit.get('n')}"
                    )
                else:
                    lines.append(f"- 标定拟合 `{block}` 未执行：{item.get('reason')}")
            elif kind == "calibration_attribution":
                lines.append(
                    f"- 标定归属 `{block}`：{item.get('selection_method')}，"
                    f"采用 `{item.get('chosen') or '未选定'}`"
                    "（文件未显式声明归属，由复算一致性推断，需人工确认）"
                )
                for candidate in item.get("candidates") or []:
                    lines.append(
                        f"  - 候选 `{candidate.get('block')}`：平均相对偏差 "
                        f"{candidate.get('mean_abs_relative_deviation')}"
                        f"（{candidate.get('n_scored')} 点，R² = {candidate.get('r2')}）"
                    )
            elif kind == "adsorption_capacity":
                if item.get("ok"):
                    inputs = item.get("inputs") or {}
                    lines.append(
                        f"- 吸附容量 `{block}`：q = {item.get('q_mg_g')} mg/g"
                        f"（C0={inputs.get('C0_mg_l')} mg/L，Ce={inputs.get('Ce_mg_l')} mg/L，"
                        f"V={inputs.get('volume_ml')} mL，m={inputs.get('resin_mass_mg')} mg；"
                        f"Ce 来源 {item.get('equilibrium_source')}）"
                    )
                else:
                    lines.append(f"- 吸附容量 `{block}` 未计算：{item.get('reason')}")
        lines.append("")

    summary = canonical.get("summary")
    if summary:
        lines.append("## 复算一致性（引擎 vs 表内自算）")
        lines.append("")
        lines.append(f"- 对照点数：{summary.get('n')}")
        lines.append(f"- 平均相对偏差：{summary.get('mean_relative_deviation')}")
        lines.append(f"- 最大绝对相对偏差：{summary.get('max_abs_relative_deviation')}")
        lines.append("")

    if canonical.get("assumptions"):
        lines.append("## 计算假设")
        lines.append("")
        for item in canonical["assumptions"]:
            lines.append(f"- {item}")
        lines.append("")

    if canonical.get("notes"):
        lines.append("## 未计算项与提示")
        lines.append("")
        for item in canonical["notes"]:
            lines.append(f"- {item}")
        lines.append("")

    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# AI 成长报告：本人归档上下文裁剪 + 结构化输出校验
# --------------------------------------------------------------------------- #

GROWTH_SYSTEM = (
    "你是 ExpResin 的实验成长复盘助手。你分析的是实验员的真实归档，"
    "负责区分实验记录质量、数据复核习惯、实验设计与结果解释。"
    "只能依据输入证据表达观察，禁止把实验数量增加直接等同于能力提升，"
    "禁止编造未提供的对照、评价或实验结果。结论不确定时明确标记数据不足。"
    "所有内容使用简体中文，只输出 JSON 对象。"
)

GROWTH_ROW_KEYS = (
    "kind", "analyte", "sample_number", "bed_volume", "volume_ml", "signal_area",
    "dilution_factor", "conc_ppm_reported", "conc_ppm_computed", "conc_mg_l_computed",
    "deviation_ppm", "removal_rate", "extrapolated", "method", "confidence",
)
GROWTH_DIRECTIONS = {"progress", "steady", "needs_attention", "insufficient_data"}


def _text(value: Any, limit: int = 240) -> str:
    if not isinstance(value, (str, int, float)):
        return ""
    text = str(value).strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _compact(value: Any, depth: int = 0) -> Any:
    """限制模型上下文中的字符串、列表与嵌套深度；数值保留原类型。"""
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return _text(value)
    if depth >= 4:
        return _text(value)
    if isinstance(value, list):
        return [_compact(item, depth + 1) for item in value[:12]]
    if isinstance(value, dict):
        return {str(key): _compact(item, depth + 1) for key, item in list(value.items())[:24]}
    return _text(value)


def _string_list(value: Any, max_items: int, max_length: int = 360) -> list[str]:
    if not isinstance(value, list):
        return []
    result = []
    for item in value:
        text = _text(item, max_length)
        if text:
            result.append(text)
        if len(result) >= max_items:
            break
    return result


def _growth_experiment(experiment: dict) -> dict:
    processed = experiment.get("processed") or {}
    metadata = processed.get("metadata") or {}
    metadata_items = []
    metadata_count = 0
    for sheet_id, fields in metadata.items():
        if not isinstance(fields, dict):
            continue
        metadata_count += len(fields)
        for key, item in fields.items():
            if not isinstance(item, dict):
                continue
            value = _text(item.get("value"), 160)
            if not value:
                continue
            metadata_items.append({
                "field": f"{sheet_id}.{key}",
                "label": _text(item.get("label") or key, 80),
                "value": value,
                "unit": _text(item.get("unit"), 24),
            })
    metadata_items = metadata_items[:24]

    status_counts: dict[str, int] = {}
    for item in (processed.get("provenance") or {}).values():
        if not isinstance(item, dict):
            continue
        status = _text(item.get("status") or "unknown", 32)
        status_counts[status] = status_counts.get(status, 0) + 1

    recognized_columns = 0
    confidences = []
    for region in (processed.get("recognized_data") or {}).get("regions") or []:
        for block in region.get("blocks") or []:
            for col in block.get("columns") or []:
                recognized_columns += 1
                try:
                    confidences.append(float(col.get("conf")))
                except (TypeError, ValueError):
                    pass

    canonical = processed.get("canonical") or {}
    rows = canonical.get("rows") or []
    if len(rows) > 6:
        row_samples = rows[:4] + rows[-2:]
    else:
        row_samples = rows[:6]
    compact_rows = []
    for row in row_samples:
        if not isinstance(row, dict):
            continue
        compact_rows.append({
            key: _compact(row.get(key))
            for key in GROWTH_ROW_KEYS
            if row.get(key) not in (None, "")
        })

    return {
        "experiment_id": experiment.get("id"),
        "title": _text(experiment.get("title"), 160),
        "experiment_type": _text(experiment.get("experiment_type"), 60),
        "date": _text(experiment.get("date_start"), 20),
        "record": {
            "metadata_field_count": metadata_count,
            "provenance_status_counts": status_counts,
            "recognized_column_count": recognized_columns,
            "mean_mapping_confidence": (
                round(sum(confidences) / len(confidences), 3) if confidences else None
            ),
        },
        "metadata": metadata_items,
        "data": {
            "raw_file_uploaded": bool(experiment.get("raw_file")),
            "canonical_row_count": len(rows),
            "canonical_error": _text(canonical.get("error"), 240),
            "row_samples": compact_rows,
            "calculations": _compact((canonical.get("calculations") or [])[:8]),
            "verification": _compact((canonical.get("verification") or [])[:8]),
            "summary": _compact(canonical.get("summary")),
            "assumptions": _string_list(canonical.get("assumptions"), 6),
            "notes": _string_list(canonical.get("notes"), 6),
        },
        "quality_warnings": _string_list(
            [item.get("message") for item in experiment.get("warnings") or []], 6
        ),
    }


def _growth_statistics(experiments: list[dict]) -> dict:
    by_type: dict[str, int] = {}
    canonical_rows = 0
    without_canonical = 0
    for experiment in experiments:
        kind = _text(experiment.get("experiment_type") or "未分类", 60)
        by_type[kind] = by_type.get(kind, 0) + 1
        rows = ((experiment.get("processed") or {}).get("canonical") or {}).get("rows") or []
        canonical_rows += len(rows)
        if not rows:
            without_canonical += 1
    return {
        "experiment_count": len(experiments),
        "with_raw_data_count": sum(bool(item.get("raw_file")) for item in experiments),
        "canonical_row_count": canonical_rows,
        "experiments_without_canonical": without_canonical,
        "warning_count": sum(len(item.get("warnings") or []) for item in experiments),
        "by_experiment_type": by_type,
    }


def _growth_goals(value: Any) -> list[dict]:
    if not isinstance(value, list):
        return []
    goals = []
    for item in value:
        if not isinstance(item, dict):
            continue
        title = _text(item.get("title"), 120)
        action = _text(item.get("action"), 500)
        metric = _text(item.get("metric"), 360)
        if not (title and action and metric):
            continue
        goals.append({
            "title": title,
            "action": action,
            "metric": metric,
            "timeframe": _text(item.get("timeframe"), 60),
        })
        if len(goals) >= 5:
            break
    return goals


def generate_growth_report(client: LLMClient, experiments: list[dict], focus: str = "") -> dict:
    """基于已经由路由严格限定归属的档案生成成长报告。

    路由负责 owner_user_id；这里不再接受任何用户 ID 或自由系统提示词。
    统计与实验时间线标题由 Python 回填，模型只负责语义判断。
    """
    ordered = sorted(
        experiments,
        key=lambda item: (item.get("date_start") or item.get("created_at") or "", item.get("id") or ""),
    )
    contexts = [_growth_experiment(item) for item in ordered]
    payload = json.dumps({"experiments": contexts}, ensure_ascii=False, separators=(",", ":"))
    if len(payload) > 90000:
        # 大档案集优先保留所有实验，减少单次样本而不是截掉后面的成长经历。
        for context in contexts:
            context["metadata"] = context["metadata"][:16]
            context["data"]["row_samples"] = context["data"]["row_samples"][:2]
            context["data"]["calculations"] = context["data"]["calculations"][:4]
        payload = json.dumps({"experiments": contexts}, ensure_ascii=False, separators=(",", ":"))

    focus_text = _text(focus, 160)
    prompt = f"""请基于以下当前实验员的归档数据，生成一份阶段性成长报告。

【分析侧重】
{focus_text or "未指定额外侧重；请平衡分析记录、复核、设计与数据解释。"}
（这只是复盘侧重，不是可以当作实验事实的新信息。）

【本人实验数据：按时间升序】
{payload}

【必须遵守】
1. 整体总结要区分“记录更完整、复核更规范、数据表现更好”等不同含义，不空泛表扬。
2. timeline 必须为输入中的每一个 experiment_id 各给一条观察；日期和标题无需输出，由系统回填。
3. 每条观察说明本次体现的学习或进步；证据不足时 direction 用 insufficient_data，不强行判断成长。
4. evidence 只引用输入中真实存在的字段、数据质量或计算信息，不编造数值。
5. goals 给出 3–5 个后续目标，每个都有可执行 action、可检查 metric 和建议 timeframe。
6. 如果数据缺口影响判断，写入 data_gaps；不要把缺口隐瞒成确定结论。
7. 只输出以下 JSON 结构，不要 Markdown：
{{
  "summary": "整体成长总结",
  "strengths": ["已有优势"],
  "timeline": [
    {{"experiment_id": "输入中的准确编号", "direction": "progress | steady | needs_attention | insufficient_data", "observation": "本次成长观察", "evidence": "记录依据"}}
  ],
  "goals": [
    {{"title": "目标", "action": "具体行动", "metric": "验收方式", "timeframe": "建议周期"}}
  ],
  "data_gaps": ["数据限制"]
}}"""

    parsed, response = client.chat_json(
        [
            {"role": "system", "content": GROWTH_SYSTEM},
            {"role": "user", "content": prompt},
        ],
        tier="pro",
        temperature=0.1,
        max_tokens=8192,
        timeout=120,
        max_retries=2,
    )
    summary = _text((parsed or {}).get("summary"), 3200)
    goals = _growth_goals((parsed or {}).get("goals"))
    if not summary or not goals:
        raise ValueError("AI 返回的报告缺少整体总结或有效提升目标，请重试")

    raw_timeline = {}
    for item in (parsed or {}).get("timeline") or []:
        if not isinstance(item, dict):
            continue
        experiment_id = _text(item.get("experiment_id"), 80)
        if experiment_id and experiment_id not in raw_timeline:
            raw_timeline[experiment_id] = item

    timeline = []
    for context in contexts:
        experiment_id = context["experiment_id"]
        item = raw_timeline.get(experiment_id, {})
        observation = _text(item.get("observation"), 800)
        direction = _text(item.get("direction"), 32)
        if direction not in GROWTH_DIRECTIONS:
            direction = "insufficient_data"
        if not observation:
            direction = "insufficient_data"
            observation = "本次记录可用于成长判断的信息不足，暂不作能力推断。"
        timeline.append({
            "experiment_id": experiment_id,
            "title": context["title"],
            "date": context["date"],
            "direction": direction,
            "observation": observation,
            "evidence": _text(item.get("evidence"), 500),
        })

    dates = sorted(item["date"] for item in contexts if item["date"])
    return {
        "schema_version": "growth_report_v1",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "scope": {
            "experiment_ids": [item["experiment_id"] for item in contexts],
            "experiment_count": len(contexts),
            "date_from": dates[0] if dates else None,
            "date_to": dates[-1] if dates else None,
        },
        "statistics": _growth_statistics(experiments),
        "summary": summary,
        "strengths": _string_list((parsed or {}).get("strengths"), 4),
        "timeline": timeline,
        "goals": goals,
        "data_gaps": _string_list((parsed or {}).get("data_gaps"), 6),
        "model": {"name": response.model},
    }
