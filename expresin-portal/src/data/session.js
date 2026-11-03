/**
 * PortalJarvis 会话状态。
 * 后端可用时走后端（AssistantSession / FormDraft），不可用时回退为本地草稿，
 * 保证「实验前录入」与「实验后识别」流程始终可用。
 */

import { computed, reactive } from 'vue'
import { t } from '../composables/useI18n.js'
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
  archiveLoading: false,
  lastArchiveError: '',
  draftSessions: [],
  draftsLoading: false,
  lastDraftsError: '',
  draftSaving: false,
  draftSaveError: '',
  lastDraftSavedAt: '',
})

const DRAFT_SAVE_DELAY = 450
const pendingDraftFields = new Map()
let draftSaveTimer = null
let draftSaveInFlight = null

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

function queueDraftSave(fieldPath) {
  if (!session.online || !session.sessionId) return
  pendingDraftFields.set(fieldPath, {
    field_path: fieldPath,
    ...session.drafts[fieldPath],
  })
  session.draftSaveError = ''
  if (draftSaveTimer) clearTimeout(draftSaveTimer)
  draftSaveTimer = setTimeout(() => {
    draftSaveTimer = null
    void flushDrafts()
  }, DRAFT_SAVE_DELAY)
}

/** 将一批变更写入后端；失败时保留待保存内容，归档仍会提交完整字段快照。 */
export async function flushDrafts() {
  if (draftSaveTimer) {
    clearTimeout(draftSaveTimer)
    draftSaveTimer = null
  }
  while (draftSaveInFlight) {
    try {
      await draftSaveInFlight
    } catch {
      // 首个调用会记录错误并重排队；归档等后续调用仍可继续提交完整快照。
    }
  }
  if (!session.online || !session.sessionId || !pendingDraftFields.size) return

  const sid = session.sessionId
  const fields = Array.from(pendingDraftFields.values())
  for (const field of fields) pendingDraftFields.delete(field.field_path)
  session.draftSaving = true

  let saved = false
  draftSaveInFlight = api.updateDrafts(sid, fields)
  try {
    await draftSaveInFlight
    saved = true
    if (session.sessionId === sid) {
      session.draftSaveError = ''
      session.lastDraftSavedAt = new Date().toISOString()
    }
  } catch (error) {
    if (session.sessionId === sid) {
      for (const field of fields) {
        if (!pendingDraftFields.has(field.field_path)) {
          pendingDraftFields.set(field.field_path, field)
        }
      }
      session.draftSaveError = error.message || t('草稿自动保存失败')
    }
  } finally {
    draftSaveInFlight = null
    session.draftSaving = false
  }

  // 请求期间产生的新变更紧接着保存；失败批次不自动重试，避免离线请求循环。
  if (saved && pendingDraftFields.size && session.sessionId === sid) {
    await flushDrafts()
  }
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
  queueDraftSave(fieldPath)
}

