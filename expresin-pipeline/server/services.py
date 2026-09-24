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