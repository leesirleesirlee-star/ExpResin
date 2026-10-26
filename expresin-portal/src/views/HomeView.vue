<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { api } from '../data/api.js'
import { auth } from '../data/auth.js'
import { loadArchive, session } from '../data/session.js'
import { useToast } from '../composables/useToast.js'

const { show } = useToast()
const REPORT_LIMIT = 20

const modules = [
  {
    id: 'growth',
    label: '成长总结',
    desc: 'AI 复盘实验轨迹',
    headline: '从每一次实验记录中，看见进步与下一步。',
    icon: 'M4 19V5M4 19h16M7 15l4-4 3 2 5-7M16 6h3v3',
  },
  {
    id: 'setup',
    label: '实验新建',
    desc: '快速记录与草稿',
    headline: '实验方法与材料的工作区，后续在这里承接。',
    icon: 'M9 3h6M10 3v6l-5 9a2 2 0 0 0 2 3h10a2 2 0 0 0 2-3l-5-9V3M8 15h8',
  },
  {
    id: 'curve',
    label: '曲线生成',
    desc: '标定与穿透曲线',
    headline: '把识别后的实验数据转化为可分析的曲线。',
    icon: 'M4 4v16h16M7 16l4-5 3 3 5-8M7 8h.01',
  },
]

const activeModule = ref('growth')
const currentModule = computed(() => modules.find((m) => m.id === activeModule.value) || modules[0])

/* 管理员在档案页可以看全部，但成长报告永远只分析当前账号自己的数据。 */
const ownArchive = computed(() =>
  session.archive.filter((item) => item.owner_user_id === auth.user?.id),
)
const experimentTypeCount = computed(
  () => new Set(ownArchive.value.map((item) => item.experiment_type).filter(Boolean)).size,
)
const archiveDateRange = computed(() => {
  const dates = ownArchive.value.map((item) => item.date_start).filter(Boolean).sort()
  if (!dates.length) return '暂无日期'
  return dates[0] === dates.at(-1) ? dates[0] : `${dates[0]} 至 ${dates.at(-1)}`
})
const scopeLabel = computed(() =>
  ownArchive.value.length > REPORT_LIMIT
    ? `最近 ${REPORT_LIMIT} 份本人实验档案`
    : `全部 ${ownArchive.value.length} 份本人实验档案`,
)

const focus = ref('')
const generating = ref(false)
const generateError = ref('')
const report = ref(null)
const canGenerate = computed(
  () => session.online && ownArchive.value.length > 0 && !generating.value,
)

async function generateReport() {
  if (!canGenerate.value) return
  generating.value = true
  generateError.value = ''
  try {
    report.value = await api.createGrowthReport({
      focus: focus.value.trim() || undefined,
      limit: REPORT_LIMIT,
    })
    show('成长报告已生成', { tone: 'success' })
  } catch (error) {
    generateError.value = error.message || '报告生成失败，请稍后重试'
  } finally {
    generating.value = false
  }
}

function formatDate(value) {
  return value || '未记录日期'
}

function formatDateTime(value) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN', { hour12: false })
}

const DIRECTIONS = {
  progress: { label: '有进步', className: 'is-progress' },
  steady: { label: '稳定积累', className: 'is-steady' },
  needs_attention: { label: '待加强', className: 'is-attention' },
  insufficient_data: { label: '数据不足', className: 'is-insufficient' },
}

function directionOf(item) {
  return DIRECTIONS[item?.direction] || DIRECTIONS.insufficient_data
}

