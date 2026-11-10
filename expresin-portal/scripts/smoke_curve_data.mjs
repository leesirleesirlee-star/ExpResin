import fs from 'node:fs'
import { en } from '../src/i18n/en.js'
import {
  breakthroughSummary,
  buildBreakthroughSeries,
  buildCurveSeries,
  concentrationToMgL,
  effluentConcentration,
  extractInitialConcentration,
  finiteNumber,
  inferAxes,
  inferGroupKey,
  niceScale,
  numericColumnKeys,
  sampleMeasurementRows,
  thresholdCrossing,
} from '../src/domain/curveData.js'

let checks = 0
function check(condition, message) {
  if (!condition) throw new Error(message)
  checks += 1
}

const rows = [
  { row_index: 1, bed_volume: 0, analyte: 'SO4', conc_ppm_computed: 10 },
  { row_index: 2, bed_volume: 2, analyte: 'SO4', conc_ppm_computed: 8 },
  { row_index: 3, bed_volume: 3, analyte: 'Cl', conc_ppm_computed: 6 },
  { row_index: 4, bed_volume: 1, analyte: 'Cl', conc_ppm_computed: 12 },
  { row_index: 5, bed_volume: '', analyte: 'Cl', conc_ppm_computed: 4 },
  { row_index: 6, bed_volume: 4, analyte: '', conc_ppm_computed: null },
]
const columns = ['row_index', 'bed_volume', 'analyte', 'conc_ppm_computed']

const numeric = numericColumnKeys(columns, rows)
check(numeric.includes('bed_volume'), 'numeric columns must include bed_volume')
check(!numeric.includes('analyte'), 'text columns must not be numeric')

const axes = inferAxes(numeric)
check(axes.xKey === 'bed_volume', `expected bed_volume x-axis, got ${axes.xKey}`)
check(axes.yKey === 'conc_ppm_computed', `expected computed concentration y-axis, got ${axes.yKey}`)

check(inferGroupKey(rows) === 'analyte', 'multiple analytes should default to analyte grouping')

const grouped = buildCurveSeries(rows, {
  xKey: 'bed_volume',
  yKey: 'conc_ppm_computed',
  groupKey: 'analyte',
  noneLabel: 'Ungrouped',
})
check(grouped.length === 2, 'expected two analyte series')
const so4 = grouped.find((item) => item.label === 'SO4')
const cl = grouped.find((item) => item.label === 'Cl')
check(so4 && so4.points.length === 2, 'SO4 series point count mismatch')
check(cl && cl.points.length === 2, 'Cl series point count mismatch')
check(cl.points[0].x === 1 && cl.points[1].x === 3, 'points must be sorted by x')

const ungrouped = buildCurveSeries(rows, {
  xKey: 'bed_volume',
  yKey: 'conc_ppm_computed',
  groupKey: 'none',
  noneLabel: 'All data',
})
check(ungrouped.length === 1 && ungrouped[0].label === 'All data', 'ungrouped series mismatch')
check(ungrouped[0].points.length === 4, 'blank x/y rows must be skipped')

check(finiteNumber('') === null, 'empty string is not a number')
check(finiteNumber('1.25') === 1.25, 'numeric strings are accepted')
check(finiteNumber(true) === null, 'booleans are not numbers')

const scale = niceScale(0.2, 13.7, 5)
check(scale.ticks.length >= 4, 'scale should produce enough ticks')
check(scale.min <= 0.2 && scale.max >= 13.7, 'scale must cover the data')
check(scale.ticks.every((value, i) => i === 0 || value > scale.ticks[i - 1]), 'ticks must increase')

const constant = niceScale(5, 5)
check(constant.min < 5 && constant.max > 5, 'constant range must be padded')

const reversed = niceScale(10, 2)
check(reversed.min <= 2 && reversed.max >= 10, 'reversed range must be normalized')

