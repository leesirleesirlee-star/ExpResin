<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch, nextTick } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { api } from '../data/api.js'
import { loadArchive, session } from '../data/session.js'
import { useToast } from '../composables/useToast.js'
import ProvenanceRail from '../components/ProvenanceRail.vue'

const route = useRoute()
const { show } = useToast()
const record = ref(null)
const loading = ref(true)
// 规范长表：归档产物里的**逐行数据值**（识别骨架只含列映射，value 恒为空）。
const canonical = ref(null)
// 正在执行的导出类型（'' | 'template' | 'csv'），用于按钮禁用与文案切换
const exporting = ref('')

/** 触发浏览器下载：api 返回 {blob, filename} 后走 object URL，失败 toast 后端 detail。 */
async function downloadFile(kind) {
  const id = route.params.id
  exporting.value = kind
  try {
    const { blob, filename } =
      kind === 'template' ? await api.exportTemplate(id) : await api.exportCanonicalCsv(id)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
    show(`已导出 ${filename}`)
  } catch (e) {
    show(e.message || '导出失败，请稍后重试', { tone: 'error' })
  } finally {
    exporting.value = ''
  }
}

onMounted(async () => {
  const id = route.params.id
  await loadArchive()
  let found = session.archive.find((r) => r.id === id) || null

  if (session.online) {
    try {
      const remote = await api.getExperiment(id)
      // 归档时识别的原始快照保存在 processed.recognized_data 里（含 regions / source）。
      // 档案列表接口不返回 regions，若沿用列表里的值，详情页统计会全部显示为 0。
      const snapshot = remote?.processed?.recognized_data || null
      const regions = snapshot?.regions?.length ? snapshot.regions : found?.regions
      found = {
        ...found,
        ...remote,
        regions,
        source_file: remote?.raw_file || snapshot?.source?.file || found?.source_file,
      }
    } catch {
      /* 保留本地记录 */
    }
    try {
      const res = await api.getCanonical(id)
      canonical.value = res?.canonical || null
    } catch {
      // 404 = 尚未生成规范长表（示例档案 / 无可复算数据），属正常情况而非故障
      canonical.value = null
    }
  }
  record.value = found
  loading.value = false
})

const stats = computed(() => {
  const regions = record.value?.regions || []
  let blocks = 0
  let cols = 0
  let mapped = 0
  let low = 0
  for (const r of regions) {
    for (const b of r.blocks || []) {
      blocks += 1
      for (const c of b.columns || []) {
        cols += 1
        if (c.target) mapped += 1
        if (c.target && c.conf < 0.8) low += 1
      }
    }
  }
  return { regions: regions.length, blocks, cols, mapped, low }
})

/**
 * 数据质量警告（后端 checks.py 随取随算，挂在 detail 响应的 warnings 上）。
 * 本地兜底记录 / 旧快照没有该字段时按空数组处理，不渲染本节。
 */
const warnings = computed(() => record.value?.warnings || [])

/** 警告代码 → 徽标文案；未知代码给通用兜底，便于后端后续新增警告类型。 */
function warningLabel(code) {
  return { type_field_mismatch: '类型一致性' }[code] || '数据提示'
}

/** 规范长表的列清单由后端给出，避免前端硬编码列顺序造成漂移。 */
const canonicalColumns = computed(() => canonical.value?.columns || [])
/** 单页最多渲染的行数：列多（24+）时全量渲染会明显拖慢，故截断并提示导出 CSV。 */
const CANONICAL_PREVIEW_ROWS = 100
const canonicalRows = computed(() => (canonical.value?.rows || []).slice(0, CANONICAL_PREVIEW_ROWS))
const canonicalTotal = computed(() => (canonical.value?.rows || []).length)

/**
 * 页内目录跳转：hash 路由下 `href="#xxx"` 会改写 location.hash，
 * 被 Vue Router 当成未匹配路由重定向到工作台，因此必须用 JS 滚动。
 * 目录条为滑块分段控件：点击/滚动时滑块平移到当前区域。
 */