function reportMarkdown() {
  const r = report.value
  if (!r) return ''
  const stats = r.statistics || {}
  const lines = [
    '# ExpResin 实验成长报告',
    '',
    `- 生成时间：${formatDateTime(r.generated_at)}`,
    `- 分析范围：${r.scope?.experiment_count || 0} 份本人实验档案`,
    `- 规范数据行：${stats.canonical_row_count || 0}`,
    '',
    '## 整体总结',
    '',
    r.summary || '',
    '',
  ]
  if (r.strengths?.length) {
    lines.push('## 已形成的优势', '')
    for (const item of r.strengths) lines.push(`- ${item}`)
    lines.push('')
  }
  lines.push('## 每一次成长经历', '')
  for (const item of r.timeline || []) {
    lines.push(`### ${formatDate(item.date)} · ${item.title || item.experiment_id}`, '')
    lines.push(`- 实验编号：${item.experiment_id}`)
    lines.push(`- 阶段判断：${directionOf(item).label}`)
    lines.push(`- 成长观察：${item.observation}`)
    if (item.evidence) lines.push(`- 依据：${item.evidence}`)
    lines.push('')
  }
  lines.push('## 日后提升目标', '')
  for (const [index, goal] of (r.goals || []).entries()) {
    lines.push(`### ${index + 1}. ${goal.title}`, '')
    lines.push(`- 行动：${goal.action}`)
    lines.push(`- 验收：${goal.metric}`)
    if (goal.timeframe) lines.push(`- 建议周期：${goal.timeframe}`)
    lines.push('')
  }
  if (r.data_gaps?.length) {
    lines.push('## 数据限制', '')
    for (const item of r.data_gaps) lines.push(`- ${item}`)
    lines.push('')
  }
  lines.push('> AI 分析仅用于实验复盘，请结合原始记录与导师反馈判断。')
  return lines.join('\n')
}

async function copyReport() {
  const text = reportMarkdown()
  if (!text) return
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text)
    } else {
      const area = document.createElement('textarea')
      area.value = text
      area.style.position = 'fixed'
      area.style.opacity = '0'
      document.body.appendChild(area)
      area.select()
      const ok = document.execCommand('copy')
      area.remove()
      if (!ok) throw new Error('copy failed')
    }
    show('报告已复制', { tone: 'success' })
  } catch {
    show('复制失败，请改用 Markdown 导出', { tone: 'error' })
  }
}

function downloadReport() {
  const text = reportMarkdown()
  if (!text) return
  const blob = new Blob([text], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `ExpResin_成长报告_${new Date().toISOString().slice(0, 10)}.md`
  link.click()
  window.setTimeout(() => URL.revokeObjectURL(url), 0)
  show('Markdown 报告已导出', { tone: 'success' })
}

onMounted(loadArchive)
</script>

<template>
  <main class="page">
    <div class="wrap">
      <header class="workspace-head">
        <div class="workspace-title">
          <p class="eyebrow">个人研究工作台</p>
          <h1>把每一次实验，变成下一步的进步。</h1>
          <p>实验记录、数据复盘与成长目标，在同一个工作区持续沉淀。</p>
        </div>
        <RouterLink to="/setup" class="btn btn-primary start-btn">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" aria-hidden="true">
            <path d="M12 5v14M5 12h14" />
          </svg>
          开始实验
        </RouterLink>
      </header>

      <div class="module-bar" aria-label="工作台模块">
        <button
          v-for="module in modules"
          :key="module.id"
          class="module-tab"
          :class="{ 'is-active': activeModule === module.id }"
          type="button"
          :aria-pressed="activeModule === module.id"
          @click="activeModule = module.id"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path :d="module.icon" />
          </svg>
          <span class="module-tab-copy">
            <span class="module-tab-label">{{ module.label }}</span>
            <span class="module-tab-desc">{{ module.desc }}</span>
          </span>
          <span class="module-status" :class="{ 'is-ready': module.id === 'growth' }">
            {{ module.id === 'growth' ? '可用' : '占位' }}
          </span>
        </button>
      </div>

      <section class="module-panel" :aria-busy="generating">
        <header class="module-head">
          <div>
            <h2>{{ currentModule.label }}</h2>
            <p>{{ currentModule.headline }}</p>
          </div>
          <RouterLink v-if="activeModule === 'growth'" to="/archive" class="archive-link">
            查看实验档案
            <span aria-hidden="true">→</span>
          </RouterLink>
        </header>

        <Transition name="module-swap" mode="out-in">
          <div :key="activeModule" class="module-content">
            <template v-if="activeModule === 'growth'">
              <div v-if="session.archiveLoading" class="state-block" role="status">
                <span class="spinner" aria-hidden="true"></span>
                <h3>正在读取实验档案</h3>
                <p>确认当前账号可用于成长分析的数据范围。</p>
              </div>

              <div v-else-if="!session.online" class="state-block">
                <h3>后端服务尚未连接</h3>
                <p>成长报告需要读取本人归档并调用 AI，连接后端后再试。</p>
                <button class="btn btn-ghost" type="button" @click="loadArchive">重新连接</button>
              </div>

              <div v-else-if="session.lastArchiveError" class="state-block state-block--error" role="alert">
                <h3>实验档案读取失败</h3>
                <p>{{ session.lastArchiveError }}</p>
                <button class="btn btn-ghost" type="button" @click="loadArchive">重新加载</button>
              </div>

              <div v-else-if="!ownArchive.length" class="state-block">
                <span class="state-icon" aria-hidden="true">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M4 19V5M4 19h16M7 15l4-4 3 2 5-7M16 6h3v3" />
                  </svg>
                </span>
                <h3>先完成一次实验，再回来看成长</h3>
                <p>没有本人归档时不会生成空泛结论。完成实验录入与数据归档后，这里就能开始复盘。</p>
                <RouterLink to="/setup" class="btn btn-primary">开始第一次实验</RouterLink>
              </div>

              <div v-else class="growth-workspace">
                <section class="growth-config">
                  <div class="config-main">
                    <div>
                      <h3>生成阶段性成长报告</h3>
                      <p>AI 将分析{{ scopeLabel }}，梳理每次实验的成长观察与后续目标。</p>
                    </div>
                    <button class="btn btn-primary generate-btn" type="button" :disabled="!canGenerate" @click="generateReport">
                      <span v-if="generating" class="spinner spinner--button" aria-hidden="true"></span>
                      {{ generating ? '正在生成…' : report ? '重新生成报告' : '生成成长报告' }}
                    </button>
                  </div>

                  <div class="focus-field">
                    <label for="growth-focus">希望重点提升的方向 <span>选填</span></label>
                    <input
                      id="growth-focus"
                      v-model="focus"
                      class="input"
                      type="text"
                      maxlength="160"
                      :disabled="generating"
                      placeholder="例如：提高数据复核能力，或减少实验记录遗漏"
                    />
                  </div>

                  <dl class="archive-facts">
                    <div><dt>本人档案</dt><dd>{{ ownArchive.length }} 份</dd></div>
                    <div><dt>实验类型</dt><dd>{{ experimentTypeCount }} 类</dd></div>
                    <div><dt>记录时间</dt><dd>{{ archiveDateRange }}</dd></div>
                  </dl>
                  <p class="privacy-note">仅使用当前登录账号的归档数据；AI 结论用于复盘，不替代原始记录与导师评价。</p>
                </section>

                <div v-if="generating" class="report-loading" role="status">
                  <span class="spinner" aria-hidden="true"></span>
                  <div>
                    <h3>正在阅读实验轨迹并生成报告</h3>
                    <p>分析实验记录、规范数据与复核信息，可能需要片刻，请勿重复提交。</p>
                  </div>
                </div>

                <div v-else-if="generateError" class="report-error" role="alert">
                  <div><strong>这次未能生成报告</strong><p>{{ generateError }}</p></div>
                  <button class="btn btn-ghost" type="button" @click="generateReport">重试</button>
                </div>

                <article v-if="report" class="growth-report">
                  <header class="report-head">
                    <div>
                      <p class="report-eyebrow">EXPRESIN · GROWTH REPORT</p>
                      <h2>我的实验成长报告</h2>
                      <p>{{ formatDateTime(report.generated_at) }} · 基于 {{ report.scope?.experiment_count || 0 }} 份实验档案</p>
                    </div>
                    <div class="report-actions">
                      <button class="btn btn-ghost report-action" type="button" @click="copyReport">复制报告</button>
                      <button class="btn btn-ghost report-action" type="button" @click="downloadReport">导出 Markdown</button>
                    </div>
                  </header>

                  <section class="report-section report-summary">
                    <h3>整体总结</h3>
                    <p>{{ report.summary }}</p>
                    <dl class="report-stats">
                      <div><dt>分析档案</dt><dd>{{ report.statistics?.experiment_count || 0 }} 份</dd></div>
                      <div><dt>含原始数据</dt><dd>{{ report.statistics?.with_raw_data_count || 0 }} 份</dd></div>
                      <div><dt>规范数据行</dt><dd>{{ report.statistics?.canonical_row_count || 0 }} 行</dd></div>
                      <div><dt>质量提示</dt><dd>{{ report.statistics?.warning_count || 0 }} 条</dd></div>
                    </dl>
                  </section>

                  <section v-if="report.strengths?.length" class="report-section">
                    <h3>已形成的优势</h3>
                    <ul class="strength-list">
                      <li v-for="item in report.strengths" :key="item"><span aria-hidden="true">✓</span>{{ item }}</li>
                    </ul>
                  </section>

                  <section class="report-section">
                    <div class="section-title-row">
                      <h3>每一次成长经历</h3>
                      <span>按实验时间排列</span>
                    </div>
                    <ol class="timeline-list">
                      <li v-for="item in report.timeline || []" :key="item.experiment_id" class="timeline-item">
                        <time>{{ formatDate(item.date) }}</time>
                        <div class="timeline-content">
                          <div class="timeline-title">
                            <div>
                              <h4>{{ item.title || '（未命名实验）' }}</h4>
                              <RouterLink :to="`/archive/${item.experiment_id}`" class="experiment-id mono">{{ item.experiment_id }}</RouterLink>
                            </div>
                            <span class="direction-badge" :class="directionOf(item).className">{{ directionOf(item).label }}</span>
                          </div>
                          <p>{{ item.observation }}</p>
                          <p v-if="item.evidence" class="timeline-evidence"><strong>记录依据</strong>{{ item.evidence }}</p>
                        </div>
                      </li>
                    </ol>
                  </section>

                  <section class="report-section">
                    <div class="section-title-row">
                      <h3>日后提升目标</h3>
                      <span>行动与验收方式</span>
                    </div>
                    <ol class="goal-list">
                      <li v-for="(goal, index) in report.goals || []" :key="`${goal.title}-${index}`">
                        <span class="goal-number">{{ String(index + 1).padStart(2, '0') }}</span>
                        <div>
                          <div class="goal-title"><h4>{{ goal.title }}</h4><span v-if="goal.timeframe">{{ goal.timeframe }}</span></div>
                          <p>{{ goal.action }}</p>
                          <p class="goal-metric"><strong>验收方式</strong>{{ goal.metric }}</p>
                        </div>
                      </li>
                    </ol>
                  </section>

                  <details v-if="report.data_gaps?.length" class="report-gaps">
                    <summary>查看本次分析的数据限制（{{ report.data_gaps.length }}）</summary>
                    <ul><li v-for="item in report.data_gaps" :key="item">{{ item }}</li></ul>
                  </details>
                  <footer class="report-foot">报告由 AI 基于所选档案生成，请结合实验原始记录与导师反馈使用。</footer>
                </article>
              </div>
            </template>

            <div v-else class="placeholder-state">
              <span class="placeholder-icon" aria-hidden="true">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"><path :d="currentModule.icon" /></svg>
              </span>
              <span class="placeholder-tag">模块占位 · 尚未开放</span>
              <h3>{{ activeModule === 'setup' ? '实验新建工作区' : '曲线生成工作区' }}</h3>
              <p v-if="activeModule === 'setup'">后续将在这里承接快速新建、草稿续接与最近录入。目前请使用页面右上角的「开始实验」。</p>
              <p v-else>后续将在这里承接标定曲线、穿透曲线与图形导出。目前可在数据识别页查看已识别曲线。</p>
              <RouterLink :to="activeModule === 'setup' ? '/setup' : '/recognize'" class="btn btn-ghost">
                {{ activeModule === 'setup' ? '前往新建实验' : '前往数据识别' }}
              </RouterLink>
            </div>
          </div>
        </Transition>
      </section>
    </div>
  </main>
</template>

<style scoped>
.page {
  min-height: 0;
  overflow-y: auto;
  position: relative;
  z-index: 1;
}
.wrap {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
  max-width: 1120px;
  margin: 0 auto;
  padding: var(--space-7) var(--space-6) var(--space-9);
}
.workspace-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--space-6);
}
.workspace-title {
  min-width: 0;
}
.eyebrow {
  margin-bottom: var(--space-2);
  color: var(--accent);
  font: var(--text-xs);
  font-weight: 600;
}
.workspace-head h1 {
  max-width: 720px;
  font-size: clamp(26px, 3.4vw, 36px);
  font-weight: 620;
  line-height: 1.28;
  letter-spacing: -0.035em;
}
.workspace-title > p:last-child {
  margin-top: var(--space-3);
  color: var(--text-secondary);
  font: var(--text-sm);
  line-height: 1.7;
}
.start-btn {
  flex: none;
  height: 46px;
  padding-inline: var(--space-5);
  text-decoration: none;
}
.start-btn svg {
  width: 17px;
  height: 17px;
  stroke-width: 2;
}