// Breakthrough-specific semantics
const nestedMeta = {
  '02_Method_Materials': {
    initial_concentration: { label: '初始浓度', value: '100', unit: 'mg/L' },
  },
}
const metaC0 = extractInitialConcentration(nestedMeta)
check(metaC0.value === 100 && metaC0.source === 'metadata', 'nested metadata C0 mismatch')
const calcC0 = extractInitialConcentration({}, [
  { type: 'adsorption_capacity', inputs: { C0_mg_l: 120 } },
])
check(calcC0.value === 120 && calcC0.source === 'canonical', 'calculation fallback C0 mismatch')
check(concentrationToMgL(500, 'µg/L') === 0.5, 'microgram unit conversion mismatch')
check(concentrationToMgL(0.5, 'g/L') === 500, 'gram unit conversion mismatch')

const breakthroughRows = [
  { kind: 'calibration', bed_volume: 0, analyte: 'SO4', conc_ppm_reported: 10 },
  { kind: 'sample_measurement', bed_volume: 0, analyte: 'SO4', conc_ppm_computed: 0.5 },
  { kind: 'sample_measurement', bed_volume: 5, analyte: 'SO4', conc_ppm_computed: 2.5 },
  { kind: 'sample_measurement', bed_volume: 10, analyte: 'SO4', conc_ppm_computed: 6 },
  { kind: 'sample_measurement', bed_volume: 5, analyte: 'Cl', conc_ppm_reported: 4 },
  { kind: 'sample_measurement', bed_volume: null, analyte: 'Cl', conc_ppm_reported: 8 },
]
check(sampleMeasurementRows(breakthroughRows).length === 5, 'sample row filtering mismatch')
check(
  effluentConcentration({ conc_ppm_computed: 2, conc_ppm_reported: 9 }) === 2,
  'computed concentration must win over reported concentration',
)
const breakthrough = buildBreakthroughSeries(breakthroughRows, {
  xKey: 'bed_volume',
  c0: 100,
  groupKey: 'analyte',
})
check(breakthrough.length === 2, 'expected two breakthrough series')
const btSo4 = breakthrough.find((item) => item.label === 'SO4')
const btCl = breakthrough.find((item) => item.label === 'Cl')
check(btSo4?.points.length === 3, 'calibration rows must be excluded')
check(btSo4?.points[1].ratio === 0.025, 'C/C0 ratio mismatch')
check(btCl?.points.length === 1 && btCl.points[0].ratio === 0.04, 'reported fallback ratio mismatch')

const crossing = thresholdCrossing(btSo4.points, 0.05)
check(crossing?.interpolated === true, 'threshold crossing must interpolate')
check(Math.abs(crossing.x - (5 + (0.05 - 0.025) / (0.06 - 0.025) * 5)) < 1e-9, 'interpolated BV mismatch')
const summary = breakthroughSummary(btSo4.points, { threshold: 0.05, saturation: 0.95 })
check(summary.breakthrough?.x > 5 && summary.breakthrough.x < 10, 'breakthrough summary mismatch')
check(summary.saturation === null, 'saturation must be reported as not reached')
check(summary.maxRatio === 0.06, 'max ratio mismatch')
const alreadyAbove = thresholdCrossing([{ x: 0, ratio: 0.06 }], 0.05)
check(alreadyAbove?.x === 0 && alreadyAbove.interpolated === false, 'first-point crossing mismatch')

const curveSource = fs.readFileSync(
  new URL('../src/components/CurveBuilder.vue', import.meta.url),
  'utf8',
)
const uiKeys = new Set(['床体积 (BV)', '流出体积 (mL)', '时间 (min)', '时间 (h)'])
for (const match of curveSource.matchAll(/(?:\$t|\bt)\(\s*'([^']+)'/g)) uiKeys.add(match[1])
const missingKeys = [...uiKeys].filter((key) => !(key in en)).sort()
check(missingKeys.length === 0, `missing English curve keys: ${missingKeys.join(', ')}`)

console.log(`CURVE_DATA_OK checks=${checks}`)
