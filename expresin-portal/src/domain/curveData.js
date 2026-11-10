/**
 * Pure curve-building helpers for the workbench curve module.
 * Kept framework-free so the numeric/grouping rules can be tested with plain Node.
 */

export function finiteNumber(value) {
  if (value === null || value === undefined || value === '' || typeof value === 'boolean') return null
  const n = Number(value)
  return Number.isFinite(n) ? n : null
}

export function numericColumnKeys(columns, rows, minPoints = 2) {
  const keys = []
  for (const key of columns || []) {
    let count = 0
    for (const row of rows || []) {
      if (finiteNumber(row?.[key]) !== null) count += 1
      if (count >= minPoints) break
    }
    if (count >= minPoints) keys.push(key)
  }
  return keys
}

export function inferAxes(keys) {
  const available = keys || []
  const preferredX = ['bed_volume', 'volume_ml', 'row_index', 'signal_area', 'time_min', 'time_h']
  const preferredY = [
    'conc_ppm_computed',
    'conc_mg_l_computed',
    'conc_ppm_reported',
    'removal_rate',
    'ph',
    'current_density',
    'charge_c',
    'energy_kwh',
  ]
  const pick = (preferred, excluded = '') => {
    const match = preferred.find((key) => key !== excluded && available.includes(key))
    return match || available.find((key) => key !== excluded) || available[0] || ''
  }
  const xKey = pick(preferredX)
  const yKey = pick(preferredY, xKey)
  return { xKey, yKey }
}

export function inferGroupKey(rows) {
  for (const key of ['analyte', 'block', 'region']) {
    const values = new Set(
      (rows || [])
        .map((row) => String(row?.[key] ?? '').trim())
        .filter(Boolean),
    )
    if (values.size > 1) return key
  }
  return 'none'
}

/**
 * Build one or more series from canonical rows. Rows without a finite x or y are
 * skipped; points are sorted by x so SVG paths never zig-zag backwards.
 */
export function buildCurveSeries(rows, { xKey, yKey, groupKey = 'none', noneLabel = 'All data' } = {}) {
  if (!xKey || !yKey) return []
  const grouped = new Map()

  for (const row of rows || []) {
    const x = finiteNumber(row?.[xKey])
    const y = finiteNumber(row?.[yKey])
    if (x === null || y === null) continue

    const label =
      groupKey && groupKey !== 'none'
        ? String(row?.[groupKey] ?? '').trim() || noneLabel
        : noneLabel
    if (!grouped.has(label)) grouped.set(label, [])
    grouped.get(label).push({ x, y })
  }

  return [...grouped.entries()]
    .map(([label, points]) => ({
      label,
      points: points.sort((a, b) => a.x - b.x),
    }))
    .filter((series) => series.points.length)
    .sort((a, b) => a.label.localeCompare(b.label))
}

const C0_KEYS = new Set([
  'initial_concentration',
  'initial_concentration_mg_l',
  'c0',
  'inlet_concentration',
  '初始浓度',
])

function normalizeMetaKey(key) {
  return String(key || '')
    .trim()
    .toLowerCase()
    .replace(/\s+/g, '_')
}

/** Convert a concentration value to mg/L using the declared metadata unit. */
export function concentrationToMgL(value, unit) {
  const number = finiteNumber(value)
  if (number === null) return null
  const normalized = String(unit || '')
    .trim()
    .toLowerCase()
    .replace(/μ/g, 'µ')
    .replace(/\s+/g, '')
  if (/^(µg|ug)\/l$/.test(normalized)) return number / 1000
  if (/^g\/l$/.test(normalized)) return number * 1000
  return number
}

/**
 * Find the experiment-level influent concentration C0 in either nested
 * `meta` objects (value/label/unit wrappers) or flat metadata keys.
 * Canonical adsorption calculations are a fallback for older records.
 */
export function extractInitialConcentration(meta, calculations = []) {
  const visit = (node, keyHint) => {
    if (node === null || node === undefined) return null
    const hint = normalizeMetaKey(keyHint)
    if (node && typeof node === 'object' && !Array.isArray(node)) {
      if ('value' in node) {
        if (!C0_KEYS.has(hint)) return null
        const value = concentrationToMgL(node.value, node.unit)
        return value !== null && value > 0 ? { value, unit: 'mg/L' } : null
      }
      for (const [key, child] of Object.entries(node)) {
        const found = visit(child, key)
        if (found) return found
      }
      return null
    }
    if (!C0_KEYS.has(hint)) return null
    const value = concentrationToMgL(node, '')
    return value !== null && value > 0 ? { value, unit: 'mg/L' } : null
  }

  const fromMeta = visit(meta, '')
  if (fromMeta) return { ...fromMeta, source: 'metadata' }

  for (const item of calculations || []) {
    if (item?.type !== 'adsorption_capacity') continue
    const value = finiteNumber(item?.inputs?.C0_mg_l)
    if (value !== null && value > 0) return { value, source: 'canonical', unit: 'mg/L' }
  }
  return { value: null, source: 'none', unit: 'mg/L' }
}

