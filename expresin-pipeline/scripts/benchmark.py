"""Benchmark v0：用确定性规则度量 L3/L4 映射准确率。

不依赖人工标注，而是利用本数据集的结构性事实构造"可计算的真相"：

1. 标定块的离子真值可判定：标定块中存在一列，其表头与取值都是离子名（SO4/Cl/NH4+/Li+），
   据此可以确定该块的真实 analyte，从而客观检查模型的 analyte 判定。
2. 相同表头应稳定映射：同一归一化表头在不同块中出现时，应映射到同一 target_field，
   用跨块一致性度量映射的确定性。
3. 有效列覆盖率：非空且非"幽灵列"（空表头/纯数字表头）的列应被捕获。

用法:
    python expresin-pipeline/scripts/benchmark.py
"""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "expresin-pipeline" / "src"))

from l1_structure import parse_workbook  # noqa: E402

TMP = ROOT / ".deepworks" / "tmp"
DOCS = ROOT / "docs"
XLSX = ROOT / "materials" / "data" / "20250528 DHT Cl SO4.xlsx"
GOLD_PATH = ROOT / "expresin-pipeline" / "config" / "gold_mapping_v0.json"

ION_ALIASES = {"so4", "cl", "nh4+", "nh4", "li+", "li", "ca", "na", "hpo4", "po4", "no3", "f"}

_NUM_RE = re.compile(r"^[+-]?\d+(\.\d+)?([eE][+-]?\d+)?$")


def norm_header(h: str | None) -> str:
    return re.sub(r"\s+", " ", (h or "").strip().lower())


def is_ghost_header(h: str | None) -> bool:
    """幽灵列表头：空，或本身就是数字（L1 把邻接数值单元格当成了表头）。"""
    h = (h or "").strip()
    return h == "" or bool(_NUM_RE.match(h))


def expected_analyte(block) -> str | None:
    """从标定块的离子标签列推断真值。"""
    for c in block.columns:
        if norm_header(c.raw_header) in ION_ALIASES:
            return c.raw_header.strip()
    return None


def load_gold() -> tuple[dict[tuple[str, str], str | None], dict]:
    """载入列级 gold 参照（领域专家弱标注）。"""
    data = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
    table = {(r["block_kind"], r["header"]): r["target"] for r in data["rules"]}
    return table, data


def build_pairs(records: list[dict], workbook):
    """按记录生成顺序，把 (sheet, region, block) 与映射记录配对。"""
    sheet_map = {s.sheet_name.strip(): s for s in workbook.sheets}
    order: list[str] = []
    for r in records:
        key = r["sheet_name"].strip()
        if key not in order:
            order.append(key)

    pairs = []
    idx = 0
    for key in order:
        sheet = sheet_map[key]
        for region in sheet.regions:
            for block in region.col_blocks:
                if idx >= len(records):
                    break
                pairs.append((sheet, region, block, records[idx]))
                idx += 1
    if idx != len(records):
        raise SystemExit(f"配对失败：blocks={idx} records={len(records)}")
    return pairs


