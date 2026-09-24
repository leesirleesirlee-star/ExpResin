"""L3/L4 语义映射层：检索增强 + Trace as State 两轮推理 + 置信度与证据输出。

映射单元是 **ColumnBlock**（而非整个 Sheet），原因：
一个 Region 里可能并排存在多个独立子表（例如 SO4 标定表与 Cl 标定表），
只有按列分组分别映射，才能正确区分语义。

两轮推理（Trace as State，落实 PRD 4.2）：
    pass1: 结构化列块 -> LLM -> 阅读笔记 (reasoning trace)
    pass2: 笔记 + 结构化列块 + 标准 Schema -> LLM -> 列级映射 JSON
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from l1_structure import ColumnBlock, DataRegion

from llm import LLMClient, LLMResponse

# --------------------------------------------------------------------------- #
# 数据结构
# --------------------------------------------------------------------------- #


@dataclass
class ColumnMapping:
    col_letter: str
    raw_header: str
    target_field: str | None
    confidence: float
    evidence: str


@dataclass
class BlockMapping:
    block_id: str
    region_id: str
    sheet_name: str
    block_kind: str
    block_kind_confidence: float
    analyte: str | None
    columns: list[ColumnMapping] = field(default_factory=list)
    trace_notes: str | None = None
    model: str = ""
    usage: dict[str, Any] = field(default_factory=dict)


# --------------------------------------------------------------------------- #
# Schema 与 Prompt 构造
# --------------------------------------------------------------------------- #


def load_schema(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _schema_digest(schema: dict) -> str:
    """把 Schema 压缩成 prompt 友好的字段清单。"""
    lines = []
    for kind, spec in schema["block_kinds"].items():
        fields = ", ".join(f"{f['key']}({f['label']})" for f in spec["target_fields"])
        lines.append(f"- {kind} [{spec['label']}]: {fields}")
    return "\n".join(lines)


def _fmt_value(v: Any) -> str:
    if isinstance(v, float):
        return f"{v:.6g}"
    return str(v)


def _block_digest(block: ColumnBlock) -> str:
    """把列块压缩成结构化摘要，供模型阅读（不含原始整表）。"""
    lines = [f"列范围: {block.col_letters}"]
    for c in block.columns:
        rng = ""
        if c.numeric_range:
            rng = f" 数值范围=[{_fmt_value(c.numeric_range[0])}, {_fmt_value(c.numeric_range[1])}]"
        samples = ", ".join(_fmt_value(v) for v in c.sample_values[:4])
        lines.append(
            f"  列{c.col_letter}: 表头={c.raw_header or '<空>'!r} | 类型={c.value_type} | "
            f"单位={c.unit or '未识别'} | 填充率={c.fill_ratio}{rng} | 样本=[{samples}]"
        )
    return "\n".join(lines)


def _context_digest(region: DataRegion) -> str:
    return (
        f"数据块标题: {region.title or '<无>'}\n"
        f"启发式类型: {region.region_kind}\n"
        f"位置: 表头行 {region.header_rows}，数据行 {region.data_start_row}-{region.data_end_row}\n"
        f"数据规模: {region.row_count} 行"
    )


# --------------------------------------------------------------------------- #
# 两轮推理
# --------------------------------------------------------------------------- #


# 单块映射的时延预算：单次 90s × 2 次尝试 ≈ 最坏 3 分钟。
# 配合"列块并行"，整体上传可稳定落在浏览器超时预算之内。
MAPPING_TIMEOUT = 90.0
MAPPING_RETRIES = 2


def _pass1_notes(client: LLMClient, block: ColumnBlock, region: DataRegion) -> LLMResponse:
    """第一轮：只产出阅读笔记（Reasoning Trace），不做最终判定。"""
    system = "你是实验数据理解专家。你的任务是阅读一份实验表格片段并写下简短的观察笔记。"
    user = f"""下面是一个真实离子交换实验 Excel 中切分出的一个数据列块。

【上下文】
{_context_digest(region)}

【列块结构】
{_block_digest(block)}

请用 3~6 句话写下你的"阅读笔记"，覆盖：
1. 这个列块整体在记录什么（标定曲线？样品测量？容量？pH 曲线？）；
2. 每一列最可能的物理量含义；
3. 你判断的依据（列名、单位、数值范围、样本值）；
4. 你不确定的地方。

只输出笔记正文，不要输出 JSON，不要下最终结论。"""
    return client.chat(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        tier="flash",
        max_tokens=2000,
        timeout=MAPPING_TIMEOUT,
        max_retries=MAPPING_RETRIES,
    )


def _pass2_map(
    client: LLMClient, block: ColumnBlock, region: DataRegion, schema: dict, notes: str | None
) -> tuple[dict, LLMResponse]:
    """第二轮：带着笔记做列级映射，输出严格 JSON。"""
    system = (
        "你是实验数据 Schema 映射专家。你只做语义映射，不做数值计算，不猜测不确定的内容。"
        "必须严格输出 JSON。"
    )
    example = {
        "block_kind": "calibration",
        "block_kind_confidence": 0.95,
        "analyte": "SO4",
        "columns": [
            {
                "col_letter": "B",
                "target_field": "signal_area",
                "confidence": 0.97,
                "evidence": "列名 area，数值范围 0~29，符合仪器信号特征",
            }
        ],
    }
    notes_section = f"\n【上一轮的阅读笔记（Reasoning Trace）】\n{notes}\n" if notes else ""
    user = f"""请把给定的实验表格列块映射到标准 Schema。