const tocEl = ref(null)
const activeSection = ref('')
const tocSlider = reactive({ x: 0, w: 0, ready: false })
let spyLock = false
let observer = null

async function updateTocSlider() {
  await nextTick()
  const toc = tocEl.value
  if (!toc) return
  const active = toc.querySelector('.toc-link.is-active')
  if (!active) {
    tocSlider.ready = false
    return
  }
  tocSlider.x = active.offsetLeft
  tocSlider.w = active.offsetWidth
  tocSlider.ready = true
}

function setActiveSection(id) {
  if (activeSection.value === id) return
  activeSection.value = id
  updateTocSlider()
}

function scrollToId(id) {
  setActiveSection(id)
  spyLock = true
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  window.setTimeout(() => {
    spyLock = false
  }, 700)
}

/* 滚动侦测：区域进入视口上沿识别带时，滑块跟随过去 */
function setupScrollSpy() {
  observer?.disconnect()
  const ids = (record.value?.regions || []).map((r) => 'region-' + r.id)
  if (canonicalColumns.value.length) ids.push('canonical')
  const els = ids.map((id) => document.getElementById(id)).filter(Boolean)
  if (!els.length) return
  if (!activeSection.value) setActiveSection(ids[0])
  observer = new IntersectionObserver(
    (entries) => {
      if (spyLock) return
      for (const e of entries) {
        if (e.isIntersecting) setActiveSection(e.target.id)
      }
    },
    { rootMargin: '-96px 0px -70% 0px' }
  )
  els.forEach((el) => observer.observe(el))
}

watch(
  () => [record.value?.regions, canonicalColumns.value.length],
  async () => {
    await nextTick()
    setupScrollSpy()
  }
)
onMounted(() => window.addEventListener('resize', updateTocSlider))
onBeforeUnmount(() => {
  observer?.disconnect()
  window.removeEventListener('resize', updateTocSlider)
})

/**
 * 列填充证据：后端在识别骨架里透传 nonNull / fillRatio。
 * 旧快照可能没有这两个字段，此时显示占位符而不是伪造数字。
 */
function fillText(col) {
  const n = col.nonNull
  if (n === undefined || n === null) return '—'
  const ratio = col.fillRatio
  return ratio === undefined || ratio === null ? `${n}` : `${n} · ${Math.round(ratio * 100)}%`
}
</script>

<template>
  <main class="page">
    <div class="wrap">
      <nav class="crumbs">
        <RouterLink to="/archive" class="btn btn-secondary back">
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-linecap="round"
            stroke-linejoin="round"
            aria-hidden="true"
          >
            <path d="M19 12H5" />
            <path d="m12 19-7-7 7-7" />
          </svg>
          返回实验档案
        </RouterLink>
        <span class="crumb-id mono">{{ route.params.id }}</span>
      </nav>

      <div v-if="loading" class="stack">
        <div class="skeleton" style="width: 320px; height: 28px" />
        <div class="skeleton" style="width: 100%; height: 120px" />
      </div>

      <p v-else-if="!record" class="empty muted">
        未找到该实验档案。
      </p>

      <template v-else>
        <header class="head">
          <div>
            <h1>{{ record.title || '（未命名实验）' }}</h1>
            <p class="muted mono">
              {{ record.id }}
              <template v-if="record.source_file"> · {{ record.source_file }}</template>
            </p>
          </div>
          <div class="head-actions">
            <button
              v-if="session.online && record.status !== 'demo'"
              class="btn btn-secondary"
              :disabled="!!exporting"
              @click="downloadFile('template')"
            >
              {{ exporting === 'template' ? '正在导出…' : '导出模板 Excel' }}
            </button>
            <span class="badge" :class="record.status === 'demo' ? 'badge-neutral' : 'badge-success'">
              {{ record.status === 'demo' ? '示例档案' : '已归档' }}
            </span>
          </div>
        </header>

        <dl class="stats">
          <div class="stat">
            <dd class="num">{{ stats.regions }}</dd>
            <dt class="lbl">数据区</dt>
          </div>
          <div class="stat">
            <dd class="num">{{ stats.blocks }}</dd>
            <dt class="lbl">列块</dt>
          </div>
          <div class="stat">
            <dd class="num">{{ stats.mapped }}/{{ stats.cols }}</dd>
            <dt class="lbl">已映射列</dt>
          </div>
          <div class="stat">
            <dd class="num">{{ stats.low }}</dd>
            <dt class="lbl">低置信度</dt>
          </div>
        </dl>

        <section v-if="warnings.length" class="warnings" aria-label="数据质量提示">
          <div v-for="(w, i) in warnings" :key="i" class="warn-item">
            <span class="badge badge-warning warn-badge">{{ warningLabel(w.code) }}</span>
            <div class="warn-body">
              <p class="warn-msg">{{ w.message }}</p>
              <p v-if="(w.columns || []).length" class="muted mono warn-cols">
                {{ w.columns.join('、') }}
              </p>
            </div>
          </div>
        </section>

        <nav
          v-if="(record.regions || []).length || canonicalColumns.length"
          ref="tocEl"
          class="toc"
          aria-label="页内目录"
        >
          <span
            class="toc-slider"
            aria-hidden="true"
            :style="{
              transform: `translateX(${tocSlider.x}px)`,
              width: `${tocSlider.w}px`,
              opacity: tocSlider.ready ? 1 : 0,
            }"
          ></span>
          <button
            v-for="region in record.regions || []"
            :key="region.id"
            type="button"
            class="toc-link"
            :class="{ 'is-active': activeSection === 'region-' + region.id }"
            @click="scrollToId('region-' + region.id)"
          >
            {{ region.kindLabel }}
          </button>
          <button
            v-if="canonicalColumns.length"
            type="button"
            class="toc-link"
            :class="{ 'is-active': activeSection === 'canonical' }"
            @click="scrollToId('canonical')"
          >
            规范长表
          </button>
        </nav>

        <p v-if="record.status === 'demo'" class="notice">
          该档案来自识别链路输出（未经过人工确认写入），因此标记为示例。连接后端并完成一次
          「确认并归档」后，此处将展示正式规范文档。
        </p>

        <section
          v-for="region in record.regions || []"
          :id="'region-' + region.id"
          :key="region.id"
          class="region"
        >
          <header class="region-head">
            <h2>{{ region.kindLabel }}</h2>
            <span class="muted mono">{{ region.title || region.id }}</span>
          </header>

          <article v-for="block in region.blocks" :key="block.id" class="block">
            <div class="block-head">
              <span class="mono muted">{{ block.id }}</span>
              <div class="tags">
                <span v-if="block.analyte" class="badge badge-accent">目标离子 {{ block.analyte }}</span>
                <ProvenanceRail
                  :confidence="block.confidence"
                  :evidence="`已映射 ${(block.columns || []).filter((c) => c.target).length}/${(block.columns || []).length} 列 · 阈值 0.80`"
                />
              </div>
            </div>

            <div class="table-scroll">
              <table class="grid" aria-label="列映射">
                <thead>
                  <tr>
                    <th scope="col">列</th>
                    <th scope="col">原始表头</th>
                    <th scope="col">标准字段</th>
                    <th scope="col">填充</th>
                    <th scope="col">单位</th>
                    <th scope="col">置信度</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="col in block.columns" :key="col.col">
                    <td class="mono dim">{{ col.col }}</td>
                    <td class="mono">{{ col.raw || '（空）' }}</td>
                    <td>{{ col.field || '未映射' }}</td>
                    <td class="mono dim">{{ fillText(col) }}</td>
                    <td class="mono dim">{{ col.unit || col.unitStd || '—' }}</td>
                    <td class="mono" :class="{ warn: col.target && col.conf < 0.8 }">
                      {{ col.conf.toFixed(2) }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </article>
        </section>

        <section v-if="canonicalColumns.length" id="canonical" class="canonical">
          <header class="region-head">
            <h2>规范长表</h2>
            <span class="muted mono">
              {{ canonicalTotal }} 行 · {{ canonicalColumns.length }} 列
            </span>
            <button
              v-if="session.online && record.status !== 'demo'"
              class="btn btn-secondary btn-compact"
              :disabled="!!exporting"
              @click="downloadFile('csv')"
            >
              {{ exporting === 'csv' ? '正在导出…' : '导出 CSV' }}
            </button>
          </header>
          <p class="muted hint">
            归档时从原始文件重读、并由计算引擎复算得到的逐行数据值（
            <span class="mono">canonical_table_v1</span>）。上方各列块表格只描述「列映射」，
            此处才是数据值本身。
          </p>
          <div class="table-scroll">
            <table class="grid" aria-label="规范长表">
              <thead>
                <tr>
                  <th v-for="name in canonicalColumns" :key="name" scope="col">{{ name }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, i) in canonicalRows" :key="i">
                  <td v-for="name in canonicalColumns" :key="name" class="mono dim">
                    {{ row[name] === null || row[name] === undefined || row[name] === '' ? '—' : row[name] }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <p v-if="canonicalTotal > canonicalRows.length" class="muted hint">
            仅展示前 {{ canonicalRows.length }} 行（共 {{ canonicalTotal }} 行），完整数据请用上方「导出 CSV」。
          </p>
        </section>
      </template>
    </div>
  </main>
</template>

<style scoped>
.page {
  min-height: 0;
  overflow-y: auto;
  position: relative;
  z-index: 1;
  scroll-behavior: smooth;
  scroll-padding-top: var(--space-5);
}
.wrap {
  max-width: 1080px;
  margin: 0 auto;
  padding: var(--space-6) var(--space-6) var(--space-9);
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}
.crumbs {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

/* 返回上级页面：复用全局 .btn-secondary 的尺寸，但在灰色画布上给白底 + 细阴影上浮 */
.back {
  height: 40px;
  padding: 0 var(--space-3);
  font: var(--text-xs);
  text-decoration: none;
  background: var(--surface-card);
  border-color: var(--border-subtle);
  box-shadow: var(--shadow-sm);
}
.back:hover:not(:disabled) {
  background: var(--surface-card);
  border-color: var(--border-strong);
  box-shadow: var(--shadow-md);
}
.back svg {
  width: 16px;
  height: 16px;
}
.crumb-id {
  font: var(--text-xs);
  color: var(--text-secondary);
}

.head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
}
/* 头部右侧操作区：导出按钮 + 归档状态徽标，垂直居中对齐 */
.head-actions {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex-shrink: 0;
}
/* 嵌入 section 标题行的紧凑按钮（与 40px 返回按钮同高） */
.btn-compact {
  height: 40px;
  padding: 0 var(--space-3);
  font: var(--text-xs);
  margin-left: auto;
}
.head h1 {
  font: var(--text-xl);
  letter-spacing: var(--tracking-tight);
}
.head p {
  margin-top: var(--space-2);
  font-size: 13px;
}

.stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-3);
  margin: 0;
}
.stat {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  padding: var(--space-4);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  background: var(--bg-secondary);
}
.stat .num,
.stat .lbl {
  margin: 0;
}
.num {
  font: var(--text-lg);
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}
.lbl {
  font: var(--text-xs);
  color: var(--text-secondary);
}

