/**
 * 字段状态唯一事实来源（Single Source of Truth）。
 *
 * 背景：此前列识别状态与录入草稿状态的「判定 + 文案 + 色调」散落在
 * demo.js / DynamicForm.vue / TemplateForm.vue，同一语义在不同面板
 * 可能出现不一致的标签与颜色。本模块把这些语义集中到一处。
 *
 * 两个域各自判定、共用文案/色调词表：
 *   - 列识别域：fieldState(col) —— 面向识别结果的列（regions/blocks/columns）
 *   - 录入草稿域：draftStatusOf(field, draft) —— 面向 SetupView 的字段草稿
 */

/* ------------------------------------------------------------------ *
 * 列识别域
 * ------------------------------------------------------------------ */

/** 离子标签列白名单：这类列天然没有目标字段，不应被标记为问题。 */
const ION_LABELS = new Set([
  'so4', 'cl', 'nh4+', 'nh4', 'li+', 'li', 'ca', 'na', 'hpo4', 'po4', 'no3', 'f',
])

/**
 * 列状态判定，供表单与 Inspector 共用。
 * 规则与旧 demo.js#fieldState 完全一致，仅迁移位置。
 */
export function fieldState(col) {
  // 人工处置优先于自动判定：用户已确认/改判/忽略的列不应再反复报警
  if (col.review) {
    if (col.review.status === 'ignore') return 'ignored'
    if (col.review.status === 'remap') return 'remapped'
    return 'confirmed'
  }

  const raw = (col.raw || '').trim()

  if (!col.target) {
    if (!raw) {
      // 「幽灵列」严格指「空表头 **且** 整列为空」。
      // 空表头但有数据的列是「未映射、待人工确认」，不能与空列混为一谈 ——
      // 否则会把真实数据当噪声丢弃。
      const hasData = typeof col.nonNull === 'number' && col.nonNull > 0
      return hasData ? 'pending' : 'missing'
    }
    if (ION_LABELS.has(raw.toLowerCase())) return 'label'
    return 'pending'
  }
  if (col.unitStd && col.unit && col.unit !== col.unitStd) return 'unit-error'
  if (col.conf < 0.8) return 'low-confidence'
  return 'confirmed'
}

/** 列状态 -> 展示文案与色调。 */
export const FIELD_STATE_META = {
  confirmed: { label: '已确认', tone: 'success' },
  pending: { label: '待确认', tone: 'warning' },
  'low-confidence': { label: '低置信度', tone: 'warning' },
  'unit-error': { label: '单位异常', tone: 'error' },
  missing: { label: '缺失', tone: 'warning' },
  label: { label: '标签列', tone: 'neutral' },
  ignored: { label: '已忽略', tone: 'neutral' },
  remapped: { label: '已改判', tone: 'accent' },
}

/** 便捷取 meta，未知状态安全兜底。 */
export function fieldStateMeta(state) {
  return FIELD_STATE_META[state] ?? { label: state ?? '', tone: 'neutral' }
}

/* ------------------------------------------------------------------ *
 * 录入草稿域
 * ------------------------------------------------------------------ */

/**
 * 录入字段状态判定。规则与旧 TemplateForm.vue#statusOf 完全一致。
 * @param {object} field 模板字段定义（含 required）
 * @param {object} draft 该字段的草稿 { value, status, confidence }
 */
export function draftStatusOf(field, draft = {}) {
  const value = String(draft.value ?? '').trim()
  if (draft.status === 'deferred') return 'deferred'
  if (!value) return field?.required ? 'missing' : 'empty'
  if (draft.status === 'unit_error') return 'unit-error'
  if (draft.status === 'low_confidence' || (typeof draft.confidence === 'number' && draft.confidence < 0.8)) {
    return 'low-confidence'
  }
  if (draft.status === 'confirmed') return 'confirmed'
  return 'pending'
}

/** 草稿状态 -> 展示文案与色调。 */
export const DRAFT_STATE_META = {
  confirmed: { label: '已确认', tone: 'success' },
  pending: { label: '待确认', tone: 'accent' },
  'low-confidence': { label: '低置信度', tone: 'warning' },
  'unit-error': { label: '单位异常', tone: 'error' },
  missing: { label: '必填缺失', tone: 'warning' },
  deferred: { label: '稍后补', tone: 'neutral' },
  empty: { label: '', tone: 'neutral' },
}

/** 便捷取 meta，未知状态安全兜底。 */
export function draftStateMeta(state) {
  return DRAFT_STATE_META[state] ?? { label: '', tone: 'neutral' }
}