【标准 Schema 可用的 block_kind 与字段】
{_schema_digest(schema)}

【待映射列块】
{_context_digest(region)}

列清单:
{_block_digest(block)}
{notes_section}
【任务】
1. 判断 block_kind（只能取上面列出的 kind 之一）。
2. 若是标定或与某离子相关，给出 analyte（如 SO4、Cl、NH4+、Li+、Ca、HPO4），否则为 null。
3. 为每一列指定 target_field（必须是该 block_kind 下的字段 key；无法对应时填 null）。
4. 每列给出 confidence(0~1) 与 evidence（引用列名/单位/数值范围的证据）。
5. 严禁猜测：若证据不足，confidence 必须低于 0.6。
6. confidence 表示"该列确实对应此字段"的把握，不是数值准确度。

【输出 JSON 格式示例】
{json.dumps(example, ensure_ascii=False)}

只输出 JSON。"""
    return client.chat_json(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        tier="pro",
        # 映射输出本身很短，但 V4 推理模型的 reasoning 同样计入 completion 配额。
        # 4096 会周期性触发「截断 → 翻倍重试」，实测把单块耗时从 ~45s 拖到 93s，故直接用 8192。
        max_tokens=8192,
        timeout=MAPPING_TIMEOUT,
        max_retries=MAPPING_RETRIES,
    )


def map_block(
    client: LLMClient,
    block: ColumnBlock,
    region: DataRegion,
    schema: dict,
    sheet_name: str,
    use_trace: bool = False,
) -> BlockMapping:
    """映射一个列块。

    use_trace=False（默认）：单轮映射。DeepSeek V4 自带 reasoning，已具备"先思考再回答"
        的能力，单轮即可保证质量，同时避免长 prompt 下推理链失控。
    use_trace=True：显式两轮推理（Trace as State），用于 PRD 要求的对比实验。
    """
    trace_resp = None
    notes: str | None = None
    if use_trace:
        trace_resp = _pass1_notes(client, block, region)
        notes = trace_resp.content.strip()
    result, map_resp = _pass2_map(client, block, region, schema, notes)

    columns = []
    for item in result.get("columns", []) or []:
        columns.append(
            ColumnMapping(
                col_letter=str(item.get("col_letter", "")).strip(),
                raw_header=str(item.get("raw_header", "") or ""),
                target_field=item.get("target_field") or None,
                confidence=float(item.get("confidence", 0.0) or 0.0),
                evidence=str(item.get("evidence", "") or ""),
            )
        )

    usage = {}
    for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
        usage[key] = map_resp.usage.get(key, 0) + (
            trace_resp.usage.get(key, 0) if trace_resp else 0
        )

    return BlockMapping(
        block_id=block.block_id,
        region_id=region.region_id,
        sheet_name=sheet_name,
        block_kind=str(result.get("block_kind", "unknown")),
        block_kind_confidence=float(result.get("block_kind_confidence", 0.0) or 0.0),
        analyte=result.get("analyte") or None,
        columns=columns,
        trace_notes=notes,
        model=map_resp.model,
        usage=usage,
    )


# --------------------------------------------------------------------------- #
# L5 证据校验（规则层，兜底）
# --------------------------------------------------------------------------- #


def validate_mapping(mapping: BlockMapping, block: ColumnBlock, schema: dict) -> list[str]:
    """对映射结果做确定性校验，返回问题列表。

    校验项：
    1. block_kind 必须存在于 Schema；
    2. 必需字段是否被覆盖；
    3. 同一目标字段是否被重复映射；
    4. 目标字段单位与原列单位是否冲突（若有单位）。
    """
    issues: list[str] = []

    spec = schema["block_kinds"].get(mapping.block_kind)
    if not spec:
        issues.append(f"block_kind '{mapping.block_kind}' 不在标准 Schema 中")
        return issues

    field_specs = {f["key"]: f for f in spec["target_fields"]}
    mapped = [c for c in mapping.columns if c.target_field]

    for c in mapped:
        if c.target_field not in field_specs:
            issues.append(f"列{c.col_letter}: 目标字段 '{c.target_field}' 不属于 block_kind '{mapping.block_kind}'")

    for c in mapped:
        spec_field = field_specs.get(c.target_field or "")
        col = next((x for x in block.columns if x.col_letter == c.col_letter), None)
        if spec_field and col and spec_field.get("unit") and col.unit and spec_field["unit"] != col.unit:
            issues.append(
                f"列{c.col_letter}: 单位冲突（列单位 {col.unit} vs 标准单位 {spec_field['unit']}）"
            )

    required = [f["key"] for f in spec["target_fields"] if f.get("required")]
    covered = {c.target_field for c in mapped}
    # 目标离子可由块级 analyte 提供（标定表通常没有独立的 analyte 列，而是写在表头标签列）
    if mapping.analyte:
        covered.add("analyte")
    missing = [k for k in required if k not in covered]
    if missing:
        issues.append(f"缺少必需字段: {', '.join(missing)}")

    seen: dict[str, str] = {}
    for c in mapped:
        key = c.target_field or ""
        if key in seen:
            issues.append(f"目标字段 '{key}' 被列{seen[key]}与列{c.col_letter}重复映射")
        else:
            seen[key] = c.col_letter

    return issues


def mapping_to_dict(mapping: BlockMapping) -> dict:
    return asdict(mapping)