"""ExpResin PortalJarvis 后端 API（FastAPI）。

契约对应 PRD 第 12 章与 v2.0 第 3.2 节，可在 /api-docs 页面查阅。

启动：
    python -m uvicorn app:app --app-dir expresin-pipeline/server --port 8000
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[2]
PIPELINE = ROOT / "expresin-pipeline"
for extra in (PIPELINE / "src", PIPELINE / "server"):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

from l1_structure import parse_workbook  # noqa: E402
from llm import LLMClient, LLMConfig  # noqa: E402
from mapping import load_schema, map_block  # noqa: E402
from template_export import workbook_bytes  # noqa: E402
from template_fill import build_template_data  # noqa: E402
from services import (  # noqa: E402
    build_processed,
    check_unit,
    compose_reply,
    compute_missing,
    extract_fields,
    field_index,
    load_template,
    normalize_unit,
    render_csv,
    render_markdown,
)
from store import Store  # noqa: E402

DATA_DIR = PIPELINE / "data"
RAW_DIR = DATA_DIR / "raw"
DB_PATH = DATA_DIR / "expresin.db"
SCHEMA_PATH = PIPELINE / "config" / "standard_schema.json"
TEMPLATES = {"expresin_template_v1": load_template()}
KIND_LABELS = {
    "calibration": "标定曲线",
    "sample_measurement": "样品测量",
    "capacity": "交换容量",
    "ph_curve": "pH 曲线",
}

CACHE_DIR = DATA_DIR / "cache"
RAW_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# 识别「规则层」版本号：任何会改变识别结果的规则改动都必须递增。
# 缓存里存的是最终 payload（已含规则层结论），若不带版本校验，
# 升级后的规则会被旧缓存整体绕过 —— 确定性修复尤其容易被缓存悄悄吞掉。
RECOGNITION_RULE_VERSION = "rules_v2_missing_header"

# 列块之间彼此独立，可并行映射；并发过高易触发服务端限流，4 为本数据的实测甜点值。
MAX_MAPPING_WORKERS = max(1, int(os.environ.get("MAPPING_MAX_WORKERS", "4")))

store = Store(DB_PATH)


def cache_path(sha: str, sheet: str | None) -> Path:
    """识别结果缓存键：文件内容 sha + 工作表名（重复上传同一文件可秒回）。"""
    key = f"{sha}__{(sheet or 'default').strip()}"
    return CACHE_DIR / f"{re.sub(r'[^0-9a-zA-Z_.-]', '_', key)}.json"

app = FastAPI(title="ExpResin PortalJarvis API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def llm_client() -> LLMClient:
    return LLMClient(LLMConfig.from_env(ROOT / ".env"))


def template_of(template_id: str) -> dict:
    tpl = TEMPLATES.get(template_id)
    if not tpl:
        raise HTTPException(status_code=404, detail=f"未知的 template_id: {template_id}")
    return tpl


def form_state(session_id: str) -> dict:
    drafts = store.get_drafts(session_id)
    index = field_index(TEMPLATES["expresin_template_v1"])
    fields = []
    for d in drafts:
        field = index.get(d["field_path"], {})
        fields.append(
            {
                "field_path": d["field_path"],
                "label": field.get("label", d["field_path"]),
                "value": d["value"],
                "unit": d["unit"] or field.get("unit"),
                "confidence": d["confidence"],
                "status": d["status"],
                "source_type": d["source_type"],
                "source_ref": d["source_ref"],
                "raw_text": d["raw_text"],
                "updated_at": d["updated_at"],
            }
        )
    return {"session_id": session_id, "fields": fields}


# --------------------------------------------------------------------------- #
# 分析：L1 结构解析 + L3/L4 语义映射
# --------------------------------------------------------------------------- #


ION_LABELS = {"so4", "cl", "nh4+", "nh4", "li+", "li", "ca", "na", "hpo4", "po4", "no3", "f"}


def ion_label_of(columns: list[dict]) -> str | None:
    """从块内找出离子标签列的文本。

    标签列是整列常量文本（如 Cl / SO4），它比区块标题更能代表真实离子，
    因此可作为校验 analyte 判定的硬证据。
    """
    for col in columns:
        raw = (col.get("raw") or "").strip().lower()
        if raw and not col.get("target") and raw in ION_LABELS:
            return raw
    return None


# 离子判定是列块级结论，人工处置时用它作为「伪列名」，与真实数据列（A/B/C…）区分
ANALYTE_SCOPE_COL = "analyte"

# 人工改判离子时的候选：只接受标准离子标签，避免把自由文本写进 Processed
ANALYTE_OPTIONS = [
    {"key": "SO4", "label": "SO4（硫酸根）"},
    {"key": "Cl", "label": "Cl（氯离子）"},
    {"key": "NO3", "label": "NO3（硝酸根）"},
    {"key": "F", "label": "F（氟离子）"},
    {"key": "PO4", "label": "PO4（磷酸根）"},
    {"key": "HPO4", "label": "HPO4（磷酸氢根）"},
    {"key": "NH4+", "label": "NH4+（铵根）"},
    {"key": "Li+", "label": "Li+（锂离子）"},
    {"key": "Na", "label": "Na（钠离子）"},
    {"key": "Ca", "label": "Ca（钙离子）"},
]

_ANALYTE_ALIASES = {
    "so4": "SO4",
    "so42-": "SO4",
    "硫酸根": "SO4",
    "cl": "Cl",
    "cl-": "Cl",
    "氯离子": "Cl",
    "no3": "NO3",
    "no3-": "NO3",
    "f": "F",
    "f-": "F",
    "po4": "PO4",
    "po43-": "PO4",
    "hpo4": "HPO4",
    "nh4": "NH4+",
    "nh4+": "NH4+",
    "li": "Li+",
    "li+": "Li+",
    "na": "Na",
    "ca": "Ca",
}


def norm_analyte(value: str | None) -> str | None:
    """把人工填写的离子写法归一化为标准标签；无法识别返回 None。"""
    if not value:
        return None
    return _ANALYTE_ALIASES.get(value.strip().lower().replace(" ", ""))


def column_data_evidence(profile) -> dict:
    """把 L1 的客观填充证据透传给前端。

    前端需要它来区分「真空列」与「有数据但无表头」——两者此前都被标成"幽灵列"。
    """
    if profile is None:
        return {"nonNull": 0, "fillRatio": 0.0, "valueType": None}
    return {
        "nonNull": int(getattr(profile, "non_null", 0) or 0),
        "fillRatio": round(float(getattr(profile, "fill_ratio", 0.0) or 0.0), 3),
        "valueType": getattr(profile, "value_type", None),
    }


def build_block_payload(block, mapping) -> dict:
    """把一个列块的映射结果转成前端契约结构（含离子判定冲突信号）。

    规则层对「无表头列」做**确定性兜底**：表头缺失时模型没有语义证据，
    实测同一输入下会在 concentration_mg_l(0.70) 与 None(0.20) 之间跳变
    （0305-600#R44-44/B1 的 G 列，6 次快照 4:2，见 RO-005）。
    这里统一**不自动映射**，把模型的候选建议降级为 evidence 交人工判定，
    从而保证「同输入同输出」；人工仍可一键改判为正确字段。
    """
    columns = []
    for cm in mapping.columns:
        profile = next((c for c in block.columns if c.col_letter == cm.col_letter), None)
        raw_header = (profile.raw_header if profile else "") or ""
        suggested = cm.target_field
        confidence = round(float(cm.confidence), 2)

        if not raw_header.strip():
            # 无表头 → 不自动映射（确定性优先，绝不臆造）
            target_field = None
            hint = f"（模型建议 {suggested}，置信度 {confidence}）" if suggested else ""
            evidence = (
                f"该列无表头，缺少语义证据，未自动映射{hint}；如确为有效数据列，请人工改判"
            )
            confidence = min(confidence, 0.2)
        else:
            target_field = suggested
            evidence = cm.evidence

        columns.append(
            {
                "col": cm.col_letter,
                "raw": raw_header,
                "target": target_field,
                "field": target_field or ("离子标签列" if raw_header else None),
                "value": "",
                "conf": confidence,
                "unit": profile.unit if profile else None,
                "unitStd": None,
                "evidence": evidence,
                **column_data_evidence(profile),
            }
        )
    label = ion_label_of(columns)
    analyte = (mapping.analyte or "").strip()
    conflict = (
        {
            "expected": label,
            "actual": mapping.analyte,
            "evidence": f"块内离子标签列写作 {label}，与离子判定 {mapping.analyte} 矛盾，需人工确认",
        }
        if label and analyte and label != analyte.lower().replace(" ", "")
        else None
    )
    return {
        "id": block.block_id,
        "kind": mapping.block_kind,
        "analyte": mapping.analyte,
        "confidence": round(float(mapping.block_kind_confidence), 2),
        "analyteConflict": conflict,
        "columns": columns,
    }


def degraded_block_payload(block, error: str | None) -> dict:
    """某个列块映射失败时的降级结果：保留整列结构供人工处理，而不是丢掉整块。"""
    return {
        "id": block.block_id,
        "kind": "unknown",
        "analyte": None,
        "confidence": 0.0,
        "analyteConflict": None,
        "degraded": True,
        "error": error or "该列块识别失败",
        "columns": [
            {
                "col": profile.col_letter,
                "raw": profile.raw_header or "",
                "target": None,
                "field": None,
                "value": "",
                "conf": 0.0,
                "unit": profile.unit,
                "unitStd": None,
                "evidence": f"该列块识别失败：{error or '未知错误'}",
                **column_data_evidence(profile),
            }
            for profile in block.columns
        ],
    }


def analyze_workbook(path: Path, sheet_name: str | None = None) -> dict:
    schema = load_schema(SCHEMA_PATH)
    workbook = parse_workbook(path)
    target = None
    for sheet in workbook.sheets:
        if sheet_name is None or sheet.sheet_name.strip() == sheet_name.strip():
            target = sheet
            break
    if target is None:
        raise HTTPException(status_code=400, detail=f"未找到工作表: {sheet_name}")

    # 展平为任务列表：并行映射后再按 region 归组，避免"逐块串行"造成分钟级等待。
    jobs = [(region, block) for region in target.regions for block in region.col_blocks]

    with llm_client() as client:

        def run(job: tuple) -> tuple:
            region, block = job
            try:
                return map_block(client, block, region, schema, target.sheet_name), None
            except Exception as exc:  # noqa: BLE001
                # 单块失败只降级该块，绝不能让整个接口变成 500（用户拿不到任何结果）
                return None, str(exc)[:200]

        if len(jobs) > 1:
            with ThreadPoolExecutor(max_workers=min(MAX_MAPPING_WORKERS, len(jobs))) as pool:
                results = list(pool.map(run, jobs))
        else:
            results = [run(job) for job in jobs]

    grouped: dict[str, list[dict]] = {}
    failures: list[dict] = []
    for (region, block), (mapping, error) in zip(jobs, results):
        if mapping is None:
            failures.append({"block": block.block_id, "error": error})
            payload = degraded_block_payload(block, error)
        else:
            payload = build_block_payload(block, mapping)
        grouped.setdefault(region.region_id, []).append(payload)

    regions = []
    for region in target.regions:
        blocks = grouped.get(region.region_id) or []
        if not blocks:
            continue
        regions.append(
            {
                "id": region.region_id,
                "title": region.title or "",
                "kind": blocks[0]["kind"],
                "kindLabel": KIND_LABELS.get(blocks[0]["kind"], blocks[0]["kind"]),
                "blocks": blocks,
            }
        )

    return {
        "source": {
            "file": path.name,
            "sheet": target.sheet_name.strip(),
            "failedBlocks": failures,
            "ruleVersion": RECOGNITION_RULE_VERSION,
        },
        "regions": regions,
    }


# --------------------------------------------------------------------------- #
# 请求体
# --------------------------------------------------------------------------- #


class SessionCreate(BaseModel):
    template_id: str = "expresin_template_v1"
    project_id: str = "DHT"
    user_id: str = "default_user"


class MessageIn(BaseModel):
    text: str


class ConfirmIn(BaseModel):
    experiment_id: str | None = None
    fields: list[dict] | None = None
    confirmed_by: str = "user"


class ColumnReviewIn(BaseModel):
    """人工对「某一列映射判定」的处置。

    action:
      confirm 确认系统判定正确
      remap   改判为另一个合法标准字段（需 target_field）
      ignore  判定为非数据列，不参与 Processed
    """

    block_id: str
    col: str
    action: str
    target_field: str | None = None
    note: str | None = None


# --------------------------------------------------------------------------- #
# 运维
# --------------------------------------------------------------------------- #


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """把未处理异常转成带 CORS 头的 500。

    否则 Starlette 的 ServerErrorMiddleware 在 CORS 中间件的外层生成 500 响应，
    该响应不带 CORS 头，浏览器只会看到跨域失败，前端会把「后端内部错误」
    误报成「无法连接后端服务」，把真正的故障线索藏起来。
    """
    return JSONResponse(
        status_code=500,
        content={"detail": f"服务内部错误：{type(exc).__name__}: {exc}"},
    )


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "service": "expresin-portal", "version": "0.1.0"}


def schema_column_options() -> dict[str, list[dict]]:
    """把标准 Schema 展平为「列块类型 → 合法目标字段」。

    识别页的人工改判必须从这里取候选，避免把非法字段名写进 Processed。
    """
    schema = load_schema(SCHEMA_PATH)
    out: dict[str, list[dict]] = {}
    for kind, spec in (schema.get("block_kinds") or {}).items():
        out[kind] = [
            {
                "key": field.get("key"),
                "label": field.get("label") or field.get("key"),
                "unit": field.get("unit"),
            }
            for field in (spec.get("target_fields") or [])
            if field.get("key")
        ]
    return out


@app.get("/v1/schema/columns")
def get_schema_columns() -> dict:
    """识别页人工处置所需的候选值。

    columns 用于列级改判，analytes 用于列块级的离子判定改判。
    """
    return {"columns": schema_column_options(), "analytes": ANALYTE_OPTIONS}


# --------------------------------------------------------------------------- #
# Portal Assistant API
# --------------------------------------------------------------------------- #


@app.get("/portal/assistant/templates/{template_id}")
def get_template(template_id: str) -> dict:
    return template_of(template_id)


@app.post("/portal/assistant/sessions")
def create_session(payload: SessionCreate) -> dict:
    template_of(payload.template_id)
    sess = store.create_session(
        template_id=payload.template_id,
        project_id=payload.project_id,
        user_id=payload.user_id,
    )
    suggestion = store.next_experiment_id()
    store.add_message(
        sess["id"],
        "assistant",
        "我是 Jarvis，负责记录这次实验。可以直接用一句话说明实验安排，我会帮你填入表单。",
    )
    return {**sess, "experiment_id_suggestion": suggestion}


@app.get("/portal/assistant/sessions/{sid}")
def get_session(sid: str) -> dict:
    sess = store.get_session(sid)
    if not sess:
        raise HTTPException(status_code=404, detail="会话不存在")
    return sess


@app.get("/portal/assistant/sessions/{sid}/form-state")
def get_form_state(sid: str) -> dict:
    if not store.get_session(sid):
        raise HTTPException(status_code=404, detail="会话不存在")
    return form_state(sid)


@app.get("/portal/assistant/sessions/{sid}/missing-fields")
def get_missing_fields(sid: str) -> dict:
    if not store.get_session(sid):
        raise HTTPException(status_code=404, detail="会话不存在")
    drafts = store.get_draft_map(sid)
    template = TEMPLATES["expresin_template_v1"]
    return {
        "missing": compute_missing(template, drafts, "pre"),
        "deferred": [d["field_path"] for d in drafts.values() if d["status"] == "deferred"],
    }


@app.post("/portal/assistant/sessions/{sid}/messages")
def post_message(sid: str, payload: MessageIn) -> dict:
    if not store.get_session(sid):
        raise HTTPException(status_code=404, detail="会话不存在")
    template = TEMPLATES["expresin_template_v1"]
    index = field_index(template)

    store.add_message(sid, "user", payload.text)

    try:
        with llm_client() as client:
            extracted, _usage = extract_fields(client, payload.text, template, "pre")
    except Exception as exc:  # noqa: BLE001 - 外部依赖失败时降级
        store.add_message(sid, "assistant", f"字段抽取失败：{exc}")
        raise HTTPException(status_code=502, detail=f"LLM 调用失败: {exc}") from exc

    for item in extracted:
        field = index.get(item["field_path"], {})
        if item["status"] == "unit_error":
            item["status"] = "unit_error"
        elif check_unit(field, item.get("unit")) == "unit_error":
            item["status"] = "unit_error"
        store.upsert_draft(
            sid,
            item["field_path"],
            item["value"],
            unit=item.get("unit"),
            confidence=item.get("confidence"),
            status=item["status"],
            source_type="conversation",
            raw_text=item.get("raw_text"),
            model_version="deepseek-v4-pro",
        )

    drafts = store.get_draft_map(sid)
    missing = compute_missing(template, drafts, "pre")
    reply = compose_reply(extracted, missing, index)
    store.add_message(sid, "assistant", reply, meta={"extracted": extracted})
    store.touch_session(sid)

    return {
        "reply": reply,
        "extracted": extracted,
        "missing": missing,
        "form_state": form_state(sid),
    }


@app.post("/portal/assistant/sessions/{sid}/upload")
async def upload(
    sid: str,
    file: UploadFile = File(...),
    analyze: bool = Form(True),
    sheet: str | None = Form(None),
) -> dict:
    if not store.get_session(sid):
        raise HTTPException(status_code=404, detail="会话不存在")

    data = await file.read()
    sha = hashlib.sha256(data).hexdigest()
    dest = RAW_DIR / f"{sid}__{file.filename}"
    dest.write_bytes(data)

    # Raw 层：只追加，不覆盖（同名文件保留多版本，以 sha 区分）
    store.add_asset(
        sid,
        "raw_file",
        name=file.filename,
        sha256=sha,
        payload={"uri": str(dest), "size": len(data)},
    )
    store.upsert_draft(
        sid,
        "04_RawData.raw_file",
        file.filename,
        status="confirmed",
        source_type="upload",
        source_ref=str(dest),
    )

    recognized = {"source": {"file": file.filename, "sha256": sha}, "regions": []}
    if analyze and dest.suffix.lower() in (".xlsx", ".xls", ".xlsm"):
        cached_file = cache_path(sha, sheet)
        cached = None
        if cached_file.exists():
            try:
                cached = json.loads(cached_file.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                cached = None
        if cached is not None and (
            cached.get("source", {}).get("ruleVersion") != RECOGNITION_RULE_VERSION
        ):
            # 规则层已升级：旧缓存必须失效重算，否则新规则永远不生效
            cached = None
        if cached is not None:
            # 同一文件 + 同一工作表重复上传时直接命中，避免再次付出分钟级 LLM 成本
            recognized = cached
            recognized["source"]["cached"] = True
        else:
            try:
                recognized = analyze_workbook(dest, sheet)
            except Exception as exc:  # noqa: BLE001
                # 把"模型不可用"变成可读、可重试的提示，而不是让前端只看到 500
                raise HTTPException(
                    status_code=503,
                    detail={
                        "message": f"识别服务暂时不可用，请稍后重试：{str(exc)[:160]}",
                        "retryable": True,
                    },
                ) from exc
            recognized["source"]["cached"] = False
            try:
                cached_file.write_text(
                    json.dumps(recognized, ensure_ascii=False), encoding="utf-8"
                )
            except OSError:
                pass
        # 对外只暴露用户原始文件名，内部存储名不进契约
        recognized["source"]["file"] = file.filename
        recognized["source"]["stored_as"] = dest.name
        recognized["source"]["sha256"] = sha
        store.add_asset(sid, "recognized_blocks", name=file.filename, payload=recognized)
        store.add_message(
            sid,
            "assistant",
            f"已解析《{file.filename}》，识别到 {len(recognized['regions'])} 个数据区。请在表单中逐列核对映射。",
        )

    store.touch_session(sid)
    return {
        "raw": {"uri": str(dest), "sha256": sha, "size": len(data)},
        "recognized": recognized,
        "form_state": form_state(sid),
    }


ACTION_LABEL = {
    "confirm": "确认映射正确",
    "remap": "改判为其他标准字段",
    "ignore": "判定为非数据列",
}

ANALYTE_ACTION_LABEL = {
    "confirm": "确认离子判定正确",
    "remap": "改判为其他离子",
}


def _review_block_analyte(sid: str, snapshot: dict, asset: dict, block: dict, payload) -> dict:
    """处置列块级的「离子判定存疑」。

    analyte 是列块的结论（该块测的是哪种离子），不是某一列的取值，
    因此单独走这条路径：确认或改判都会清除冲突信号，并保留判定前后的取证信息。
    这里不接受 ignore —— 「该块不是数据」应通过处置它的各列来表达。
    """
    if payload.action == "ignore":
        raise HTTPException(
            status_code=422,
            detail="离子判定属于列块级结论，不能标记为非数据列；请改用确认或改判",
        )

    previous_analyte = block.get("analyte")
    conflict_before = block.get("analyteConflict")

    if payload.action == "remap":
        new_analyte = norm_analyte(payload.target_field)
        if not new_analyte:
            raise HTTPException(
                status_code=422,
                detail=f"非法离子标签：{payload.target_field or '（空）'}",
            )
    else:  # confirm
        new_analyte = previous_analyte
        if not new_analyte:
            raise HTTPException(
                status_code=422, detail="该列块没有可确认的离子判定，请改用改判"
            )

    block["analyte"] = new_analyte
    block["analyteConflict"] = None
    block["analyteReviewed"] = True
    review = {
        "status": payload.action,
        "by": "user",
        "at": datetime.now().isoformat(timespec="seconds"),
        "previous_analyte": previous_analyte,
        "analyte": new_analyte,
        "conflict_before": conflict_before,
        "note": payload.note or None,
    }
    block["analyteReview"] = review

    store.add_asset(sid, "recognized_blocks", name=asset.get("name"), payload=snapshot)
    store.log_confirmation(sid, f"analyte:{payload.block_id}", previous_analyte, new_analyte, "user")
    store.add_message(
        sid,
        "assistant",
        f"已记录人工离子判定 {payload.block_id}：{ANALYTE_ACTION_LABEL[payload.action]}"
        f"{('（' + str(new_analyte) + '）') if new_analyte else ''}",
    )
    store.touch_session(sid)

    return {"recognized": snapshot, "review": review, "scope": "block", "analyte": new_analyte}


@app.patch("/portal/assistant/sessions/{sid}/recognized-columns")
def review_recognized_column(sid: str, payload: ColumnReviewIn) -> dict:
    """记录人工对某一列映射的判定。

    遵循「Raw 不可覆盖、Processed 可追溯」：不原地篡改历史资产，
    而是把修正后的完整快照作为新版本追加，并写入审计消息与确认日志。
    """
    if not store.get_session(sid):
        raise HTTPException(status_code=404, detail="会话不存在")

    asset = store.latest_asset(sid, "recognized_blocks")
    if not asset:
        raise HTTPException(status_code=404, detail="会话还没有识别结果，请先上传原始数据")

    if payload.action not in ACTION_LABEL:
        raise HTTPException(status_code=422, detail=f"未知操作：{payload.action}")

    snapshot = json.loads(json.dumps(asset["payload"], ensure_ascii=False))

    target_block = None
    target_column = None
    for region in snapshot.get("regions", []):
        for block in region.get("blocks", []):
            if block.get("id") != payload.block_id:
                continue
            target_block = block
            for column in block.get("columns", []):
                if column.get("col") == payload.col:
                    target_column = column
    if target_block is None:
        raise HTTPException(status_code=404, detail=f"未找到列块 {payload.block_id}")

    # 离子判定是列块级结论，不走列级通道
    if payload.col == ANALYTE_SCOPE_COL:
        return _review_block_analyte(sid, snapshot, asset, target_block, payload)

    if target_column is None:
        # 列块整体识别失败时整块被降级，没有任何可处置的列。
        # 这不是「列不存在」的资源错误，而是「该块不支持列级处置」，
        # 返回 404 会误导调用方去猜列名，必须给出可操作的提示。
        if target_block.get("degraded"):
            raise HTTPException(
                status_code=422,
                detail=(
                    f"列块 {payload.block_id} 识别失败"
                    f"（{target_block.get('error') or '未知原因'}），"
                    "无法通过人工判定修复，请重新上传该文件或重试识别"
                ),
            )
        raise HTTPException(
            status_code=404, detail=f"未找到列 {payload.block_id}/{payload.col}"
        )

    previous_target = target_column.get("target")

    if payload.action == "remap":
        new_field = (payload.target_field or "").strip()
        if not new_field:
            raise HTTPException(status_code=422, detail="改判必须提供 target_field")
        allowed = {o["key"] for opts in schema_column_options().values() for o in opts}
        if new_field not in allowed:
            raise HTTPException(status_code=422, detail=f"非法标准字段：{new_field}")
        target_column["target"] = new_field
        target_column["field"] = new_field
        target_column["conf"] = 1.0
        target_column["evidence"] = f"人工改判：由 {previous_target or '未映射'} 改为 {new_field}"
    elif payload.action == "ignore":
        target_column["target"] = None
        target_column["conf"] = 0.0
        target_column["evidence"] = "人工判定为非数据列，不参与 Processed"
    else:  # confirm
        if not previous_target:
            raise HTTPException(
                status_code=422, detail="该列没有可确认的映射，请改用改判指定字段"
            )
        target_column["conf"] = 1.0
        target_column["evidence"] = f"人工确认映射：{previous_target}"

    review = {
        "status": payload.action,
        "by": "user",
        "at": datetime.now().isoformat(timespec="seconds"),
        "previous_target": previous_target,
        "target_field": target_column.get("target"),
        "note": payload.note or None,
    }
    target_column["review"] = review

    store.add_asset(sid, "recognized_blocks", name=asset.get("name"), payload=snapshot)
    store.log_confirmation(
        sid,
        f"column:{payload.block_id}/{payload.col}",
        previous_target,
        target_column.get("target"),
        "user",
    )
    store.add_message(
        sid,
        "assistant",
        f"已记录人工判定 {payload.block_id}/{payload.col}：{ACTION_LABEL[payload.action]}"
        f"{('（' + str(target_column.get('target')) + '）') if target_column.get('target') else ''}",
    )
    store.touch_session(sid)

    return {"recognized": snapshot, "review": review}


@app.post("/portal/assistant/sessions/{sid}/confirm")
def confirm(sid: str, payload: ConfirmIn) -> dict:
    sess = store.get_session(sid)
    if not sess:
        raise HTTPException(status_code=404, detail="会话不存在")

    template = TEMPLATES["expresin_template_v1"]
    index = field_index(template)

    for item in payload.fields or []:
        path = item.get("field_path")
        if path not in index:
            continue
        old = store.draft_value(sid, path)
        store.upsert_draft(
            sid,
            path,
            item.get("value"),
            unit=item.get("unit"),
            confidence=item.get("confidence"),
            status="confirmed",
            source_type=item.get("source_type") or "manual",
        )
        store.log_confirmation(sid, path, old, item.get("value"), payload.confirmed_by)

    drafts = store.get_draft_map(sid)
    missing = compute_missing(template, drafts, "pre")
    if missing:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "存在未填写的必填项，无法归档",
                "missing": missing,
            },
        )

    # 同一会话重复归档应当是幂等的：复用该会话既有编号并更新记录，
    # 而不是插入重复主键（曾因此抛 UNIQUE constraint failed 导致归档整体失败）。
    experiment_id = payload.experiment_id or sess.get("experiment_id")
    if experiment_id:
        existing = store.get_experiment(experiment_id)
        if existing and existing.get("session_id") != sid:
            raise HTTPException(
                status_code=409,
                detail=f"实验编号 {experiment_id} 已被其他会话占用，请更换编号",
            )
    else:
        experiment_id = store.next_experiment_id()

    raw_asset = store.latest_asset(sid, "raw_file")
    recognized_asset = store.latest_asset(sid, "recognized_blocks")
    # 计算引擎需要回到 Raw 原始文件重读完整数值列（L1 画像只留 5 个样本值）
    raw_path = ((raw_asset or {}).get("payload") or {}).get("uri")
    processed = build_processed(
        experiment_id,
        template,
        drafts,
        recognized_asset["payload"] if recognized_asset else None,
        raw_asset["name"] if raw_asset else None,
        raw_path=raw_path,
    )

    experiment = store.create_experiment(
        experiment_id=experiment_id,
        session_id=sid,
        project_id=sess["project_id"],
        title=str(drafts.get("01_Metadata.title", {}).get("value") or "（未命名实验）"),
        experiment_type=str(drafts.get("01_Metadata.experiment_type", {}).get("value") or ""),
        operator=str(drafts.get("01_Metadata.operator", {}).get("value") or ""),
        date_start=str(drafts.get("01_Metadata.date_start", {}).get("value") or ""),
        meta=processed.get("metadata", {}),
        processed=processed,
        raw_file=raw_asset["name"] if raw_asset else None,
        raw_sha256=raw_asset["sha256"] if raw_asset else None,
    )
    store.set_session_experiment(sid, experiment_id)
    store.add_message(sid, "assistant", f"实验已归档，编号 {experiment_id}。")

    return experiment


# --------------------------------------------------------------------------- #
# Public API v1
# --------------------------------------------------------------------------- #


@app.get("/v1/experiments")
def list_experiments(limit: int = 100) -> dict:
    return {"experiments": store.list_experiments(limit)}


@app.get("/v1/experiments/{experiment_id}")
def get_experiment(experiment_id: str) -> dict:
    exp = store.get_experiment(experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail="实验不存在")
    return exp


@app.get("/v1/experiments/{experiment_id}/data/processed")
def get_processed(experiment_id: str) -> dict:
    exp = store.get_experiment(experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail="实验不存在")
    return {"experiment_id": experiment_id, "processed": exp["processed"]}


@app.get("/v1/experiments/{experiment_id}/data/processed/markdown")
def get_processed_markdown(experiment_id: str) -> dict:
    exp = store.get_experiment(experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail="实验不存在")
    return {
        "experiment_id": experiment_id,
        "markdown": render_markdown(exp["processed"]),
    }


@app.get("/v1/experiments/{experiment_id}/data/canonical")
def get_canonical(experiment_id: str) -> dict:
    """规范长表（结构化 JSON），供后续 Evidence Package / 推送复用。"""
    exp = store.get_experiment(experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail="实验不存在")
    canonical = (exp.get("processed") or {}).get("canonical") or {}
    if not canonical.get("rows"):
        raise HTTPException(status_code=404, detail="该实验尚未生成规范表格")
    return {"experiment_id": experiment_id, "canonical": canonical}


@app.get("/v1/experiments/{experiment_id}/data/canonical/csv")
def get_canonical_csv(experiment_id: str) -> Response:
    """规范长表 CSV 下载（utf-8-sig，Excel 可直接打开）。"""
    exp = store.get_experiment(experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail="实验不存在")
    canonical = (exp.get("processed") or {}).get("canonical") or {}
    if not canonical.get("rows"):
        raise HTTPException(status_code=404, detail="该实验尚未生成规范表格")
    return Response(
        content=render_csv(canonical),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{experiment_id}_canonical.csv"'},
    )


@app.get("/v1/experiments/{experiment_id}/export/template")
def export_experiment_template(experiment_id: str) -> Response:
    """按指导老师模板导出 Excel（每个目标离子一个工作表，A/B/C 三段结构）。

    数据口径见 template_fill / template_export 模块文档：
    B 区从 Raw 重读，浓度引擎复算优先；C 区由 derive 确定性计算，缺输入带 reason。
    """
    exp = store.get_experiment(experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail="实验不存在")
    processed = exp.get("processed") or {}
    recognized = processed.get("recognized_data")
    if not recognized or not recognized.get("regions"):
        raise HTTPException(status_code=404, detail="该实验缺少识别数据，无法按模板导出")

    # 归档只存了原始文件名，完整路径保存在会话资产 payload.uri 中
    raw_asset = store.latest_asset(exp["session_id"], "raw_file") if exp.get("session_id") else None
    raw_path = ((raw_asset or {}).get("payload") or {}).get("uri")
    if not raw_path or not Path(raw_path).exists():
        raise HTTPException(status_code=404, detail="原始数据文件缺失，无法按模板导出")

    # 元数据按 sheet 分组存储（{sheet: {key: {value, ...}}}），导出层需要扁平 key→value
    metadata = {
        key: entry.get("value")
        for sheet in (exp.get("meta") or {}).values()
        if isinstance(sheet, dict)
        for key, entry in sheet.items()
        if isinstance(entry, dict)
    }
    metadata.setdefault("experiment_type", exp.get("experiment_type"))
    metadata.setdefault("experiment_id", experiment_id)

    try:
        data = build_template_data(
            experiment_type=exp.get("experiment_type") or "",
            recognized=recognized,
            raw_path=raw_path,
            experiment_id=experiment_id,
            metadata=metadata,
            canonical=processed.get("canonical"),
        )
    except ValueError as exc:
        # 未知实验类型（如 regeneration 暂无模板）属于语义错误而非资源缺失
        raise HTTPException(status_code=422, detail=str(exc))

    filename = f"{experiment_id}_{data.get('template_id') or 'template'}.xlsx"
    return Response(
        content=workbook_bytes(data),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )