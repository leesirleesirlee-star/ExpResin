/**
 * PortalJarvis 会话状态。
 * 后端可用时走后端（AssistantSession / FormDraft），不可用时回退为本地草稿，
 * 保证「实验前录入」与「实验后识别」流程始终可用。
 */

import { computed, reactive } from 'vue'
import { api, probeBackend } from './api.js'

const TEMPLATE_FALLBACK = `${import.meta.env.BASE_URL}data/experiment_template_v1.json`

export const session = reactive({
  ready: false,
  online: false,
  templateId: 'expresin_template_v1',
  template: null,
  sessionId: null,
  drafts: {},
  messages: [],
  missing: [],
  experimentId: '',
  recognized: null,
  archive: [],
  lastArchiveError: '',
})

/** 标准 Schema 的合法目标字段（列块类型 → 字段清单），供识别页人工改判使用。 */
export const schemaColumns = reactive({})

/** 列块级离子判定的候选离子标签，来自后端标准 Schema。 */
export const analyteOptions = reactive([])

export const preSheets = computed(
  () => (session.template?.sheets ?? []).filter((s) => s.stage === 'pre'),
)
export const postSheets = computed(
  () => (session.template?.sheets ?? []).filter((s) => s.stage === 'post'),
)

export const templateFields = computed(() => {
  const map = {}
  for (const sheet of session.template?.sheets ?? []) {
    for (const f of sheet.fields) map[f.path] = f
  }
  return map
})

function suggestExperimentId() {
  const d = new Date()
  const stamp = `${d.getFullYear()}${String(d.getMonth() + 1).padStart(2, '0')}${String(
    d.getDate(),
  ).padStart(2, '0')}`
  return `RES-${stamp}-001`
}

export function setField(fieldPath, value, extra = {}) {
  const prev = session.drafts[fieldPath] || {}
  const next = {
    value,
    unit: extra.unit ?? prev.unit ?? templateFields.value[fieldPath]?.unit ?? null,
    confidence: extra.confidence ?? prev.confidence ?? null,
    status: extra.status ?? (String(value ?? '').trim() ? 'pending' : 'empty'),
    source_type: extra.source_type ?? 'manual',
    source_ref: extra.source_ref ?? prev.source_ref ?? null,
    raw_text: extra.raw_text ?? prev.raw_text ?? null,
  }
  if (extra.status === undefined && next.status === 'empty' && prev.status === 'deferred') {
    next.status = 'deferred'
  }
  session.drafts[fieldPath] = next

  if (session.online && session.sessionId) {
    api
      .getFormState(session.sessionId)
      .catch(() => {})
    // 后端模式下由 sendMessage / upload 负责同步，这里不重复写，避免请求风暴
  }
}

export function deferField(fieldPath) {
  const prev = session.drafts[fieldPath] || {}
  session.drafts[fieldPath] = { ...prev, status: 'deferred', source_type: prev.source_type || 'manual' }
}

/** 本地缺失项计算（与后端 missing-fields 口径一致）。 */
export const missingFields = computed(() => {
  const out = []
  for (const sheet of session.template?.sheets ?? []) {
    if (sheet.stage !== 'pre') continue
    for (const f of sheet.fields) {
      if (!f.required) continue
      const d = session.drafts[f.path] || {}
      if (String(d.value ?? '').trim()) continue
      if (d.status === 'deferred') continue
      out.push({ field_path: f.path, label: f.label, reason: '必填项尚未填写', required: true })
    }
  }
  return out
})

export const deferredFields = computed(() =>
  Object.entries(session.drafts)
    .filter(([, d]) => d.status === 'deferred')
    .map(([path, d]) => ({ field_path: path, label: templateFields.value[path]?.label || path })),
)

export function applyFormState(formState) {
  if (!formState) return
  for (const item of formState.fields ?? formState) {
    session.drafts[item.field_path] = {
      value: item.value,
      unit: item.unit,
      confidence: item.confidence,
      status: item.status,
      source_type: item.source_type,
      source_ref: item.source_ref,
      raw_text: item.raw_text,
    }
  }
}

async function loadTemplate() {
  try {
    return await api.getTemplate(session.templateId)
  } catch {
    const res = await fetch(TEMPLATE_FALLBACK, { cache: 'no-store' })
    return res.json()
  }
}

export async function initSession() {
  if (session.ready) return
  session.template = await loadTemplate()
  session.online = await probeBackend()

  if (session.online) {
    try {
      const created = await api.createSession({
        template_id: session.templateId,
        project_id: 'DHT',
      })
      session.sessionId = created.id
      session.experimentId = created.experiment_id_suggestion || suggestExperimentId()
      applyFormState(await api.getFormState(created.id))
    } catch {
      session.online = false
    }
  }

  if (!session.experimentId) session.experimentId = suggestExperimentId()
  if (!session.drafts['01_Metadata.experiment_id']) {
    setField('01_Metadata.experiment_id', session.experimentId, {
      source_type: 'template_default',
      status: 'pending',
    })
  }
  if (!session.drafts['01_Metadata.date_start']) {
    setField('01_Metadata.date_start', new Date().toISOString().slice(0, 10), {
      source_type: 'template_default',
      status: 'pending',
    })
  }

  if (!session.messages.length) {
    session.messages.push({
      role: 'assistant',
      content:
        '我是 Jarvis，负责记录这次实验。你可以直接用一句话告诉我实验安排，例如：' +
        '“今天用 120 mg 的 A600 树脂和 50 mL 溶液做 SO4 的批次吸附，初始浓度 100 mg/L”。' +
        '我会自动填入右侧表单，并提示还缺哪些必填信息。',
    })
  }

  session.ready = true
}