.module-bar {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-1);
  padding: 4px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  background: var(--bg-tertiary);
}
.module-tab {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  min-height: 58px;
  padding: 8px 12px;
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  background: transparent;
  color: var(--text-secondary);
  text-align: left;
  cursor: pointer;
  transition: background var(--duration-fast) var(--ease-standard),
    border-color var(--duration-fast) var(--ease-standard),
    color var(--duration-fast) var(--ease-standard),
    box-shadow var(--duration-fast) var(--ease-standard);
}
.module-tab:hover {
  color: var(--text-primary);
  background: color-mix(in srgb, var(--bg-card) 55%, transparent);
}
.module-tab.is-active {
  border-color: var(--border-subtle);
  background: var(--bg-card);
  box-shadow: var(--shadow-xs);
  color: var(--text-primary);
}
.module-tab > svg {
  flex: none;
  width: 20px;
  height: 20px;
  color: var(--text-tertiary);
  stroke-width: 1.7;
}
.module-tab.is-active > svg {
  color: var(--accent);
}
.module-tab-copy {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}
.module-tab-label,
.module-tab-desc {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.module-tab-label {
  font-size: 14px;
  font-weight: 600;
}
.module-tab-desc {
  color: var(--text-tertiary);
  font-size: 11px;
}
.module-status {
  flex: none;
  padding: 2px 6px;
  border-radius: var(--radius-sm);
  background: var(--bg-secondary);
  color: var(--text-tertiary);
  font-size: 10px;
}
.module-status.is-ready {
  background: var(--success-bg);
  color: var(--success);
}

.module-panel {
  min-width: 0;
  overflow: hidden;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-xl);
  background: var(--bg-secondary);
  box-shadow: var(--shadow-sm);
}
.module-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  min-height: 76px;
  padding: var(--space-4) var(--space-5);
  border-bottom: 1px solid var(--border-subtle);
}
.module-head h2 {
  font: var(--text-lg);
  font-weight: 600;
}
.module-head p {
  margin-top: 3px;
  color: var(--text-tertiary);
  font: var(--text-xs);
  line-height: 1.5;
}
.archive-link {
  display: inline-flex;
  flex: none;
  gap: 6px;
  color: var(--text-secondary);
  font: var(--text-xs);
  text-decoration: none;
}
.archive-link:hover {
  color: var(--accent);
}
.module-content {
  min-width: 0;
}
.module-swap-enter-active,
.module-swap-leave-active {
  transition: opacity 160ms var(--ease-standard), transform 160ms var(--ease-standard);
}
.module-swap-enter-from {
  opacity: 0;
  transform: translateY(4px);
}
.module-swap-leave-to {
  opacity: 0;
  transform: translateY(-3px);
}