/* 页内目录：吸顶滑块分段控件，与顶栏导航同一视觉语言，整体居中 */
.toc {
  position: sticky;
  top: var(--space-3);
  z-index: 2;
  display: flex;
  flex-wrap: wrap;
  gap: 2px;
  width: fit-content;
  margin: 0 auto var(--space-5);
  padding: 4px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-full);
  background: var(--nav-track);
}
.toc-slider {
  position: absolute;
  top: 4px;
  bottom: 4px;
  left: 0;
  border-radius: var(--radius-full);
  background: var(--surface-card);
  box-shadow: var(--shadow-sm);
  pointer-events: none;
  transition: transform var(--duration-fast) var(--ease-standard),
    width var(--duration-fast) var(--ease-standard),
    opacity var(--duration-fast) var(--ease-standard);
}
.toc-link {
  position: relative;
  z-index: 1;
  display: inline-flex;
  align-items: center;
  min-height: 32px;
  padding: 0 var(--space-3);
  border: 0;
  border-radius: var(--radius-full);
  background: none;
  cursor: pointer;
  font: var(--text-xs);
  color: var(--text-secondary);
  text-decoration: none;
  transition: color var(--duration-fast) var(--ease-standard);
}
.toc-link:hover {
  color: var(--text-primary);
}
.toc-link.is-active {
  color: var(--accent);
  font-weight: 500;
}
.region {
  scroll-margin-top: var(--space-8);
}
#canonical {
  scroll-margin-top: var(--space-8);
}

