<script setup>
import { computed, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { api } from '../data/api.js'
import { useToast } from '../composables/useToast.js'
import { useI18n } from '../composables/useI18n.js'
import {
  breakthroughSummary,
  buildBreakthroughSeries,
  extractInitialConcentration,
  finiteNumber,
  inferGroupKey,
  niceScale,
  numericColumnKeys,
  sampleMeasurementRows,
} from '../domain/curveData.js'

const props = defineProps({
  experiments: { type: Array, default: () => [] },
  online: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
  error: { type: String, default: '' },
})

const { t, locale } = useI18n()
const { show } = useToast()

const selectedId = ref(props.experiments[0]?.id || '')
const canonical = ref(null)
const detail = ref(null)
const loadingCanonical = ref(false)
const canonicalError = ref('')
const xKey = ref('')
const yMode = ref('ratio')
const groupKey = ref('none')
const thresholdPct = ref(5)
const c0Input = ref('')
const c0Source = ref('none')
const exporting = ref('')
const svgEl = ref(null)
let loadToken = 0

const X_LABELS = {
  bed_volume: '床体积 (BV)',
  volume_ml: '流出体积 (mL)',
  time_min: '时间 (min)',
  time_h: '时间 (h)',
}

const GROUP_LABELS = {
  none: '不分组',
  analyte: '按分析物',
  block: '按数据区',
  region: '按区域',
}

const PALETTE = ['#2563eb', '#0f766e', '#b45309', '#be123c', '#6d28d9', '#475569', '#0891b2', '#4d7c0f']
const MAX_SERIES = 8
const SATURATION = 0.95
const W = 760
const H = 400
const M = { top: 30, right: 24, bottom: 62, left: 78 }

const rows = computed(() => (Array.isArray(canonical.value?.rows) ? canonical.value.rows : []))
const columns = computed(() => (Array.isArray(canonical.value?.columns) ? canonical.value.columns : []))
const sampleRows = computed(() => sampleMeasurementRows(rows.value))
const sampleKeys = computed(() => {
  const source = columns.value.length ? columns.value : Object.keys(sampleRows.value[0] || {})
  return numericColumnKeys(source, sampleRows.value)
})
const xOptions = computed(() =>
  ['bed_volume', 'volume_ml', 'time_min', 'time_h'].filter((key) =>
    sampleKeys.value.includes(key),
  ),
)
const selectedExperiment = computed(
  () => props.experiments.find((item) => item.id === selectedId.value) || null,
)
const c0 = computed(() => finiteNumber(c0Input.value))
const c0Valid = computed(() => c0.value !== null && c0.value > 0)
const threshold = computed(() => Number(thresholdPct.value) / 100)
const xUnit = computed(() => {
  if (xKey.value === 'bed_volume') return 'BV'
  if (xKey.value === 'volume_ml') return 'mL'
  if (xKey.value === 'time_min') return 'min'
  if (xKey.value === 'time_h') return 'h'
  return ''
})
const calibrationCount = computed(() => rows.value.filter((row) => row?.kind === 'calibration').length)

const c0ByLabel = computed(() => {
  const map = {}
  for (const item of canonical.value?.calculations || []) {
    if (item?.type !== 'adsorption_capacity') continue
    const label = String(item.analyte ?? '').trim()
    const value = finiteNumber(item?.inputs?.C0_mg_l)
    if (label && value !== null && value > 0) map[label] = value
  }
  return map
})

const groupOptions = computed(() =>
  Object.entries(GROUP_LABELS)
    .filter(
      ([value]) =>
        value === 'none' ||
        sampleRows.value.some((row) => String(row?.[value] ?? '').trim()),
    )
    .map(([value, label]) => ({ value, label: t(label) })),
)

const c0SourceText = computed(() => {
  if (c0Source.value === 'metadata') return t('来自实验元数据')
  if (c0Source.value === 'canonical') return t('来自规范表容量计算')
  if (c0Source.value === 'manual') return t('手动填写')
  return t('未找到')
})

function onC0Input() {
  c0Source.value = 'manual'
  if (c0Valid.value && yMode.value === 'concentration') yMode.value = 'ratio'
}

function experimentLabel(item) {
  const title = item?.title || item?.id || t('未命名实验')
  return item?.id && item?.title ? `${title} · ${item.id}` : title
}

function formatNumber(value) {
  const n = Number(value)
  if (!Number.isFinite(n)) return '—'
  const abs = Math.abs(n)
  if (abs !== 0 && (abs >= 100000 || abs < 0.001)) return n.toExponential(2)
  return n.toLocaleString(locale.value === 'en' ? 'en-US' : 'zh-CN', {
    maximumFractionDigits: abs < 1 ? 4 : 2,
  })
}

const series = computed(() =>
  buildBreakthroughSeries(sampleRows.value, {
    xKey: xKey.value,
    c0: c0.value,
    groupKey: groupKey.value,
    noneLabel: groupKey.value === 'none' ? t('全部样品') : t('未分组'),
    c0ByLabel: c0Source.value === 'manual' ? {} : c0ByLabel.value,
  }).slice(0, MAX_SERIES),
)

const plottedSeries = computed(() =>
  series.value
    .map((item) => ({
      ...item,
      points: item.points.filter((point) =>
        (yMode.value === 'ratio' ? point.ratio : point.c) !== null,
      ),
    }))
    .filter((item) => item.points.length),
)

const chart = computed(() => {
  if (!xKey.value || !plottedSeries.value.length) return null
  const allPoints = plottedSeries.value.flatMap((item) =>
    item.points.map((point) => ({
      ...point,
      y: yMode.value === 'ratio' ? point.ratio : point.c,
    })),
  )
  const xScale = niceScale(
    Math.min(0, ...allPoints.map((point) => point.x)),
    Math.max(...allPoints.map((point) => point.x)),
  )
  const yValues = allPoints.map((point) => point.y)
  const yScale = niceScale(
    Math.min(0, ...yValues),
    yMode.value === 'ratio' ? Math.max(1, ...yValues) : Math.max(...yValues),
  )
  const innerW = W - M.left - M.right
  const innerH = H - M.top - M.bottom
  const xSpan = xScale.max - xScale.min || 1
  const ySpan = yScale.max - yScale.min || 1
  const px = (value) => M.left + ((value - xScale.min) / xSpan) * innerW
  const py = (value) => M.top + innerH - ((value - yScale.min) / ySpan) * innerH
  const thresholdValue = c0Valid.value
    ? yMode.value === 'ratio'
      ? threshold.value
      : c0.value * threshold.value
    : null
  const saturationValue = c0Valid.value
    ? yMode.value === 'ratio'
      ? SATURATION
      : c0.value * SATURATION
    : null
  const pointCount = allPoints.length

  return {
    xScale,
    yScale,
    xLabel: t(X_LABELS[xKey.value] || xKey.value),
    yLabel: yMode.value === 'ratio' ? t('C/C₀（出口/入口）') : t('出口浓度 C (mg/L)'),
    xUnit: xUnit.value,
    pointCount,
    showPointMarks: pointCount <= 120,
    thresholdLines: [
      ...(thresholdValue === null
        ? []
        : [{ key: 'breakthrough', value: thresholdValue, y: py(thresholdValue), label: `${thresholdPct.value}%` }]),
      ...(saturationValue === null
        ? []
        : [{ key: 'saturation', value: saturationValue, y: py(saturationValue), label: '95%' }]),
    ],
    series: plottedSeries.value.map((item, index) => {
      const points = item.points.map((point) => {
        const y = yMode.value === 'ratio' ? point.ratio : point.c
        return { ...point, y, cx: px(point.x), cy: py(y) }
      })
      const summary = breakthroughSummary(item.points, {
        threshold: threshold.value,
        saturation: SATURATION,
      })
      const color = PALETTE[index % PALETTE.length]
      const markers = []
      if (thresholdValue !== null && summary.breakthrough) {
        markers.push({
          key: 'breakthrough',
          x: summary.breakthrough.x,
          y: thresholdValue,
          cx: px(summary.breakthrough.x),
          cy: py(thresholdValue),
          label: `${thresholdPct.value}%`,
        })
      }
      if (saturationValue !== null && summary.saturation) {
        markers.push({
          key: 'saturation',
          x: summary.saturation.x,
          y: saturationValue,
          cx: px(summary.saturation.x),
          cy: py(saturationValue),
          label: '95%',
        })
      }
      return {
        label: item.label,
        color,
        c0: item.c0,
        points,
        markers,
        summary,
        path: points
          .map((point, i) => `${i ? 'L' : 'M'}${point.cx.toFixed(2)},${point.cy.toFixed(2)}`)
          .join(' '),
      }
    }),
    xTicks: xScale.ticks.map((value) => ({ value, x: px(value) })),
    yTicks: yScale.ticks.map((value) => ({ value, y: py(value) })),
    plot: { x: M.left, y: M.top, w: innerW, h: innerH },
    zeroY: yScale.min < 0 && yScale.max > 0 ? py(0) : null,
  }
})

const ariaLabel = computed(() => {
  if (!chart.value) return t('图表数据')
  return `${t('图表数据')}：${chart.value.xLabel} / ${chart.value.yLabel}，${chart.value.pointCount} ${t('数据点')}`
})

function applyDefaults() {
  const sample = sampleMeasurementRows(rows.value)
  const source = columns.value.length ? columns.value : Object.keys(sample[0] || {})
  const keys = numericColumnKeys(source, sample)
  xKey.value =
    ['bed_volume', 'volume_ml', 'time_min', 'time_h'].find((key) => keys.includes(key)) || ''
  const c0Info = extractInitialConcentration(detail.value?.meta, canonical.value?.calculations)
  c0Input.value = c0Info.value !== null ? String(c0Info.value) : ''
  c0Source.value = c0Info.source
  yMode.value = c0Info.value !== null ? 'ratio' : 'concentration'
  groupKey.value = sample.some((row) => String(row?.analyte ?? '').trim())
    ? 'analyte'
    : inferGroupKey(sample)
  thresholdPct.value = 5
}

async function loadCanonical() {
  if (!selectedId.value || !props.online) {
    canonical.value = null
    detail.value = null
    canonicalError.value = ''
    return
  }
  const token = ++loadToken
  loadingCanonical.value = true
  canonicalError.value = ''
  try {
    const [res, experiment] = await Promise.all([
      api.getCanonical(selectedId.value),
      api.getExperiment(selectedId.value).catch(() => null),
    ])
    if (token !== loadToken) return
    canonical.value = res?.canonical || null
    detail.value = experiment || null
    applyDefaults()
  } catch (error) {
    if (token !== loadToken) return
    canonical.value = null
    detail.value = null
    canonicalError.value =
      error.status === 404
        ? t('该实验还没有可绘制的规范长表。完成归档并生成规范数据后再试。')
        : error.message || t('规范数据读取失败')
  } finally {
    if (token === loadToken) loadingCanonical.value = false
  }
}

watch(
  () => props.experiments,
  (list) => {
    if (!list.length) {
      selectedId.value = ''
      return
    }
    if (!list.some((item) => item.id === selectedId.value)) {
      selectedId.value = list[0].id
    }
  },
  { immediate: true },
)

watch(
  [selectedId, () => props.online],
  ([id, online]) => {
    if (id && online) loadCanonical()
    else {
      canonical.value = null
      detail.value = null
      canonicalError.value = ''
    }
  },
  { immediate: true },
)

function baseFilename() {
  return `ExpResin_${selectedId.value}_breakthrough`.replace(/[^\w.-]+/g, '_')
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  window.setTimeout(() => URL.revokeObjectURL(url), 1000)
}

function svgMarkup(exportSize = false) {
  const node = svgEl.value?.cloneNode(true)
  if (!node) return ''
  node.setAttribute('xmlns', 'http://www.w3.org/2000/svg')
  if (exportSize) {
    node.setAttribute('width', '1520')
    node.setAttribute('height', '800')
  }
  return `<?xml version="1.0" encoding="UTF-8"?>\n${new XMLSerializer().serializeToString(node)}`
}

async function exportSvg() {
  if (!chart.value) return
  exporting.value = 'svg'
  try {
    const filename = `${baseFilename()}.svg`
    downloadBlob(new Blob([svgMarkup(true)], { type: 'image/svg+xml;charset=utf-8' }), filename)
    show(t('已导出 {filename}', { filename }), { tone: 'success' })
  } catch {
    show(t('曲线导出失败，请稍后重试'), { tone: 'error' })
  } finally {
    exporting.value = ''
  }
}

async function exportPng() {
  if (!chart.value) return
  exporting.value = 'png'
  const url = URL.createObjectURL(new Blob([svgMarkup(true)], { type: 'image/svg+xml;charset=utf-8' }))
  try {
    const image = new Image()
    await new Promise((resolve, reject) => {
      image.onload = resolve
      image.onerror = reject
      image.src = url
    })
    const canvas = document.createElement('canvas')
    canvas.width = 1520
    canvas.height = 800
    const context = canvas.getContext('2d')
    context.fillStyle = '#ffffff'
    context.fillRect(0, 0, canvas.width, canvas.height)
    context.drawImage(image, 0, 0, canvas.width, canvas.height)
    const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/png'))
    if (!blob) throw new Error('png encode failed')
    const filename = `${baseFilename()}.png`
    downloadBlob(blob, filename)
    show(t('已导出 {filename}', { filename }), { tone: 'success' })
  } catch {
    show(t('曲线导出失败，请稍后重试'), { tone: 'error' })
  } finally {
    URL.revokeObjectURL(url)
    exporting.value = ''
  }
}

function exportCsv() {
  if (!chart.value) return
  exporting.value = 'csv'
  try {
    const escape = (value) => `"${String(value).replace(/"/g, '""')}"`
    const lines = [
      [t('曲线'), `${t(X_LABELS[xKey.value] || xKey.value)} (${xUnit.value})`, t('出口浓度 C (mg/L)'), 'C/C0']
        .map(escape)
        .join(','),
    ]
    for (const item of series.value) {
      for (const point of item.points) {
        lines.push(
          [item.label, point.x, point.c, point.ratio ?? ''].map(escape).join(','),
        )
      }
    }
    const filename = `${baseFilename()}.csv`
    downloadBlob(
      new Blob(['\uFEFF' + lines.join('\r\n')], { type: 'text/csv;charset=utf-8' }),
      filename,
    )
    show(t('已导出 {filename}', { filename }), { tone: 'success' })
  } catch {
    show(t('曲线导出失败，请稍后重试'), { tone: 'error' })
  } finally {
    exporting.value = ''
  }
}
</script>

<template>
  <div class="curve-builder">
    <div v-if="loading" class="curve-state" role="status">
      <span class="spinner" aria-hidden="true"></span>
      <h3>{{ $t('正在读取实验档案') }}</h3>
      <p>{{ $t('确认当前账号可用于曲线分析的数据范围。') }}</p>
    </div>

    <div v-else-if="!online" class="curve-state">
      <h3>{{ $t('后端服务尚未连接') }}</h3>
      <p>{{ $t('曲线生成需要读取本人归档的规范长表，连接后端后再试。') }}</p>
    </div>

    <div v-else-if="error" class="curve-state curve-state--error" role="alert">
      <h3>{{ $t('实验档案读取失败') }}</h3>
      <p>{{ error }}</p>
    </div>

    <div v-else-if="!experiments.length" class="curve-state">
      <span class="curve-state-icon" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round">
          <path d="M4 4v16h16M7 16l4-5 3 3 5-8" />
        </svg>
      </span>
      <h3>{{ $t('先归档一次实验，再生成曲线') }}</h3>
      <p>{{ $t('曲线只读取本人已归档的规范长表，不会用示例数据伪造结果。') }}</p>
      <RouterLink to="/setup" class="btn btn-primary">{{ $t('开始第一次实验') }}</RouterLink>
    </div>

    <div v-else class="curve-workspace">
      <div class="curve-toolbar">
        <label class="curve-field curve-field--experiment">
          <span>{{ $t('选择实验') }}</span>
          <select v-model="selectedId" class="input">
            <option v-for="item in experiments" :key="item.id" :value="item.id">
              {{ experimentLabel(item) }}
            </option>
          </select>
        </label>

        <label class="curve-field">
          <span>{{ $t('横轴') }}</span>
          <select v-model="xKey" class="input" :disabled="loadingCanonical || !xOptions.length">
            <option v-for="key in xOptions" :key="key" :value="key">
              {{ $t(X_LABELS[key]) }}
            </option>
          </select>
        </label>

        <label class="curve-field">
          <span>{{ $t('纵轴') }}</span>
          <select v-model="yMode" class="input" :disabled="loadingCanonical">
            <option value="ratio" :disabled="!c0Valid">{{ $t('C/C₀（出口/入口）') }}</option>
            <option value="concentration">{{ $t('出口浓度 C (mg/L)') }}</option>
          </select>
        </label>

        <label class="curve-field">
          <span>{{ $t('入口浓度 C₀ (mg/L)') }}</span>
          <input
            v-model="c0Input"
            class="input"
            type="number"
            min="0"
            step="any"
            inputmode="decimal"
            :placeholder="$t('未找到，可手动填写')"
            :title="c0SourceText"
            @input="onC0Input"
          />
        </label>

        <label class="curve-field">
          <span>{{ $t('穿透点阈值') }}</span>
          <select v-model.number="thresholdPct" class="input" :disabled="loadingCanonical">
            <option :value="5">C/C₀ = 5%</option>
            <option :value="10">C/C₀ = 10%</option>
          </select>
        </label>

        <button
          class="curve-refresh"
          type="button"
          :disabled="loadingCanonical"
          :aria-label="$t('刷新数据')"
          :title="$t('刷新数据')"
          @click="loadCanonical"
        >
          ↻
        </button>
      </div>

      <div v-if="loadingCanonical" class="curve-state curve-state--compact" role="status">
        <span class="spinner" aria-hidden="true"></span>
        <p>{{ $t('正在读取规范数据…') }}</p>
      </div>

      <div v-else-if="canonicalError" class="curve-state curve-state--compact curve-state--error" role="alert">
        <p>{{ canonicalError }}</p>
        <button class="btn btn-ghost" type="button" @click="loadCanonical">{{ $t('重新加载') }}</button>
      </div>

      <div v-else-if="!rows.length" class="curve-state curve-state--compact">
        <p>{{ $t('该实验还没有可绘制的规范长表。完成归档并生成规范数据后再试。') }}</p>
      </div>

      <div v-else-if="!sampleRows.length" class="curve-state curve-state--compact">
        <p>{{ $t('该实验只有标定行，没有样品测量行，无法绘制穿透曲线。') }}</p>
      </div>

      <div v-else-if="!xOptions.length" class="curve-state curve-state--compact">
        <p>{{ $t('样品行缺少床体积 (BV)、流出体积 (mL) 或时间列，无法绘制穿透曲线。') }}</p>
      </div>

      <div v-else class="curve-content">
        <div class="curve-meta">
          <div>
            <strong>{{ selectedExperiment?.title || selectedId }}</strong>
            <span>{{ $t('{n} 个样品点', { n: chart?.pointCount || 0 }) }}</span>
            <span>{{ $t('{n} 条曲线', { n: chart?.series.length || 0 }) }}</span>
            <span v-if="calibrationCount">
              {{ $t('已排除 {n} 个标定行', { n: calibrationCount }) }}
            </span>
          </div>
          <div class="curve-actions">
            <button class="btn btn-secondary btn-compact" type="button" :disabled="!!exporting || !chart" @click="exportSvg">
              {{ exporting === 'svg' ? $t('正在导出…') : $t('导出 SVG') }}
            </button>
            <button class="btn btn-secondary btn-compact" type="button" :disabled="!!exporting || !chart" @click="exportPng">
              {{ exporting === 'png' ? $t('正在导出…') : $t('导出 PNG') }}
            </button>
            <button class="btn btn-secondary btn-compact" type="button" :disabled="!!exporting || !chart" @click="exportCsv">
              {{ exporting === 'csv' ? $t('正在导出…') : $t('导出曲线 CSV') }}
            </button>
          </div>
        </div>

        <div class="curve-context">
          <span>
            {{ $t('入口浓度 C₀') }}:
            <strong>{{ c0Valid ? formatNumber(c0) : '—' }}</strong>
            <em>mg/L</em>
          </span>
          <span>{{ c0SourceText }}</span>
          <label class="curve-group-control">
            <span>{{ $t('曲线分组') }}</span>
            <select
              v-model="groupKey"
              :disabled="loadingCanonical || !sampleRows.length"
              :aria-label="$t('曲线分组')"
            >
              <option v-for="option in groupOptions" :key="option.value" :value="option.value">
                {{ option.label }}
              </option>
            </select>
          </label>
          <span v-if="!c0Valid" class="curve-context-warning">
            {{ $t('填写 C₀ 后才能计算 C/C₀ 和穿透点。') }}
          </span>
        </div>

        <div v-if="!chart" class="curve-state curve-state--compact">
          <p>
            {{
              !c0Valid && yMode === 'ratio'
                ? $t('缺少入口浓度 C₀，请填写 C₀ 或切换为出口浓度。')
                : $t('样品行没有可用的出口浓度或横轴数值。')
            }}
          </p>
        </div>

        <template v-else>
          <div class="breakthrough-summary" :aria-label="$t('穿透点摘要')">
            <article
              v-for="item in chart.series"
              :key="`summary-${item.label}`"
              class="breakthrough-card"
            >
              <header>
                <i :style="{ background: item.color }" aria-hidden="true"></i>
                <strong>{{ item.label }}</strong>
                <small v-if="item.c0">C₀ {{ formatNumber(item.c0) }} mg/L</small>
              </header>
              <dl>
                <div>
                  <dt>{{ $t('穿透点') }} · {{ thresholdPct }}%</dt>
                  <dd>
                    {{ !c0Valid
                      ? '—'
                      : item.summary.breakthrough
                        ? `${formatNumber(item.summary.breakthrough.x)} ${chart.xUnit}`
                        : $t('未达到') }}
                  </dd>
                </div>
                <div>
                  <dt>{{ $t('饱和点') }} · 95%</dt>
                  <dd>
                    {{ !c0Valid
                      ? '—'
                      : item.summary.saturation
                        ? `${formatNumber(item.summary.saturation.x)} ${chart.xUnit}`
                        : $t('未达到') }}
                  </dd>
                </div>
                <div>
                  <dt>{{ $t('最高 C/C₀') }}</dt>
                  <dd>{{ formatNumber(item.summary.maxRatio) }}</dd>
                </div>
              </dl>
            </article>
          </div>

          <div class="curve-chart-shell">
            <svg
              ref="svgEl"
              class="curve-chart"
              :viewBox="`0 0 ${W} ${H}`"
              role="img"
              :aria-label="ariaLabel"
            >
              <title>{{ ariaLabel }}</title>
              <rect :width="W" :height="H" fill="#ffffff" />
              <g stroke="#e2e8f0" stroke-width="1">
                <line v-for="tick in chart.yTicks" :key="`gy-${tick.value}`" :x1="chart.plot.x" :y1="tick.y" :x2="chart.plot.x + chart.plot.w" :y2="tick.y" />
                <line v-for="tick in chart.xTicks" :key="`gx-${tick.value}`" :x1="tick.x" :y1="chart.plot.y" :x2="tick.x" :y2="chart.plot.y + chart.plot.h" />
              </g>
              <g v-for="line in chart.thresholdLines" :key="`threshold-${line.key}`">
                <line
                  :x1="chart.plot.x"
                  :y1="line.y"
                  :x2="chart.plot.x + chart.plot.w"
                  :y2="line.y"
                  stroke="#94a3b8"
                  stroke-width="1"
                  stroke-dasharray="5 4"
                />
                <text
                  :x="chart.plot.x + chart.plot.w - 4"
                  :y="line.y - 5"
                  text-anchor="end"
                  fill="#64748b"
                  font-size="10"
                  font-family="system-ui, sans-serif"
                >
                  {{ line.label }}
                </text>
              </g>
              <line v-if="chart.zeroY !== null" :x1="chart.plot.x" :y1="chart.zeroY" :x2="chart.plot.x + chart.plot.w" :y2="chart.zeroY" stroke="#94a3b8" stroke-width="1.5" stroke-dasharray="4 4" />
              <g stroke="#334155" stroke-width="1.2">
                <line :x1="chart.plot.x" :y1="chart.plot.y + chart.plot.h" :x2="chart.plot.x + chart.plot.w" :y2="chart.plot.y + chart.plot.h" />
                <line :x1="chart.plot.x" :y1="chart.plot.y" :x2="chart.plot.x" :y2="chart.plot.y + chart.plot.h" />
              </g>
              <g fill="#64748b" font-size="11" font-family="system-ui, sans-serif">
                <text v-for="tick in chart.yTicks" :key="`ty-${tick.value}`" :x="chart.plot.x - 10" :y="tick.y + 4" text-anchor="end">
                  {{ formatNumber(tick.value) }}
                </text>
                <text v-for="tick in chart.xTicks" :key="`tx-${tick.value}`" :x="tick.x" :y="chart.plot.y + chart.plot.h + 20" text-anchor="middle">
                  {{ formatNumber(tick.value) }}
                </text>
                <text :x="chart.plot.x + chart.plot.w / 2" :y="H - 10" text-anchor="middle" fill="#334155" font-size="12">
                  {{ chart.xLabel }}
                </text>
                <text :x="18" :y="chart.plot.y + chart.plot.h / 2" text-anchor="middle" fill="#334155" font-size="12" :transform="`rotate(-90 18 ${chart.plot.y + chart.plot.h / 2})`">
                  {{ chart.yLabel }}
                </text>
              </g>
              <g v-for="item in chart.series" :key="item.label" fill="none" :stroke="item.color" stroke-width="2" stroke-linejoin="round" stroke-linecap="round">
                <path :d="item.path" />
                <template v-if="chart.showPointMarks">
                  <circle v-for="(point, i) in item.points" :key="`${item.label}-${i}`" :cx="point.cx" :cy="point.cy" r="2.4" :fill="item.color" stroke="#ffffff" stroke-width="1">
                    <title>{{ item.label }} · {{ formatNumber(point.x) }} {{ chart.xUnit }} / {{ formatNumber(point.y) }}</title>
                  </circle>
                </template>
                <circle
                  v-for="marker in item.markers"
                  :key="`${item.label}-${marker.key}`"
                  :cx="marker.cx"
                  :cy="marker.cy"
                  r="4"
                  fill="#ffffff"
                  :stroke="item.color"
                  stroke-width="2"
                >
                  <title>{{ item.label }} · {{ marker.label }} · {{ formatNumber(marker.x) }} {{ chart.xUnit }}</title>
                </circle>
              </g>
            </svg>
          </div>
          <div class="curve-legend" :aria-label="$t('图例')">
            <span v-for="item in chart.series" :key="item.label">
              <i :style="{ background: item.color }" aria-hidden="true"></i>
              {{ item.label }}
            </span>
            <span v-if="series.length === MAX_SERIES" class="curve-limit">
              {{ $t('最多显示 {n} 组曲线', { n: MAX_SERIES }) }}
            </span>
          </div>
          <p class="curve-note">
            {{ $t('穿透点和饱和点按相邻样品线性插值；饱和点固定为 C/C₀ ≥ 95%。') }}
            <span v-if="calibrationCount">{{ $t('标定行已排除。') }}</span>
          </p>
          <p v-if="selectedExperiment" class="curve-source">
            <RouterLink :to="{ name: 'archive-detail', params: { id: selectedId } }">
              {{ $t('查看该实验的规范档案') }} →
            </RouterLink>
          </p>
        </template>
      </div>
    </div>
  </div>
</template>

<style scoped>
.curve-builder {
  min-width: 0;
  padding: var(--space-5);
}
.curve-state {
  display: flex;
  align-items: center;
  flex-direction: column;
  justify-content: center;
  min-height: 340px;
  padding: var(--space-7) var(--space-5);
  text-align: center;
}
.curve-state--compact {
  min-height: 180px;
}
.curve-state h3 {
  margin-top: var(--space-4);
  font: var(--text-lg);
  font-weight: 600;
}
.curve-state p {
  max-width: 560px;
  margin: var(--space-2) auto var(--space-4);
  color: var(--text-secondary);
  font: var(--text-sm);
  line-height: 1.75;
}
.curve-state--error {
  color: var(--error);
}
.curve-state-icon {
  display: grid;
  place-items: center;
  width: 48px;
  height: 48px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  background: var(--bg-tertiary);
  color: var(--text-tertiary);
}
.curve-state-icon svg {
  width: 24px;
  height: 24px;
  stroke-width: 1.5;
}
.curve-workspace {
  min-width: 0;
}
.curve-toolbar {
  display: grid;
  grid-template-columns:
    minmax(260px, 2fr)
    minmax(100px, 1fr)
    minmax(132px, 1.16fr)
    minmax(118px, 1fr)
    minmax(118px, 1fr)
    40px;
  gap: var(--space-3);
  align-items: end;
  padding: 14px var(--space-4);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  background: var(--bg-primary);
}
.curve-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}
.curve-field > span {
  min-height: 16px;
  overflow: hidden;
  color: var(--text-tertiary);
  font: var(--text-xs);
  font-weight: 600;
  line-height: 16px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.curve-field .input {
  width: 100%;
  min-width: 0;
  height: 40px;
}
.curve-refresh {
  display: grid;
  place-items: center;
  width: 40px;
  height: 40px;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-md);
  background: var(--bg-primary);
  color: var(--text-secondary);
  font-size: 18px;
}
.curve-refresh:hover:not(:disabled) {
  border-color: var(--accent);
  color: var(--accent);
}
.curve-refresh:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}
.curve-refresh:focus-visible {
  outline: none;
  box-shadow: var(--focus-ring);
}
.curve-actions .btn-compact {
  min-height: 40px;
}
.curve-content {
  padding-top: var(--space-4);
}
.curve-meta {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
  margin-bottom: var(--space-3);
}
.curve-meta > div:first-child {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: var(--space-2);
  min-width: 0;
}
.curve-meta strong {
  font: var(--text-base);
  font-weight: 600;
}
.curve-meta span {
  color: var(--text-tertiary);
  font: var(--text-xs);
}
.curve-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  justify-content: flex-end;
}
.curve-context {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-2) var(--space-4);
  margin-bottom: var(--space-3);
  color: var(--text-secondary);
  font: var(--text-xs);
}
.curve-context strong {
  color: var(--text-primary);
  font-weight: 600;
}
.curve-context em {
  color: var(--text-tertiary);
  font-style: normal;
}
.curve-group-control {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-left: auto;
}
.curve-group-control select {
  height: 28px;
  padding: 0 24px 0 8px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  background: var(--bg-primary);
  color: var(--text-secondary);
  font: var(--text-xs);
}
.curve-group-control select:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: var(--focus-ring);
}
.curve-group-control select:disabled {
  color: var(--text-tertiary);
  cursor: not-allowed;
}
.curve-context-warning {
  color: var(--warning, #b45309);
}
.breakthrough-summary {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: var(--space-3);
  margin-bottom: var(--space-4);
}
.breakthrough-card {
  padding: var(--space-3);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  background: var(--bg-secondary);
}
.breakthrough-card header {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}
.breakthrough-card header i {
  width: 14px;
  height: 3px;
  flex: 0 0 auto;
  border-radius: var(--radius-full);
}
.breakthrough-card header strong {
  overflow: hidden;
  font: var(--text-sm);
  text-overflow: ellipsis;
  white-space: nowrap;
}
.breakthrough-card header small {
  margin-left: auto;
  color: var(--text-tertiary);
  font: var(--text-xs);
  white-space: nowrap;
}
.breakthrough-card dl {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-2);
  margin: var(--space-3) 0 0;
}
.breakthrough-card dl div {
  min-width: 0;
}
.breakthrough-card dt {
  color: var(--text-tertiary);
  font: var(--text-xs);
  line-height: 1.4;
}
.breakthrough-card dd {
  margin: 4px 0 0;
  overflow: hidden;
  color: var(--text-primary);
  font: var(--text-sm);
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.curve-note {
  max-width: 760px;
  margin-top: var(--space-2);
  color: var(--text-tertiary);
  font: var(--text-xs);
  line-height: 1.7;
}
.curve-chart-shell {
  overflow-x: auto;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  background: #fff;
}
.curve-chart {
  display: block;
  width: 100%;
  min-width: 560px;
  height: auto;
}
.curve-legend {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-2) var(--space-4);
  margin-top: var(--space-3);
  color: var(--text-secondary);
  font: var(--text-xs);
}
.curve-legend span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.curve-legend i {
  width: 14px;
  height: 3px;
  border-radius: var(--radius-full);
}
.curve-limit {
  color: var(--text-tertiary);
}
.curve-source {
  margin-top: var(--space-3);
  font: var(--text-xs);
}
.curve-source a {
  color: var(--accent);
  text-decoration: none;
}
.curve-source a:hover {
  text-decoration: underline;
}

@media (max-width: 900px) {
  .curve-toolbar {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .curve-field--experiment {
    grid-column: 1 / -1;
  }
  .curve-refresh {
    width: 100%;
  }
  .curve-meta {
    flex-direction: column;
  }
  .curve-actions {
    justify-content: flex-start;
  }
  .curve-group-control {
    margin-left: 0;
  }
}

@media (max-width: 560px) {
  .curve-builder {
    padding: var(--space-4);
  }
  .curve-toolbar {
    grid-template-columns: 1fr;
  }
  .curve-field--experiment {
    grid-column: auto;
  }
}
</style>