.state-block,
.placeholder-state {
  display: flex;
  align-items: center;
  flex-direction: column;
  justify-content: center;
  min-height: 340px;
  padding: var(--space-7) var(--space-5);
  text-align: center;
}
.state-block h3,
.placeholder-state h3 {
  margin-top: var(--space-4);
  font: var(--text-lg);
  font-weight: 600;
}
.state-block p,
.placeholder-state p {
  max-width: 520px;
  margin: var(--space-2) auto var(--space-4);
  color: var(--text-secondary);
  font: var(--text-sm);
  line-height: 1.75;
}
.state-block > .btn,
.placeholder-state > .btn {
  text-decoration: none;
}
.state-block--error {
  color: var(--error);
}
.state-icon,
.placeholder-icon {
  display: grid;
  place-items: center;
  width: 48px;
  height: 48px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  background: var(--bg-tertiary);
  color: var(--text-tertiary);
}
.state-icon svg,
.placeholder-icon svg {
  width: 24px;
  height: 24px;
  stroke-width: 1.5;
}
.placeholder-tag {
  margin-top: var(--space-4);
  color: var(--text-tertiary);
  font: var(--text-xs);
}
.placeholder-state h3 {
  margin-top: var(--space-2);
}

.growth-config {
  padding: var(--space-5);
}
.config-main {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-5);
}
.config-main h3 {
  font: var(--text-base);
  font-weight: 600;
}
.config-main p {
  margin-top: 5px;
  color: var(--text-secondary);
  font: var(--text-sm);
  line-height: 1.6;
}
.generate-btn {
  flex: none;
  min-width: 144px;
}
.focus-field {
  max-width: 620px;
  margin-top: var(--space-4);
}
.focus-field label {
  display: block;
  margin-bottom: 6px;
  color: var(--text-secondary);
  font: var(--text-xs);
}
.focus-field label span {
  margin-left: 4px;
  color: var(--text-tertiary);
}
.focus-field .input {
  width: 100%;
  background: var(--bg-primary);
}
.archive-facts {
  display: grid;
  grid-template-columns: 0.7fr 0.7fr 1.6fr;
  gap: var(--space-4);
  margin: var(--space-5) 0 0;
  padding: var(--space-4) 0;
  border-top: 1px solid var(--border-subtle);
  border-bottom: 1px solid var(--border-subtle);
}
.archive-facts dt {
  color: var(--text-tertiary);
  font: var(--text-xs);
}
.archive-facts dd {
  margin: 4px 0 0;
  overflow-wrap: anywhere;
  font: var(--text-sm);
  font-weight: 550;
}
.privacy-note {
  margin-top: var(--space-3);
  color: var(--text-tertiary);
  font: var(--text-xs);
  line-height: 1.6;
}
.report-loading,
.report-error {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  margin: 0 var(--space-5) var(--space-5);
  padding: var(--space-4);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  background: var(--bg-tertiary);
}
.report-loading h3 {
  font: var(--text-sm);
  font-weight: 600;
}
.report-loading p,
.report-error p {
  margin-top: 4px;
  color: var(--text-secondary);
  font: var(--text-xs);
  line-height: 1.6;
}
.report-error {
  justify-content: space-between;
  border-color: color-mix(in srgb, var(--error) 35%, transparent);
  background: var(--error-bg);
}
.report-error strong {
  font: var(--text-sm);
}
.spinner {
  display: inline-block;
  flex: none;
  width: 24px;
  height: 24px;
  border: 2px solid var(--border-strong);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 800ms linear infinite;
}
.spinner--button {
  width: 15px;
  height: 15px;
  border-color: rgb(255 255 255 / 35%);
  border-top-color: currentColor;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}