.notice {
  padding: var(--space-3) var(--space-4);
  border-left: 2px solid var(--warning);
  background: var(--warning-bg);
  border-radius: var(--radius-md);
  font: var(--text-xs);
  line-height: 1.5;
}

/* 数据质量警告：与 .notice 同族的警示肌理，扩展为徽标 + 正文的横排列表 */
.warnings {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
.warn-item {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  border-left: 2px solid var(--warning);
  background: var(--warning-bg);
  border-radius: var(--radius-md);
}
.warn-badge {
  flex: none;
  margin-top: 1px;
}
.warn-body {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  min-width: 0;
}
.warn-msg {
  font: var(--text-xs);
  line-height: 1.5;
}
.warn-cols {
  font-size: 12px;
}

.region-head {
  display: flex;
  align-items: baseline;
  gap: var(--space-3);
  margin-bottom: var(--space-3);
}
.region-head h2 {
  font: var(--text-lg);
}
.region-head span {
  font-size: 12px;
}

.block {
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  background: var(--bg-secondary);
  overflow: hidden;
}
.block + .block {
  margin-top: var(--space-3);
}
.block-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  border-bottom: 1px solid var(--border-subtle);
}
.block-head .mono {
  font-size: 12px;
}
.tags {
  display: flex;
  gap: var(--space-2);
}

.grid {
  width: 100%;
  border-collapse: collapse;
  font: var(--text-sm);
}
.grid th {
  text-align: left;
  font: var(--text-xs);
  font-weight: 500;
  letter-spacing: var(--tracking-caps);
  text-transform: uppercase;
  color: var(--text-tertiary);
  padding: var(--space-2) var(--space-4);
  border-bottom: 1px solid var(--border-subtle);
}
.grid td {
  padding: var(--space-2) var(--space-4);
  border-bottom: 1px solid var(--border-subtle);
}
.grid tbody tr:last-child td {
  border-bottom: none;
}
.grid tbody tr:hover {
  background: var(--bg-tertiary);
}
.dim {
  color: var(--text-secondary);
}
.warn {
  color: var(--warning);
}

/* 规范长表：列多（24+），横向滚动查看，避免列宽被压缩到不可读 */
.canonical {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
.hint {
  font: var(--text-xs);
  line-height: 1.5;
}
.table-scroll {
  overflow-x: auto;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  background: var(--bg-secondary);
}
.table-scroll .grid {
  min-width: max-content;
}
/* 列块内嵌表格已由 .block 提供外框，去掉重复边框 */
.block .table-scroll {
  border: none;
  border-radius: 0;
  background: transparent;
}

.empty {
  font: var(--text-sm);
  padding: var(--space-5);
  border: 1px dashed var(--border-strong);
  border-radius: var(--radius-lg);
}
.stack {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

@media (max-width: 768px) {
  .stats {
    grid-template-columns: repeat(2, 1fr);
  }
  .wrap {
    padding: var(--space-4) var(--space-4) var(--space-8);
  }
}
</style>