export function deferField(fieldPath) {
  const prev = session.drafts[fieldPath] || {}
  session.drafts[fieldPath] = { ...prev, status: 'deferred', source_type: prev.source_type || 'manual' }
  queueDraftSave(fieldPath)
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
      out.push({ field_path: f.path, label: f.label, reason: t('必填项尚未填写'), required: true })
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

function resetSessionState() {
  if (draftSaveTimer) {
    clearTimeout(draftSaveTimer)
    draftSaveTimer = null
  }
  pendingDraftFields.clear()
  session.ready = false
  session.sessionId = null
  session.drafts = {}
  session.messages = []
  session.missing = []
  session.experimentId = ''
  session.recognized = null
  session.draftSaving = false
  session.draftSaveError = ''
  session.lastDraftSavedAt = ''
}

async function initializeSession(initial = {}) {
  if (!session.template) session.template = await loadTemplate()
  session.online = await probeBackend()

  if (session.online) {
    try {
      const created = await api.createSession({
        template_id: session.templateId,
        project_id: 'DEMO',
      })
      session.sessionId = created.id
      session.experimentId = created.experiment_id_suggestion || suggestExperimentId()
      // 新建会话必为空，无需再请求一次空 form-state。
    } catch {
      session.online = false
      session.sessionId = null
    }
  }

  if (!session.experimentId) session.experimentId = suggestExperimentId()
  setField('01_Metadata.experiment_id', session.experimentId, {
    source_type: 'template_default',
    status: 'pending',
  })
  setField('01_Metadata.date_start', initial.dateStart || new Date().toISOString().slice(0, 10), {
    source_type: 'template_default',
    status: 'pending',
  })
  if (initial.title) setField('01_Metadata.title', initial.title)
  if (initial.experimentType) setField('01_Metadata.experiment_type', initial.experimentType)
  if (initial.operator) setField('01_Metadata.operator', initial.operator)

  session.messages.push({
    role: 'assistant',
    content:
      '我是 Jarvis，负责记录这次实验。你可以直接用一句话告诉我实验安排，例如：“今天用 120 mg 的 A600 树脂和 50 mL 溶液做 SO4 的批次吸附，初始浓度 100 mg/L”。我会自动填入右侧表单，并提示还缺哪些必填信息。',
  })
  session.ready = true
  return session
}

export async function initSession() {
  if (session.ready) return session
  return initializeSession()
}

/** 从工作台显式开始新实验；与导航进入 /setup 时续接当前会话的语义区分开。 */
export async function startNewSession(initial = {}) {
  await flushDrafts()
  resetSessionState()
  return initializeSession(initial)
}

/**
 * 续接一个已存在的后端会话（例如从「实验档案」点进「数据识别」）。
 * 档案里只有元数据、还没上传数据表格时，必须回到**该实验原来那个会话**继续：
 * 否则上传的数据会落到新会话，归档时会因实验编号已被占用而失败。
 */
export async function resumeSession(sid) {
  if (!sid) return false
  await flushDrafts()
  resetSessionState()
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
        content:
          '已回到实验 {id} 的记录。请上传这次实验的原始数据表格，我会识别列与单位后请你逐列确认。',
        params: { id: session.experimentId || info.id },
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
      const content = e.timeout
        ? '模型响应超时，这次描述暂未写入。你可以重试，或直接在右侧表单填写。'
        : e.status === 502
          ? '模型服务暂时不可用，这次描述暂未写入。你可以稍后重试，或直接填写表单。'
          : '消息发送失败（{message}），请稍后重试或直接在表单中填写。'
      session.messages.push({
        role: 'assistant',
        content,
        params: e.timeout || e.status === 502 ? undefined : { message: e.message },
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
    return { ok: false, reason: t('后端未连接，无法解析文件。请启动 expresin-pipeline/server 后重试。') }
  }
  const res = await api.uploadFile(session.sessionId, file, true, sheet)
  session.recognized = res.recognized
  applyFormState(res.form_state)
  return { ok: true, result: res }
}

export async function confirmSession() {
  await flushDrafts()
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
    title: session.drafts['01_Metadata.title']?.value || t('（未命名实验）'),
    local: true,
  }
}

export async function loadDraftSessions(limit = 6) {
  session.draftsLoading = true
  try {
    if (!session.online) session.online = await probeBackend()
    if (!session.online) {
      session.draftSessions = []
      session.lastDraftsError = ''
      return
    }
    const res = await api.listSessions(limit)
    session.draftSessions = res.sessions || []
    session.lastDraftsError = ''
  } catch (error) {
    session.draftSessions = []
    session.lastDraftsError = error.message || t('草稿列表读取失败')
  } finally {
    session.draftsLoading = false
  }
}

export async function loadArchive() {
  session.archiveLoading = true
  try {
    /* 首页可能先于任何实验会话挂载，此时 online 仍是初始 false；
       先探测一次，避免后端正常却被误判成空档案。 */
    if (!session.online) session.online = await probeBackend()
    if (!session.online) {
      session.archive = []
      return
    }
    const res = await api.listExperiments()
    session.archive = res.experiments || res || []
    session.lastArchiveError = ''
  } catch (e) {
    session.archive = []
    session.lastArchiveError = e.message
  } finally {
    session.archiveLoading = false
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
    return { ok: false, reason: t('后端未连接，人工判定无法保存。请先启动后端服务。') }
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