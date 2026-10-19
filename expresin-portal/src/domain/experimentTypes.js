/**
 * 实验类型展示名（badge / 列表 / 详情）单一来源。
 *
 * 与 expresin-pipeline/config/experiment_template_v1.json 的 option_labels 保持同步；
 * 电化学分支（两室/三室/双极膜）在 2026-10-13 作为独立 experiment_type 键引入，
 * 存储与导出链路沿用同一键，仅展示层映射为中文名。
 */

export const TYPE_LABELS = {
  batch: '批次实验',
  column: '柱实验',
  electrochemical: '电化学实验',
  electrochemical_two_chamber: '两室电化学',
  electrochemical_three_chamber: '三室电化学',
  electrochemical_bipolar: '双极膜电化学',
  regeneration: '再生',
  characterization: '表征',
}

/**
 * 类型键 → 中文展示名。
 * 未知键回退原始值（兼容后端新增类型与 demo 档案的现成中文标签），空值回退占位符。
 */
export function experimentTypeLabel(type, fallback = '—') {
  const raw = String(type ?? '').trim()
  if (!raw) return fallback
  return TYPE_LABELS[raw.toLowerCase()] ?? raw
}
