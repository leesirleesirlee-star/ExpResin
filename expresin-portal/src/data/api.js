/**
 * PortalJarvis 后端 API 封装（API-first：页面功能一律优先走后端契约）。
 * 后端不可用时由调用方回退到本地模式，保证界面始终可用。
 */

const BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000'

async function req(path, options = {}, timeoutMs = 0) {
  const isForm = options.body instanceof FormData
  const controller = new AbortController()
  const timer = timeoutMs > 0 ? setTimeout(() => controller.abort(), timeoutMs) : null
  let res
  try {
    res = await fetch(`${BASE}${path}`, {
      ...options,
      signal: controller.signal,
      headers: {
        ...(isForm ? {} : { 'Content-Type': 'application/json' }),
        ...(options.headers || {}),
      },
    })
  } catch (e) {
    // 超时与断连必须给出不同提示，否则用户无法判断该重试还是该启动服务
    if (e.name === 'AbortError') {
      const err = new Error(`请求超时：${Math.round(timeoutMs / 1000)} 秒内未收到响应`)
      err.status = 0
      err.timeout = true
      throw err
    }
    // 浏览器把「后端 500 且响应缺少 CORS 头」同样表现为网络层失败，
    // 因此这里不能断言服务没启动，必须保留另一种可能，否则会掩盖真实故障。
    const err = new Error('无法连接后端服务（也可能是后端返回了未处理的错误，请查看后端日志）')
    err.status = 0
    err.offline = true
    throw err
  } finally {
    if (timer) clearTimeout(timer)
  }
  if (!res.ok) {
    let detail = `HTTP ${res.status}`
    let payload = null
    try {
      const body = await res.json()
      payload = body
      // 后端错误细节可能是字符串，也可能是结构化对象（如 confirm 409 的 {message, missing}）
      if (typeof body.detail === 'string') detail = body.detail
      else if (body.detail && typeof body.detail === 'object') detail = body.detail.message || detail
      else if (typeof body.message === 'string') detail = body.message
    } catch {
      /* 保留默认信息 */
    }
    const err = new Error(detail)
    err.status = res.status
    err.payload = payload
    throw err
  }
  return res.json()
}

/**
 * 文件下载专用请求：不走 req() 的 JSON 解析，返回 {blob, filename}。
 * 错误解析与 req() 保持一致（后端 detail 可能是字符串或结构化对象）。
 */
async function download(path, fallbackName) {
  let res
  try {
    res = await fetch(`${BASE}${path}`)
  } catch {
    const err = new Error('无法连接后端服务（也可能是后端返回了未处理的错误，请查看后端日志）')
    err.status = 0
    err.offline = true
    throw err
  }
  if (!res.ok) {
    let detail = `HTTP ${res.status}`
    try {
      const body = await res.json()
      if (typeof body.detail === 'string') detail = body.detail
      else if (body.detail && typeof body.detail === 'object') detail = body.detail.message || detail
      else if (typeof body.message === 'string') detail = body.message
    } catch {
      /* 保留默认信息 */
    }
    const err = new Error(detail)
    err.status = res.status
    throw err
  }
  const blob = await res.blob()
  const disp = res.headers.get('content-disposition') || ''
  const match = /filename="([^"]+)"/.exec(disp)
  return { blob, filename: (match && match[1]) || fallbackName }
}

export const api = {
  base: BASE,

  health: () => req('/api/health'),

  getTemplate: (templateId = 'expresin_template_v1') =>
    req(`/portal/assistant/templates/${templateId}`),

  createSession: (payload = {}) =>
    req('/portal/assistant/sessions', { method: 'POST', body: JSON.stringify(payload) }),

  getSession: (sid) => req(`/portal/assistant/sessions/${sid}`),

  getFormState: (sid) => req(`/portal/assistant/sessions/${sid}/form-state`),

  getMissingFields: (sid) => req(`/portal/assistant/sessions/${sid}/missing-fields`),

  sendMessage: (sid, text) =>
    req(
      `/portal/assistant/sessions/${sid}/messages`,
      { method: 'POST', body: JSON.stringify({ text }) },
      120000,
    ),

  uploadFile: (sid, file, analyze = true, sheet = null) => {
    const fd = new FormData()
    fd.append('file', file)
    fd.append('analyze', String(analyze))
    if (sheet) fd.append('sheet', sheet)
    // 冷启动需并行调用多个 LLM（实测约 30–60s），给足 5 分钟预算；
    // 同一文件重复上传会命中后端缓存并秒回。
    return req(`/portal/assistant/sessions/${sid}/upload`, { method: 'POST', body: fd }, 300000)
  },

  confirmSession: (sid, payload = {}) =>
    req(
      `/portal/assistant/sessions/${sid}/confirm`,
      { method: 'POST', body: JSON.stringify(payload) },
      120000,
    ),

  /** 标准 Schema 的合法列字段（列块类型 → 字段清单），供识别页人工改判时选择。 */
  getSchemaColumns: () => req('/v1/schema/columns'),

  /** 记录人工对某一列映射的判定：confirm / remap / ignore。 */
  reviewColumn: (sid, payload) =>
    req(
      `/portal/assistant/sessions/${sid}/recognized-columns`,
      { method: 'PATCH', body: JSON.stringify(payload) },
      30000,
    ),

  listExperiments: () => req('/v1/experiments'),

  getExperiment: (id) => req(`/v1/experiments/${id}`),

  getProcessed: (id) => req(`/v1/experiments/${id}/data/processed`),

  /**
   * 规范长表（逐行数据值）。由归档时从原始文件重读 + 引擎复算生成，
   * 是识别骨架（只有列映射、value 恒为空）之外**真正存放数据值**的地方。
   */
  getCanonical: (id) => req(`/v1/experiments/${id}/data/canonical`),

  /** 按老师模板导出 Excel（A/B/C 三段，多目标离子分 sheet）；失败时抛带后端 detail 的 Error。 */
  exportTemplate: (id) => download(`/v1/experiments/${id}/export/template`, `${id}_template.xlsx`),

  /** 规范长表 CSV 下载（utf-8-sig，Excel 可直接打开）。 */
  exportCanonicalCsv: (id) => download(`/v1/experiments/${id}/data/canonical/csv`, `${id}_canonical.csv`),
}

/** 探测后端是否可用，用于决定「在线」还是「本地草稿」模式。 */
export async function probeBackend(timeoutMs = 1500) {
  try {
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), timeoutMs)
    const res = await fetch(`${BASE}/api/health`, { signal: controller.signal })
    clearTimeout(timer)
    return res.ok
  } catch {
    return false
  }
}