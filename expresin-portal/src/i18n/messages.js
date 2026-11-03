import { hasTranslation, locale, t } from '../composables/useI18n.js'

const HELP_PREFIX =
  '我可以帮你做三件事：① 从实验描述中提取并填写字段；② 检查还缺哪些必填信息；③ 协助上传实验文件和完成归档。'
const NEXT_COMPLETE = '必填信息已经齐全，确认无误后即可归档。'
const NEXT_MISSING_RE =
  /^当前还缺少：(.+?)。你可以直接告诉我，也可以在右侧表单填写。$/
const RECORDED_RE = /^已记录：(.+?)。([\s\S]+)$/
const EXTRACT_ERROR_RE = /^字段抽取失败：([\s\S]+)$/
const UPLOADED_RE =
  /^已解析《(.+?)》，识别到 (\d+) 个数据区。请在表单中逐列核对映射。$/
const ARCHIVED_RE = /^实验已归档，编号 (.+)。$/
const ION_REVIEW_RE = /^已记录人工离子判定 (.+?)：(.+?)(?:（(.+)）)?$/
const COLUMN_REVIEW_RE = /^已记录人工判定 (.+?)：(.+?)(?:（(.+)）)?$/

function interpolate(text, params) {
  if (!params) return String(text)
  return String(text).replace(/\{(\w+)\}/g, (match, key) =>
    params[key] === undefined ? match : String(params[key]),
  )
}

function englishList(items) {
  if (items.length === 0) return ''
  if (items.length === 1) return items[0]
  if (items.length === 2) return `${items[0]} and ${items[1]}`
  return `${items.slice(0, -1).join(', ')}, and ${items.at(-1)}`
}

/** 后端缺失项只带字段中文标签，这里用现有词典逐项转换。 */
function translateFieldList(text) {
  let namesText = text.trim()
  let total = null
  const more = namesText.match(/^(.*?)\s*等\s*(\d+)\s*项$/)
  if (more) {
    namesText = more[1]
    total = Number(more[2])
  }

  const names = namesText
    .split('、')
    .map((name) => name.trim())
    .filter(Boolean)
    .map((name) => t(name))

  let result = englishList(names)
  if (total && total > names.length) result += ` (${total} total)`
  return result
}

function translateNextStep(text) {
  if (text === NEXT_COMPLETE) return t(NEXT_COMPLETE)
  const missing = text.match(NEXT_MISSING_RE)
  if (!missing) return text
  return `Still missing: ${translateFieldList(missing[1])}. Tell me directly or fill in the form on the right.`
}

/**
 * Jarvis 的服务端回复仍以中文生成；在英文界面渲染时在此统一转换。
 * 返回内容不修改 message 原文，切换语言后会重新计算。
 */
export function localizeJarvisText(raw, params) {
  if (raw === null || raw === undefined) return ''
  if (locale.value !== 'en') return t(raw, params)
  if (hasTranslation(raw)) return t(raw, params)

  const text = interpolate(raw, params).trim()

  const recorded = text.match(RECORDED_RE)
  if (recorded) {
    return `Recorded: ${translateFieldList(recorded[1])}. ${translateNextStep(recorded[2])}`
  }

  if (text.startsWith(HELP_PREFIX)) {
    const next = translateNextStep(text.slice(HELP_PREFIX.length))
    return `${t(HELP_PREFIX)} ${next}`.trim()
  }

  if (text === NEXT_COMPLETE || NEXT_MISSING_RE.test(text)) {
    return translateNextStep(text)
  }

  const extractError = text.match(EXTRACT_ERROR_RE)
  if (extractError) {
    return t('字段抽取失败：{message}', { message: extractError[1] })
  }

  const uploaded = text.match(UPLOADED_RE)
  if (uploaded) {
    return t('已解析《{file}》，识别到 {n} 个数据区。请在表单中逐列核对映射。', {
      file: uploaded[1],
      n: uploaded[2],
    })
  }

  const archived = text.match(ARCHIVED_RE)
  if (archived) {
    return t('实验已归档，编号 {id}。', { id: archived[1] })
  }

  const ionReview = text.match(ION_REVIEW_RE)
  if (ionReview) {
    const target = ionReview[3] ? ` (${ionReview[3]})` : ''
    return `Ion assignment saved for ${ionReview[1]}: ${t(ionReview[2])}${target}.`
  }

  const columnReview = text.match(COLUMN_REVIEW_RE)
  if (columnReview) {
    const target = columnReview[3] ? ` (${columnReview[3]})` : ''
    return `Column review saved for ${columnReview[1]}: ${t(columnReview[2])}${target}.`
  }

  return text
}