/**
 * 续接一个已存在的后端会话（例如从「实验档案」点进「数据识别」）。
 * 档案里只有元数据、还没上传数据表格时，必须回到**该实验原来那个会话**继续：
 * 否则上传的数据会落到新会话，归档时会因实验编号已被占用而失败。
 */
export async function resumeSession(sid) {
  if (!sid) return false
  if (!session.template) session.template = await loadTemplate()
  session.online = await probeBackend()
  if (!session.online) {
    session.ready = true
    return false
  }
  try {
    const info = await api.getSession(sid)
    session.sessionId = info.id
    session.experimentId = info.experiment_id || session.experimentId
    // 切会话时必须清掉上一段会话的识别结果，避免张冠李戴
    session.recognized = null
    session.missing = []
    session.drafts = {}
    applyFormState(await api.getFormState(sid))
    const draftId = session.drafts['01_Metadata.experiment_id']?.value
    if (draftId) session.experimentId = draftId
    if (!session.messages.length) {
      session.messages.push({
        role: 'assistant',
        content: `已回到实验 ${
          session.experimentId || info.id
        } 的记录。请上传这次实验的原始数据表格，我会识别列与单位后请你逐列确认。`,
      })
    }
    session.ready = true
    return true
  } catch {
    // 会话不存在或后端异常时退回常规流程，不阻断页面
    await initSession()
    return false
  }
}

export async function sendMessage(text) {
  session.messages.push({ role: 'user', content: text })
  if (session.online && session.sessionId) {
    try {
      const res = await api.sendMessage(session.sessionId, text)
      applyFormState(res.form_state)
      session.missing = res.missing || []
      session.messages.push({ role: 'assistant', content: res.reply })
      return
    } catch (e) {
      session.messages.push({
        role: 'assistant',
        content: `后端调用失败（${e.message}），请直接在表单中填写。`,
      })
      return
    }
  }
  session.messages.push({
    role: 'assistant',
    content: '（本地草稿模式）已记录你的描述。请在中栏表单直接填写或核对字段。',
  })
}

export async function uploadRawFile(file, sheet = null) {
  if (!session.online || !session.sessionId) {
    return { ok: false, reason: '后端未连接，无法解析文件。请启动 expresin-pipeline/server 后重试。' }
  }
  const res = await api.uploadFile(session.sessionId, file, true, sheet)
  session.recognized = res.recognized
  applyFormState(res.form_state)
  return { ok: true, result: res }
}

export async function confirmSession() {
  const payload = {
    experiment_id: session.drafts['01_Metadata.experiment_id']?.value || session.experimentId,
    fields: Object.entries(session.drafts).map(([field_path, d]) => ({
      field_path,
      value: d.value,
      unit: d.unit,
      confidence: d.confidence,
      status: d.status,
      source_type: d.source_type,
    })),
  }
  if (session.online && session.sessionId) {
    const exp = await api.confirmSession(session.sessionId, payload)
    session.experimentId = exp.id
    return exp
  }
  // 本地草稿模式：仅生成归档对象，不写入后端
  return {
    id: payload.experiment_id,
    title: session.drafts['01_Metadata.title']?.value || '（未命名实验）',
    local: true,
  }
}

export async function loadArchive() {
  if (!session.online) {
    session.archive = []
    return
  }
  try {
    const res = await api.listExperiments()
    session.archive = res.experiments || res || []
    session.lastArchiveError = ''
  } catch (e) {
    session.archive = []
    session.lastArchiveError = e.message
  }
}

/** 拉取标准字段清单，供识别页「改判为其他字段」使用。 */
export async function loadSchemaColumns() {
  if (Object.keys(schemaColumns).length) return
  try {
    const res = await api.getSchemaColumns()
    Object.assign(schemaColumns, res.columns || {})
    analyteOptions.length = 0
    analyteOptions.push(...(res.analytes || []))
  } catch {
    /* 后端不可用时下拉为空，问题清单仍可查看 */
  }
}

/**
 * 记录人工对某一列映射的判定。
 * 后端以「追加新版本」保存，返回修正后的完整快照，前端据此刷新展示。
 */
export async function reviewColumn(blockId, col, action, targetField = null) {
  if (!session.online || !session.sessionId) {
    return { ok: false, reason: '后端未连接，人工判定无法保存。请先启动后端服务。' }
  }
  const res = await api.reviewColumn(session.sessionId, {
    block_id: blockId,
    col,
    action,
    target_field: targetField,
  })
  session.recognized = res.recognized
  return { ok: true, review: res.review }
}