.growth-report {
  border-top: 1px solid var(--border-subtle);
}
.report-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
  padding: var(--space-5);
  background: var(--bg-tertiary);
}
.report-eyebrow {
  color: var(--accent);
  font: 10px var(--font-mono);
  letter-spacing: 0.08em;
}
.report-head h2 {
  margin-top: 6px;
  font-size: 22px;
  font-weight: 620;
  letter-spacing: -0.025em;
}
.report-head > div > p:last-child {
  margin-top: 6px;
  color: var(--text-tertiary);
  font: var(--text-xs);
}
.report-actions {
  display: flex;
  flex: none;
  gap: var(--space-2);
}
.report-action {
  min-height: 36px;
  height: 36px;
  padding-inline: var(--space-3);
  font-size: 12px;
}
.report-section {
  padding: var(--space-5);
  border-top: 1px solid var(--border-subtle);
}
.report-section > h3,
.section-title-row h3 {
  font: var(--text-base);
  font-weight: 600;
}
.report-summary > p {
  margin-top: var(--space-3);
  font-size: 15px;
  line-height: 1.9;
  white-space: pre-line;
}
.report-stats {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-5) var(--space-7);
  margin: var(--space-5) 0 0;
  padding-top: var(--space-4);
  border-top: 1px solid var(--border-subtle);
}
.report-stats dt {
  color: var(--text-tertiary);
  font: var(--text-xs);
}
.report-stats dd {
  margin: 4px 0 0;
  font: var(--text-lg);
  font-weight: 600;
}
.strength-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-3) var(--space-5);
  margin: var(--space-4) 0 0;
  padding: 0;
  list-style: none;
}
.strength-list li {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
  color: var(--text-secondary);
  font: var(--text-sm);
  line-height: 1.65;
}
.strength-list li > span {
  flex: none;
  color: var(--success);
  font-weight: 700;
}
.section-title-row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--space-3);
}
.section-title-row > span {
  color: var(--text-tertiary);
  font: var(--text-xs);
}
.timeline-list,
.goal-list {
  margin: var(--space-5) 0 0;
  padding: 0;
  list-style: none;
}
.timeline-item {
  display: grid;
  grid-template-columns: 100px minmax(0, 1fr);
  gap: var(--space-5);
  padding: var(--space-4) 0;
  border-top: 1px solid var(--border-subtle);
}
.timeline-item:first-child {
  padding-top: 0;
  border-top: none;
}
.timeline-item > time {
  padding-top: 2px;
  color: var(--text-tertiary);
  font: 12px var(--font-mono);
}
.timeline-content {
  min-width: 0;
}
.timeline-title {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-3);
}
.timeline-title h4,
.goal-title h4 {
  font: var(--text-sm);
  font-weight: 600;
  line-height: 1.5;
}
.experiment-id {
  display: inline-block;
  margin-top: 3px;
  color: var(--text-tertiary);
  font-size: 11px;
  text-decoration: none;
}
.experiment-id:hover {
  color: var(--accent);
}
.timeline-content > p,
.goal-list li > div > p {
  margin-top: var(--space-3);
  color: var(--text-secondary);
  font: var(--text-sm);
  line-height: 1.8;
}
.direction-badge {
  flex: none;
  padding: 3px 8px;
  border-radius: var(--radius-sm);
  font-size: 11px;
  white-space: nowrap;
}
.direction-badge.is-progress { background: var(--success-bg); color: var(--success); }
.direction-badge.is-steady { background: var(--accent-subtle); color: var(--accent); }
.direction-badge.is-attention { background: var(--warning-bg); color: var(--warning); }
.direction-badge.is-insufficient { background: var(--bg-tertiary); color: var(--text-tertiary); }
.timeline-evidence {
  padding: var(--space-3);
  border-left: 2px solid var(--border-strong);
  background: var(--bg-tertiary);
  font-size: 12px !important;
}
.timeline-evidence strong,
.goal-metric strong {
  display: block;
  margin-bottom: 3px;
  color: var(--text-primary);
  font-size: 11px;
  font-weight: 600;
}
.goal-list > li {
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr);
  gap: var(--space-4);
  padding: var(--space-4) 0;
  border-top: 1px solid var(--border-subtle);
}
.goal-list > li:first-child {
  padding-top: 0;
  border-top: none;
}
.goal-number {
  color: var(--accent);
  font: 12px var(--font-mono);
  line-height: 1.8;
}
.goal-title {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--space-3);
}
.goal-title > span {
  flex: none;
  color: var(--text-tertiary);
  font: var(--text-xs);
}
.goal-metric {
  padding: var(--space-3);
  border-radius: var(--radius-md);
  background: var(--bg-tertiary);
  font-size: 12px !important;
}
.report-gaps {
  margin: 0 var(--space-5) var(--space-4);
  color: var(--text-secondary);
  font: var(--text-xs);
}
.report-gaps summary {
  cursor: pointer;
}
.report-gaps ul {
  margin: var(--space-3) 0 0;
  padding-left: var(--space-5);
  line-height: 1.7;
}
.report-foot {
  padding: 0 var(--space-5) var(--space-5);
  color: var(--text-tertiary);
  font: var(--text-xs);
  line-height: 1.6;
}

