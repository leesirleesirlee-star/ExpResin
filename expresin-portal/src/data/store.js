/**
 * 分析结果数据源。
 * 优先加载 Python 链路（L1→L5）导出的 /data/analysis.json；
 * 加载失败时回退到 demo.js 的静态样本，保证界面始终可用。
 */

import { computed, ref } from 'vue'
import {
  experiment as demoExperiment,
  initialMessages as demoMessages,
  regions as demoRegions,
} from './demo.js'

export const loading = ref(true)
export const error = ref('')
export const experiments = ref([])
export const activeIndex = ref(0)

export const currentExperiment = computed(() => experiments.value[activeIndex.value] ?? null)

/** 是否正在使用回退数据。 */
export const usingFallback = computed(() => currentExperiment.value === null)

export const regions = computed(() => currentExperiment.value?.regions ?? demoRegions)

export const experiment = computed(() => {
  const e = currentExperiment.value
  if (!e) return demoExperiment
  return {
    id: e.id,
    project: e.project,
    sourceFile: e.sourceFile,
    sheet: e.sheet,
    status: e.status,
    lastSaved: e.lastSaved,
  }
})

function count(exp, fn) {
  let n = 0
  for (const r of exp.regions) for (const b of r.blocks) for (const c of b.columns) if (fn(c, b)) n += 1
  return n
}

/** 会话首屏：把真实统计写进 Jarvis 的开工说明。 */
export const messages = computed(() => {
  const e = currentExperiment.value
  if (!e) return demoMessages

  const blocks = e.regions.reduce((n, r) => n + r.blocks.length, 0)
  const cols = count(e, () => true)
  const mapped = count(e, (c) => Boolean(c.target))
  const labels = count(e, (c) => !c.target && c.raw)
  const low = count(e, (c) => c.target && c.conf < 0.8)
  const ghost = count(e, (c) => !c.target && !c.raw)

  const tail = []
  if (low) tail.push(`${low} 列置信度低于 0.8 需要确认`)
  if (ghost) tail.push(`${ghost} 列空表头已忽略`)

  return [
    {
      id: 1,
      role: 'user',
      text: `加载《${e.sourceFile}》中的 ${e.sheet}，开始识别。`,
    },
    {
      id: 2,
      role: 'jarvis',
      text: `解析完成：${e.regions.length} 个数据区、${blocks} 个列块，共 ${cols} 列。其中 ${mapped} 列已映射到标准字段，${labels} 列判定为离子标签列${tail.length ? '，' + tail.join('，') : ''}。`,
      chips: [
        `${blocks} 个列块`,
        `${mapped} 列已映射`,
        low ? `${low} 列待确认` : '无低置信度项',
      ],
    },
  ]
})

export function selectExperiment(index) {
  if (index >= 0 && index < experiments.value.length) activeIndex.value = index
}

export async function loadAnalysis() {
  try {
    const url = `${import.meta.env.BASE_URL}data/analysis.json`
    const res = await fetch(url, { cache: 'no-store' })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    if (!Array.isArray(data.experiments) || data.experiments.length === 0) {
      throw new Error('analysis.json 中没有可用的实验')
    }
    experiments.value = data.experiments
    activeIndex.value = 0
  } catch (e) {
    error.value = e?.message || String(e)
  } finally {
    loading.value = false
  }
}