export function sampleMeasurementRows(rows) {
  return (rows || []).filter((row) => row?.kind === 'sample_measurement')
}

/** Concentration hierarchy: engine-computed first, then reported measurement. */
export function effluentConcentration(row) {
  return (
    finiteNumber(row?.conc_ppm_computed) ??
    finiteNumber(row?.conc_mg_l_computed) ??
    finiteNumber(row?.conc_ppm_reported)
  )
}

/**
 * Build breakthrough series from sample rows only. Calibration standards are
 * intentionally excluded: they belong to the calibration curve, not the column
 * effluent curve.
 */
export function buildBreakthroughSeries(
  rows,
  { xKey, c0, groupKey = 'analyte', noneLabel = 'All data', c0ByLabel = {} } = {},
) {
  if (!xKey) return []
  const defaultC0 = finiteNumber(c0)
  const grouped = new Map()

  for (const row of sampleMeasurementRows(rows)) {
    const x = finiteNumber(row?.[xKey])
    const concentration = effluentConcentration(row)
    if (x === null || concentration === null) continue

    const label =
      groupKey && groupKey !== 'none'
        ? String(row?.[groupKey] ?? '').trim() || noneLabel
        : noneLabel
    const groupC0 = finiteNumber(c0ByLabel?.[label]) ?? defaultC0
    const ratio = groupC0 !== null && groupC0 > 0 ? concentration / groupC0 : null

    if (!grouped.has(label)) grouped.set(label, { label, c0: groupC0, points: [] })
    grouped.get(label).points.push({ x, c: concentration, ratio })
  }

  return [...grouped.values()]
    .map((series) => ({
      ...series,
      points: series.points.sort((a, b) => a.x - b.x),
    }))
    .filter((series) => series.points.length)
    .sort((a, b) => a.label.localeCompare(b.label))
}

/**
 * First crossing of a target C/C0 level. Linear interpolation between the two
 * neighbouring samples avoids pretending the threshold happened exactly at a
 * sampled BV.
 */
export function thresholdCrossing(points, target) {
  const usable = (points || []).filter((point) => finiteNumber(point?.ratio) !== null)
  if (!usable.length) return null
  const goal = finiteNumber(target)
  if (goal === null || goal < 0) return null
  const first = usable[0]
  if (first.ratio >= goal) return { x: first.x, ratio: first.ratio, interpolated: false }

  for (let index = 1; index < usable.length; index += 1) {
    const before = usable[index - 1]
    const after = usable[index]
    if (before.ratio >= goal || after.ratio < goal) continue
    const span = after.ratio - before.ratio
    if (span <= 0) continue
    const fraction = (goal - before.ratio) / span
    return {
      x: before.x + fraction * (after.x - before.x),
      ratio: goal,
      interpolated: true,
      before,
      after,
    }
  }
  return null
}

export function breakthroughSummary(points, { threshold = 0.05, saturation = 0.95 } = {}) {
  const ratios = (points || [])
    .map((point) => finiteNumber(point?.ratio))
    .filter((value) => value !== null)
  return {
    breakthrough: thresholdCrossing(points, threshold),
    saturation: thresholdCrossing(points, saturation),
    maxRatio: ratios.length ? Math.max(...ratios) : null,
    lastRatio: ratios.length ? ratios[ratios.length - 1] : null,
  }
}

export function niceScale(min, max, targetTicks = 5) {
  let lo = Number(min)
  let hi = Number(max)
  if (!Number.isFinite(lo) || !Number.isFinite(hi)) return { min: 0, max: 1, ticks: [0, 0.25, 0.5, 0.75, 1] }
  if (lo > hi) [lo, hi] = [hi, lo]
  if (lo === hi) {
    const pad = Math.abs(lo) || 1
    lo -= pad
    hi += pad
  }
  const rough = (hi - lo) / Math.max(2, targetTicks)
  const power = 10 ** Math.floor(Math.log10(rough))
  const normalized = rough / power
  const step = (normalized <= 1 ? 1 : normalized <= 2 ? 2 : normalized <= 5 ? 5 : 10) * power
  const start = Math.floor(lo / step) * step
  const end = Math.ceil(hi / step) * step
  const ticks = []
  for (let value = start; value <= end + step * 0.5; value += step) {
    ticks.push(Number(value.toPrecision(12)))
  }
  return { min: start, max: end, ticks }
}
