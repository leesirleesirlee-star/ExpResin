"""Benchmark 幻觉任务 v0：模板映射的幻觉探针与量化（W9 Benchmark 方向）。

设计：以三个实验记录模板（batch / column / electrochemical）的示例填写文件为
受控基线，构造语义扰动变体，量化 LLM 列映射在"语义证据缺失 / 语义证据冲突"
场景下的幻觉倾向与置信度校准表现：

  V0 baseline    原始示例（基线，列映射应全部命中 gold）
  V1 nonsense    表头替换为无语义符号（Metric_A/B/C…）→ 期望 target=null；
                 任何映射即为幻觉，conf≥0.8 记为高置信幻觉
  V2 swapped     表头循环移位、数据不动 → 区分"语义服从"（跟随新表头）与
                 "位置/数据惯性"（按列序/数值形态臆断）
  V3 headerless  清空表头行 → 首行数据成为幽灵数字表头，期望防护层拒绝映射
                 （宪法：无表头列不自动映射）

gold：config/record_templates/*_record_v1.json 的 data_columns（模板自带声明）。

用法:
    python expresin-pipeline/scripts/benchmark_hallucination.py [--only batch]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import openpyxl
from openpyxl.utils import column_index_from_string

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "expresin-pipeline" / "src"))

from l1_structure import parse_workbook  # noqa: E402
from llm import LLMClient, LLMConfig  # noqa: E402
from mapping import load_schema, map_block, mapping_to_dict  # noqa: E402

DATA_DIR = ROOT / "materials" / "record-templates"
CFG_DIR = ROOT / "expresin-pipeline" / "config" / "record_templates"
SCHEMA_PATH = ROOT / "expresin-pipeline" / "config" / "standard_schema.json"
TMP = ROOT / ".deepworks" / "tmp" / "hallucination"
DOCS = ROOT / "docs"

EXPERIMENTS = {
    "batch": ("Batch_Record_Template_v1_example_filled.xlsx", "batch_record_v1.json"),
    "column": ("Column_Record_Template_v1_example_filled.xlsx", "column_record_v1.json"),
    "electrochemical": (
        "Electrochemical_Record_Template_v1_example_filled.xlsx",
        "electrochemical_record_v1.json",
    ),
}

_NUM_RE = re.compile(r"^[+-]?\d+(\.\d+)?([eE][+-]?\d+)?$")


def norm(s: str | None) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def is_ghost(h: str | None) -> bool:
    h = (h or "").strip()
    return h == "" or bool(_NUM_RE.match(h))


def load_gold(cfg_name: str) -> dict[str, str]:
    spec = json.loads((CFG_DIR / cfg_name).read_text(encoding="utf-8"))
    return {norm(c["header"]): c["target_field"] for c in spec["data_columns"]}


def header_cells(path: Path) -> list[tuple[int, int, str]]:
    """返回原文件中全部数据块表头单元格 (row, col_idx, header)，供变体改造。"""
    wb_struct = parse_workbook(path)
    cells: list[tuple[int, int, str]] = []
    for sheet in wb_struct.sheets:
        for region in sheet.regions:
            row = region.header_rows[-1]
            for block in region.col_blocks:
                for col in block.columns:
                    cells.append((row, column_index_from_string(col.col_letter), col.raw_header))
    return cells


def build_variants(exp_type: str, src: Path) -> dict[str, Path]:
    """基于原文件构造 V0-V3 变体，返回 {variant: 路径}。"""
    TMP.mkdir(parents=True, exist_ok=True)
    cells = header_cells(src)
    out: dict[str, Path] = {}

    # V0 baseline：原样拷贝（直接用原文件）
    out["V0_baseline"] = src

    def _save(name: str, mutate) -> None:
        wb = openpyxl.load_workbook(src)
        ws = wb.worksheets[0]
        mutate(ws)
        dst = TMP / f"{exp_type}_{name}.xlsx"
        wb.save(dst)
        wb.close()
        out[name] = dst

    # V1 nonsense：表头 -> 无语义符号
    def _nonsense(ws) -> None:
        for i, (row, col_idx, _h) in enumerate(cells, start=1):
            ws.cell(row=row, column=col_idx).value = f"Metric_{i}"

    _save("V1_nonsense", _nonsense)

    # V2 swapped：表头循环移位（数据不动），逐行分组移位
    by_row: dict[int, list[tuple[int, str]]] = {}
    for row, col_idx, h in cells:
        by_row.setdefault(row, []).append((col_idx, h))

    def _swapped(ws) -> None:
        for row, items in by_row.items():
            items.sort()
            headers = [h for _c, h in items]
            shifted = headers[1:] + headers[:1]  # 循环左移
            for (col_idx, _h), new_h in zip(items, shifted):
                ws.cell(row=row, column=col_idx).value = new_h

    _save("V2_swapped", _swapped)

    # V3a headerless：清空表头行（预期 L1 整块拦截，不进入 LLM）
    def _headerless(ws) -> None:
        for row, col_idx, _h in cells:
            ws.cell(row=row, column=col_idx).value = None

    _save("V3a_headerless", _headerless)

    # V3b ghostnum：表头替换为纯数字（模拟 L1 误吞数据行当表头的幽灵列，
    # 数字表头会进入 LLM prompt，检测是否臆造映射）
    by_row3: dict[int, list[int]] = {}
    for row, col_idx, _h in cells:
        by_row3.setdefault(row, []).append(col_idx)

    def _ghostnum(ws) -> None:
        for row, cols in by_row3.items():
            cols.sort()
            for i, col_idx in enumerate(cols, start=1):
                ws.cell(row=row, column=col_idx).value = str(i)

    _save("V3b_ghostnum", _ghostnum)

    return out


def analyze(path: Path, client: LLMClient, schema: dict) -> list[dict]:
    """对一个工作簿跑完整映射，返回逐块记录（附列级明细）。"""
    workbook = parse_workbook(path)
    records: list[dict] = []
    for sheet in workbook.sheets:
        for region in sheet.regions:
            for block in region.col_blocks:
                mapping = map_block(client, block, region, schema, sheet.sheet_name)
                rec = mapping_to_dict(mapping)
                # 补充该列的原始表头（map 结果可能省略 raw_header）
                src_headers = {c.col_letter: c.raw_header for c in block.columns}
                for cm in rec["columns"]:
                    cm["src_header"] = src_headers.get(cm["col_letter"], "")
                records.append(rec)
    return records


def evaluate(exp_type: str, variants: dict[str, Path], gold: dict[str, str], results: dict[str, list[dict]]) -> dict:
    """按变体计算幻觉指标。"""
    summary: dict = {"experiment_type": exp_type, "variants": {}}

    # ---- V0：基线正确率 -----------------------------------------------------
    v0 = results["V0_baseline"]
    total = correct = 0
    for rec in v0:
        for cm in rec["columns"]:
            key = norm(cm.get("src_header") or cm.get("raw_header"))
            if key not in gold:
                continue
            total += 1
            if cm["target_field"] == gold[key]:
                correct += 1
    summary["variants"]["V0_baseline"] = {
        "gold_cols": total,
        "correct": correct,
        "accuracy": (correct / total) if total else 0.0,
    }

    # ---- V1：幻觉率 ---------------------------------------------------------
    v1 = results["V1_nonsense"]
    mapped = [cm for rec in v1 for cm in rec["columns"] if cm["target_field"]]
    hi_conf = [cm for cm in mapped if (cm["confidence"] or 0) >= 0.8]
    seen_cols = [cm for rec in v1 for cm in rec["columns"]]
    summary["variants"]["V1_nonsense"] = {
        "cols_seen": len(seen_cols),
        "mapped": len(mapped),
        "hallucination_rate": (len(mapped) / len(seen_cols)) if seen_cols else 0.0,
        "high_conf_hallucinations": [
            {
                "col": cm["col_letter"],
                "target": cm["target_field"],
                "conf": cm["confidence"],
                "evidence": (cm.get("evidence") or "")[:120],
            }
            for cm in hi_conf
        ],
    }

    # ---- V2：语义服从 vs 位置惯性 -------------------------------------------
    v2 = results["V2_swapped"]
    obey = inertia = other = unmapped = 0
    details = []
    for rec in v2:
        for cm in rec["columns"]:
            new_h = cm.get("src_header") or cm.get("raw_header") or ""
            sem_expected = gold.get(norm(new_h))  # 跟随新表头语义的期望
            if sem_expected is None:
                continue
            tgt = cm["target_field"]
            if tgt is None:
                unmapped += 1
                verdict = "unmapped"
            elif tgt == sem_expected:
                obey += 1
                verdict = "semantic-obey"
            else:
                inertia += 1
                verdict = "inertia/other"
            details.append(
                {
                    "col": cm["col_letter"],
                    "new_header": new_h,
                    "expect_if_semantic": sem_expected,
                    "got": tgt,
                    "conf": cm["confidence"],
                    "verdict": verdict,
                }
            )
    judged = obey + inertia
    summary["variants"]["V2_swapped"] = {
        "semantic_obey": obey,
        "inertia_or_other": inertia,
        "unmapped": unmapped,
        "semantic_obey_rate": (obey / judged) if judged else None,
        "details": details,
    }

    # ---- V3a：L1 层拦截（无表头整块消失） -----------------------------------
    v3a = results["V3a_headerless"]
    summary["variants"]["V3a_headerless"] = {
        "blocks_seen": len(v3a),
        "l1_blocked": len(v3a) == 0,
    }

    # ---- V3b：幽灵数字表头防护（LLM 层） -------------------------------------
    v3b = results["V3b_ghostnum"]
    ghost_cols = mapped_ghost = 0
    leaks = []
    for rec in v3b:
        for cm in rec["columns"]:
            h = cm.get("src_header") or cm.get("raw_header") or ""
            if not is_ghost(h):
                continue
            ghost_cols += 1
            if cm["target_field"]:
                mapped_ghost += 1
                leaks.append(
                    {"col": cm["col_letter"], "header": h, "target": cm["target_field"], "conf": cm["confidence"]}
                )
    summary["variants"]["V3b_ghostnum"] = {
        "blocks_seen": len(v3b),
        "l1_blocked": len(v3b) == 0,
        "ghost_cols": ghost_cols,
        "mapped_ghost": mapped_ghost,
        "guard_ok": mapped_ghost == 0,
        "leaks": leaks,
    }

    return summary


def render_report(summaries: list[dict], results: dict[str, dict[str, list[dict]]], tokens: int) -> str:
    lines: list[str] = []
    lines.append("# Benchmark 幻觉任务 v0（模板映射幻觉探针）\n")
    lines.append("- 任务卡：W9 Benchmark 方向「幻觉任务」（roadmap v2.0 §六）")
    lines.append("- 基线：`materials/record-templates/*_example_filled.xlsx`；gold：同模板 record_templates 声明")
    lines.append("- 模型链路：L1 parse_workbook → L3/L4 map_block（单轮，flash tier 默认）")
    lines.append(f"- 总 token 消耗：{tokens}\n")

    lines.append("## 变体设计\n")
    lines.append("| 变体 | 扰动 | 期望行为 | 幻觉判据 |")
    lines.append("|---|---|---|---|")
    lines.append("| V0 baseline | 无 | gold 全中 | 基线准确率 |")
    lines.append("| V1 nonsense | 表头→无语义符号 | 全部不映射 | 映射即幻觉；conf≥0.8 为高置信幻觉 |")
    lines.append("| V2 swapped | 表头循环移位、数据不动 | 跟随表头语义 | 语义服从率 vs 位置惯性 |")
    lines.append("| V3a headerless | 清空表头行 | L1 整块拦截、不进入 LLM | region 是否消失 |")
    lines.append("| V3b ghostnum | 表头→纯数字（幽灵列） | 拒绝映射 | 幽灵列被映射数 |\n")

    lines.append("## 总览\n")
    lines.append("| 模板 | V0 基线 | V1 幻觉率 | V1 高置信幻觉 | V2 语义服从率 | V3a L1 拦截 | V3b 幽灵防护 |")
    lines.append("|---|---|---|---|---|---|---|")
    for s in summaries:
        v0 = s["variants"]["V0_baseline"]
        v1 = s["variants"]["V1_nonsense"]
        v2 = s["variants"]["V2_swapped"]
        v3a = s["variants"]["V3a_headerless"]
        v3b = s["variants"]["V3b_ghostnum"]
        obey_txt = "—" if v2["semantic_obey_rate"] is None else f"{v2['semantic_obey_rate']:.0%}"
        v3a_txt = "✅ 整块拦截" if v3a["l1_blocked"] else f"⚠️ 仍产出 {v3a['blocks_seen']} 块"
        if v3b["l1_blocked"]:
            guard_txt = "✅ L1 拦截（未进 LLM）"
        elif v3b["guard_ok"]:
            guard_txt = "✅ LLM 拒映射"
        else:
            guard_txt = "❌ 泄漏 " + str(v3b["mapped_ghost"])
        lines.append(
            f"| {s['experiment_type']} | {v0['accuracy']:.0%}（{v0['correct']}/{v0['gold_cols']}） "
            f"| {v1['hallucination_rate']:.0%}（{v1['mapped']}/{v1['cols_seen']}） "
            f"| {len(v1['high_conf_hallucinations'])} "
            f"| {obey_txt} "
            f"| {v3a_txt} "
            f"| {guard_txt} |"
        )
    lines.append("")

    lines.append("## 明细\n")
    for s in summaries:
        exp = s["experiment_type"]
        lines.append(f"### {exp}\n")
        v1 = s["variants"]["V1_nonsense"]
        if v1["high_conf_hallucinations"]:
            lines.append("**V1 高置信幻觉（conf≥0.8）**：\n")
            for h in v1["high_conf_hallucinations"]:
                lines.append(f"- 列{h['col']} → `{h['target']}` conf={h['conf']:.2f} evidence：{h['evidence']}")
        else:
            lines.append("**V1**：无高置信幻觉。")
        lines.append("")
        v2 = s["variants"]["V2_swapped"]
        lines.append("**V2 逐列判定**：\n")
        lines.append("| 列 | 新表头 | 语义期望 | 实际映射 | conf | 判定 |")
        lines.append("|---|---|---|---|---|---|")
        for d in v2["details"]:
            lines.append(
                f"| {d['col']} | `{d['new_header']}` | `{d['expect_if_semantic']}` "
                f"| `{d['got']}` | {d['conf']:.2f} | {d['verdict']} |"
            )
        lines.append("")
        v3b = s["variants"]["V3b_ghostnum"]
        lines.append(f"**V3a**：L1 拦截={'是' if s['variants']['V3a_headerless']['l1_blocked'] else '否'}。")
        if v3b["l1_blocked"]:
            lines.append("**V3b**：数字表头行被 L1 拒绝（无 region 产出，未消耗 LLM 调用），防护发生在结构层。")
        elif v3b["leaks"]:
            lines.append("\n**V3b 泄漏**：")
            for lk in v3b["leaks"]:
                lines.append(f"- 列{lk['col']} 幽灵表头 {lk['header']!r} → `{lk['target']}` conf={lk['conf']:.2f}")
        else:
            lines.append(f"**V3b**：幽灵数字表头列 {v3b['ghost_cols']} 个进入 LLM，全部未映射，无泄漏。")
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", choices=list(EXPERIMENTS), default=None)
    args = parser.parse_args()

    targets = [args.only] if args.only else list(EXPERIMENTS)
    schema = load_schema(SCHEMA_PATH)
    config = LLMConfig.from_env(ROOT / ".env")

    TMP.mkdir(parents=True, exist_ok=True)
    summaries: list[dict] = []
    all_results: dict[str, dict[str, list[dict]]] = {}
    total_tokens = 0

    with LLMClient(config) as client:
        for exp in targets:
            xlsx_name, cfg_name = EXPERIMENTS[exp]
            src = DATA_DIR / xlsx_name
            gold = load_gold(cfg_name)
            variants = build_variants(exp, src)
            results: dict[str, list[dict]] = {}
            for vname, vpath in variants.items():
                print(f"[{exp}] {vname} <- {vpath.name} ...")
                recs = analyze(vpath, client, schema)
                total_tokens += sum(r["usage"].get("total_tokens", 0) for r in recs)
                results[vname] = recs
            all_results[exp] = results
            s = evaluate(exp, variants, gold, results)
            summaries.append(s)
            v1 = s["variants"]["V1_nonsense"]
            v2 = s["variants"]["V2_swapped"]
            v3b = s["variants"]["V3b_ghostnum"]
            obey = v2["semantic_obey_rate"]
            print(
                f"  V0={s['variants']['V0_baseline']['accuracy']:.0%} "
                f"V1_halluc={v1['hallucination_rate']:.0%} (hi={len(v1['high_conf_hallucinations'])}) "
                f"V2_obey={('—' if obey is None else f'{obey:.0%}')} "
                f"V3b_guard={'OK' if v3b['guard_ok'] else 'LEAK'}"
            )

    (TMP / "hallucination_result.json").write_text(
        json.dumps({"summaries": summaries, "results": all_results}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    report = render_report(summaries, all_results, total_tokens)
    (DOCS / "benchmark-hallucination-v0.md").write_text(report, encoding="utf-8")
    print(f"WROTE {DOCS / 'benchmark-hallucination-v0.md'}  total_tokens={total_tokens}")


if __name__ == "__main__":
    main()