@media (max-width: 760px) {
  .workspace-head {
    align-items: flex-start;
  }
  .workspace-head h1 {
    font-size: 27px;
  }
  .module-tab {
    justify-content: center;
    padding-inline: 8px;
  }
  .module-tab-desc,
  .module-status {
    display: none;
  }
  .module-tab-copy {
    flex: none;
  }
  .config-main,
  .report-head {
    align-items: stretch;
    flex-direction: column;
  }
  .generate-btn {
    align-self: flex-start;
  }
  .report-actions {
    align-self: flex-start;
  }
  .archive-facts {
    grid-template-columns: 1fr 1fr;
  }
  .archive-facts > div:last-child {
    grid-column: 1 / -1;
  }
  .timeline-item {
    grid-template-columns: 1fr;
    gap: var(--space-2);
  }
}

@media (max-width: 480px) {
  .wrap {
    gap: var(--space-4);
    padding: var(--space-5) var(--space-4) var(--space-8);
  }
  .workspace-head {
    flex-direction: column;
    gap: var(--space-4);
  }
  .workspace-head h1 {
    font-size: 25px;
  }
  .start-btn {
    align-self: stretch;
    justify-content: center;
  }
  .module-tab {
    gap: 6px;
    min-height: 48px;
  }
  .module-tab > svg {
    width: 17px;
    height: 17px;
  }
  .module-tab-label {
    font-size: 12px;
  }
  .module-head,
  .growth-config,
  .report-head,
  .report-section {
    padding: var(--space-4);
  }
  .module-head {
    align-items: flex-start;
  }
  .module-head p {
    max-width: 240px;
  }
  .archive-link {
    font-size: 11px;
  }
  .strength-list {
    grid-template-columns: 1fr;
  }
  .timeline-title,
  .goal-title {
    align-items: flex-start;
    flex-direction: column;
    gap: var(--space-2);
  }
  .report-loading,
  .report-error {
    align-items: flex-start;
    margin: 0 var(--space-4) var(--space-4);
  }
  .report-error {
    flex-direction: column;
  }
  .report-gaps {
    margin-inline: var(--space-4);
  }
  .report-foot {
    padding-inline: var(--space-4);
  }
}

@media (prefers-reduced-motion: reduce) {
  .module-swap-enter-active,
  .module-swap-leave-active {
    transition: none;
  }
}
</style>