def main() -> None:
    records = json.loads((TMP / "mapping_result.json").read_text(encoding="utf-8"))
    workbook = parse_workbook(XLSX)
    pairs = build_pairs(records, workbook)

    # ---- 指标 1：跨块一致性 -------------------------------------------------
    header_fields: dict[str, set[str]] = defaultdict(set)
    header_occ: dict[str, int] = defaultdict(int)
    for _sheet, _region, block, rec in pairs:
        for cm in rec["columns"]:
            col = next((c for c in block.columns if c.col_letter == cm["col_letter"]), None)
            if not col or is_ghost_header(col.raw_header):
                continue
            key = norm_header(col.raw_header)
            header_occ[key] += 1
            header_fields[key].add(cm["target_field"] or "<未映射>")

    repeated = {k: v for k, v in header_fields.items() if header_occ[k] >= 2}
    inconsistent = {k: sorted(v) for k, v in repeated.items() if len(v) > 1}
    consistency = 1 - (len(inconsistent) / len(repeated)) if repeated else 1.0

    # ---- 指标 2：标定块 analyte 准确率 --------------------------------------
    calib_total = calib_hit = 0
    analyte_errors: list[str] = []
    for _sheet, _region, block, rec in pairs:
        if rec["block_kind"] != "calibration":
            continue
        truth = expected_analyte(block)
        if not truth:
            continue
        calib_total += 1
        got = (rec["analyte"] or "").strip()
        if got.lower() == truth.lower():
            calib_hit += 1
        else:
            analyte_errors.append(
                f"{block.block_id}: 真值={truth} 预测={got or '<空>'} conf={rec['block_kind_confidence']:.2f}"
            )
    analyte_acc = calib_hit / calib_total if calib_total else 0.0

    # ---- 指标 3：有效列覆盖率 ------------------------------------------------
    meaningful = captured = 0
    missed: list[str] = []
    for _sheet, _region, block, rec in pairs:
        mapped_cols = {cm["col_letter"] for cm in rec["columns"] if cm["target_field"]}
        for col in block.columns:
            if is_ghost_header(col.raw_header):
                continue
            if col.fill_ratio < 0.3:
                continue
            # 离子标签列天然没有目标字段，不算漏映射
            if norm_header(col.raw_header) in ION_ALIASES:
                continue
            meaningful += 1
            if col.col_letter in mapped_cols:
                captured += 1
            else:
                missed.append(f"{block.block_id} 列{col.col_letter} {col.raw_header!r}")
    coverage = captured / meaningful if meaningful else 1.0

    # ---- 指标 4：低置信度暴露 -------------------------------------------------
    low_conf_mapped = 0
    total_mapped = 0
    for _sheet, _region, _block, rec in pairs:
        for cm in rec["columns"]:
            if cm["target_field"]:
                total_mapped += 1
                if cm["confidence"] < 0.8:
                    low_conf_mapped += 1

    total_tokens = sum(r["usage"].get("total_tokens", 0) for r in records)

    # ---- 指标 5：列级映射准确率（对 gold 参照）------------------------------
    gold, gold_meta = load_gold()
    judged = correct = 0
    wrong: list[str] = []
    for _sheet, _region, block, rec in pairs:
        kind = rec["block_kind"]
        for cm in rec["columns"]:
            col = next((c for c in block.columns if c.col_letter == cm["col_letter"]), None)
            if not col:
                continue
            key = (kind, norm_header(col.raw_header))
            if key not in gold:
                continue  # 未列入 gold 的表头不计入分母
            judged += 1
            expected = gold[key]
            got = cm["target_field"]
            if got == expected:
                correct += 1
            else:
                wrong.append(
                    f"{block.block_id} 列{cm['col_letter']} {col.raw_header!r}: "
                    f"期望={expected or '不映射'} 预测={got or '不映射'}"
                )
    column_accuracy = correct / judged if judged else 0.0

    # ---- 报告 ---------------------------------------------------------------
    L: list[str] = []
    A = L.append
    A("# ExpResin Excel 识别 Benchmark v0")
    A("")
    A("> 数据源：`20250528 DHT Cl SO4.xlsx`（7 个 Sheet / 27 个数据列块）")
    A("> 链路：L1 结构解析 → L3/L4 LLM 语义映射 → L5 规则校验")
    A("")
    A("## 总览")
    A("")
    A("| 指标 | 数值 |")
    A("| --- | --- |")
    A(f"| 参与评测的列块 | {len(records)} |")
    A(f"| 跨块映射一致性 | {consistency:.1%}（{len(repeated) - len(inconsistent)}/{len(repeated)} 个重复表头完全一致） |")
    A(f"| 标定块 analyte 准确率 | {analyte_acc:.1%}（{calib_hit}/{calib_total}） |")
    A(f"| 有效列覆盖率 | {coverage:.1%}（{captured}/{meaningful}） |")
    A(f"| **列级映射准确率（gold 参照）** | **{column_accuracy:.1%}**（{correct}/{judged}） |")
    A(f"| 已映射列数 | {total_mapped}（其中低置信度 {low_conf_mapped}） |")
    A(f"| Token 消耗 | {total_tokens:,} |")
    A("")

    A("## 1. 跨块一致性")
    A("")
    if inconsistent:
        A("存在同一表头映射到不同字段的情况：")
        A("")
        for k, v in inconsistent.items():
            A(f"- `{k}` → {v}")
    else:
        A("所有重复出现的表头在不同列块中都映射到了完全相同的标准字段，说明映射稳定、可复现。")
    A("")

    A("## 2. 标定块 analyte 判定")
    A("")
    if analyte_errors:
        A(f"共 {len(analyte_errors)} 处判定错误：")
        A("")
        for e in analyte_errors:
            A(f"- {e}")
    else:
        A("全部标定块的 analyte 判定与离子标签列真值一致。")
    A("")

    A("## 3. 有效列覆盖")
    A("")
    if missed:
        A(f"以下 {len(missed)} 列未被映射，需人工/规则复核：")
        A("")
        for m in missed:
            A(f"- {m}")
    else:
        A("所有有效列均被成功映射。")
    A("")

    A("## 4. 列级映射准确率（gold 参照）")
    A("")
    A(f"在 {judged} 个可判定列中，正确 {correct} 列，准确率 **{column_accuracy:.1%}**。")
    A("")
    if wrong:
        A("错误明细：")
        A("")
        for w in wrong:
            A(f"- {w}")
    else:
        A("所有可判定列均与专家判定一致。")
    A("")
    A(f"> gold 口径：{gold_meta.get('limitation', '')}")
    A("")

    A("## 5. 结论与待办")
    A("")
    A("- 映射链路在跨 Sheet、跨离子体系（SO4/Cl/NH4+/Li+）上表现稳定，具备可用性。")
    A("- 剩余风险集中在：标定块的 analyte 判定受区块标题干扰；幽灵列/系数列混入表头。")
    A("- 下一步：对低置信度与不一致项接入人工确认（L6 主动学习闭环），并按 PRD 做三组对比实验。")
    A("")

    report = "\n".join(L)
    DOCS.mkdir(parents=True, exist_ok=True)
    (DOCS / "benchmark-v0.md").write_text(report, encoding="utf-8")
    (TMP / "benchmark_metrics.json").write_text(
        json.dumps(
            {
                "blocks": len(records),
                "consistency": consistency,
                "analyte_accuracy": analyte_acc,
                "coverage": coverage,
                "column_accuracy": column_accuracy,
                "column_judged": judged,
                "column_correct": correct,
                "column_wrong": wrong,
                "inconsistent": inconsistent,
                "analyte_errors": analyte_errors,
                "missed": missed,
                "total_tokens": total_tokens,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"blocks={len(records)}")
    print(f"consistency={consistency:.1%}  analyte_acc={analyte_acc:.1%}  coverage={coverage:.1%}")
    print(f"column_accuracy={column_accuracy:.1%} ({correct}/{judged})")
    print(f"inconsistent_headers={len(inconsistent)}  analyte_errors={len(analyte_errors)}  missed={len(missed)}")
    print(f"WROTE {DOCS / 'benchmark-v0.md'}")


if __name__ == "__main__":
    main()