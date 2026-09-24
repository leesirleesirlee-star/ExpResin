<script setup>
/**
 * 数据识别页专用右边栏。
 *
 * 与录入页的 MetadataInspector 刻意分开：这里关心的是「列映射是否可信」，
 * 因此除了列出低置信度等问题，必须提供人工处置入口 ——
 * 只报告问题却不给确认按钮，等于把问题丢回给用户。
 *
 * 三种人工处置都会成为可追溯的判定记录（后端以追加新版本的方式保存）：
 *   confirm：确认系统判定正确
 *   remap  ：改判为另一个合法标准字段
 *   ignore ：判定为非数据列（标签列/空列），不参与 Processed
 */
import { computed, ref, watch } from 'vue'

const props = defineProps({
  issues: { type: Object, default: () => ({}) },
  regions: { type: Array, default: () => [] },
  selected: { type: Object, default: null },
  /** { kind: [{ key, label, unit }] } 来自标准 Schema，保证改判目标一定合法 */
  schemaColumns: { type: Object, default: () => ({}) },
  /** [{ key, label }] 列块级离子判定的候选离子 */
  analyteOptions: { type: Array, default: () => [] },
})

const emit = defineEmits(['select', 'resolve', 'confirm'])

const stats = computed(() => [
  { key: 'lowConfidence', label: '低置信度', value: (props.issues.lowConfidence ?? []).length },
  { key: 'pending', label: '未映射', value: (props.issues.pending ?? []).length },
  { key: 'unitErrors', label: '单位冲突', value: (props.issues.unitErrors ?? []).length },
  { key: 'missing', label: '幽灵列', value: (props.issues.missing ?? []).length },
  { key: 'analyteConflicts', label: '离子存疑', value: (props.issues.analyteConflicts ?? []).length },
  { key: 'failedBlocks', label: '块失败', value: (props.issues.failedBlocks ?? []).length },
])

/**
 * 「待处理」只统计可由人工就地处置的项。
 * 列块识别失败（block-failed）不是列级问题，没有 confirm/remap/ignore 入口，
 * 若计入总数会让计数永远无法清零，反而误导用户。
 */
const total = computed(() =>
  stats.value.filter((s) => s.key !== 'failedBlocks').reduce((n, s) => n + s.value, 0),
)

const groups = computed(() =>
  [
    { key: 'lowConfidence', label: '低置信度', tone: 'warning', items: props.issues.lowConfidence },
    { key: 'pending', label: '未映射列', tone: 'warning', items: props.issues.pending },
    { key: 'unitErrors', label: '单位冲突', tone: 'error', items: props.issues.unitErrors },
    { key: 'missing', label: '缺失 / 幽灵列', tone: 'warning', items: props.issues.missing },
    {
      key: 'analyteConflicts',
      label: '离子判定存疑',
      tone: 'error',
      items: props.issues.analyteConflicts ?? [],
    },
    {
      key: 'failedBlocks',
      label: '识别失败的列块',
      tone: 'error',
      items: props.issues.failedBlocks ?? [],
    },
  ].filter((g) => (g.items ?? []).length),
)

/** 从识别结果反查选中列所属的列块类型，用于给出合法的目标字段候选。 */
const selectedKind = computed(() => {
  if (!props.selected) return null
  for (const region of props.regions) {
    for (const block of region.blocks ?? []) {
      if (block.id !== props.selected.block) continue
      return block.kind ?? region.kind ?? null
    }
  }
  return null
})

/** 离子判定不是某一列的取值，而是整个列块的结论，因此单独识别。 */
const isAnalyteRow = computed(() => props.selected?.col === 'analyte')

/**
 * 整个列块识别失败：没有可处置的列。
 * 必须与列级问题区分开 —— 后端只接受「真实列」的 confirm/remap/ignore，
 * 对这类项发起列级请求只会拿到 404，所以这里只提示重试路径。
 */
const isBlockFailed = computed(() => props.selected?.state === 'block-failed')

/** 列级改判取标准字段；离子行取离子标签候选。 */
const options = computed(() =>
  isAnalyteRow.value
    ? (props.analyteOptions ?? []).map((o) => ({ key: o.key, label: o.label, unit: null }))
    : (props.schemaColumns[selectedKind.value] ?? []),
)

const targetDraft = ref('')

/** 当前生效的判定值：列用 target 字段，离子行用列块级 analyte。 */
const currentValue = computed(() =>
  isAnalyteRow.value ? (props.selected?.analyte ?? '') : (props.selected?.target ?? ''),
)

const review = computed(() =>
  isAnalyteRow.value ? (props.selected?.analyteReview ?? null) : (props.selected?.review ?? null),
)

watch(
  () => props.selected,
  () => {
    targetDraft.value = currentValue.value
  },
)

const REVIEW_LABEL = {
  confirm: '已确认判定正确',
  remap: '已改判',
  ignore: '已判定为非数据列',
}

function resolve(action, targetField) {
  if (!props.selected) return
  emit('resolve', {
    block: props.selected.block,
    col: props.selected.col,
    action,
    target_field: targetField ?? null,
  })
}
</script>

<template>
  <aside class="map-inspector" aria-label="映射确认面板">
    <div class="panel-head">
      <span class="caps">映射确认</span>
      <span class="badge" :class="total ? 'badge-warning' : 'badge-success'">
        {{ total ? `${total} 项待处理` : '全部通过' }}
      </span>
    </div>

    <div class="body">
      <!-- 概览 -->
      <section class="stats">
        <div v-for="s in stats" :key="s.key" class="stat">
          <span class="stat-num mono">{{ s.value }}</span>
          <span class="stat-label">{{ s.label }}</span>
        </div>
      </section>

      <!-- 问题分组 -->
      <section v-for="g in groups" :key="g.key" class="block">
        <h3 class="caps group-title">
          {{ g.label }}
          <span class="mono group-count">{{ g.items.length }}</span>
        </h3>
        <ul class="list">
          <li v-for="item in g.items" :key="`${g.key}-${item.block}/${item.col}`">
            <button
              class="issue"
              type="button"
              :class="[`issue--${g.tone}`, { 'is-active': selected && selected.block === item.block && selected.col === item.col }]"
              @click="$emit('select', item)"
            >
              <span class="issue-top">
                <span class="mono col">{{ item.col }}</span>
                <span class="raw mono">{{ item.raw || '（空表头）' }}</span>
                <span v-if="typeof item.conf === 'number'" class="conf mono">
                  {{ item.conf.toFixed(2) }}
                </span>
              </span>
              <span class="issue-body muted">{{ item.evidence }}</span>
            </button>
          </li>
        </ul>
      </section>

      <p v-if="!total" class="empty muted">
        没有需要人工处置的列。所有列均已映射且置信度合格。
      </p>

      <!-- 人工确认区 -->
      <section class="block confirm-block">
        <h3 class="caps group-title">人工确认</h3>

        <p v-if="!selected" class="empty muted">
          在左侧识别结果或上方清单中点选一列，即可确认、改判或忽略它的映射。
        </p>

        <template v-else>
          <div class="sel-head">
            <span class="mono sel-col">{{ isBlockFailed ? '整块' : selected.col }}</span>
            <span class="sel-arrow">→</span>
            <span class="sel-target">
              {{
                isBlockFailed
                  ? '识别失败'
                  : isAnalyteRow
                    ? `离子判定：${selected.analyte || '—'}`
                    : selected.field || selected.target || '未映射'
              }}
            </span>
          </div>

          <dl class="sel-meta">
            <div v-if="!isBlockFailed" class="meta-row">
              <dt>原始表头</dt>
              <dd class="mono">{{ selected.raw || '（空）' }}</dd>
            </div>
            <div class="meta-row">
              <dt>所属列块</dt>
              <dd class="mono">{{ selected.block }}</dd>
            </div>
            <div v-if="isAnalyteRow" class="meta-row">
              <dt>标签列证据</dt>
              <dd class="mono">{{ selected.expected || '—' }}</dd>
            </div>
            <div class="meta-row">
              <dt>置信度</dt>
              <dd class="mono">
                {{ typeof selected.conf === 'number' ? selected.conf.toFixed(2) : '—' }}
              </dd>
            </div>
            <div class="meta-row meta-row--stack">
              <dt>判定证据</dt>
              <dd>{{ selected.evidence || '—' }}</dd>
            </div>
          </dl>

          <p v-if="review" class="review-done">
            人工判定：{{ REVIEW_LABEL[review.status] || review.status }}
            <span v-if="review.at" class="muted mono">（{{ review.at }}）</span>
          </p>

          <!-- 列块识别失败：没有列级处置入口，只引导重试，避免发出必然 404 的请求 -->
          <div v-if="isBlockFailed" class="actions">
            <p class="empty muted tiny">
              该列块整体识别失败，没有可逐列处置的映射。请重新上传该文件或重试识别；
              失败只会降级为待确认，原始数据不会被丢弃。
            </p>
            <button
              class="btn btn-secondary act"
              type="button"
              @click="$emit('select', null)"
            >
              知道了
            </button>
          </div>

          <div v-else class="actions">
            <button
              class="btn btn-primary act"
              type="button"
              :disabled="!currentValue"
              @click="resolve('confirm')"
            >
              {{ isAnalyteRow ? '确认离子判定' : '确认此映射' }}
            </button>
            <p v-if="isAnalyteRow" class="empty muted tiny">
              离子判定是该列块的结论（整块测的是哪种离子），确认后会清除存疑标记。
            </p>

            <div class="remap">
              <label class="caps remap-label" :for="`remap-${selected.block}-${selected.col}`">
                {{ isAnalyteRow ? '改判为离子' : '改判为' }}
              </label>
              <select
                :id="`remap-${selected.block}-${selected.col}`"
                v-model="targetDraft"
                class="input remap-select"
              >
                <option value="">{{ isAnalyteRow ? '选择离子…' : '选择标准字段…' }}</option>
                <option v-for="o in options" :key="o.key" :value="o.key">
                  {{ o.label }}{{ o.unit ? `（${o.unit}）` : '' }}{{ isAnalyteRow ? '' : ` · ${o.key}` }}
                </option>
              </select>
              <button
                class="btn btn-secondary act"
                type="button"
                :disabled="!targetDraft || targetDraft === currentValue"
                @click="resolve('remap', targetDraft)"
              >
                应用改判
              </button>
            </div>

            <button
              v-if="!isAnalyteRow"
              class="btn btn-ghost act"
              type="button"
              @click="resolve('ignore')"
            >
              标记为非数据列
            </button>
          </div>
        </template>
      </section>
    </div>

    <div class="foot">
      <button class="btn btn-primary block-btn" type="button" @click="$emit('confirm')">
        确认并写入 Processed
      </button>
      <p class="foot-hint muted">
        人工判定会作为新版本追加保存，原始识别结果与 Raw 文件都不会被覆盖。
      </p>
    </div>
  </aside>
</template>

<style scoped>
.map-inspector {
  display: flex;
  flex-direction: column;
  min-height: 0;
  min-width: 0;
  background: var(--bg-secondary);
  border-left: 1px solid var(--border-subtle);
}

.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 48px;
  padding: 0 var(--space-4);
  border-bottom: 1px solid var(--border-subtle);
  flex: none;
}

.body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}

.stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-2);
}
.stat {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  background: var(--bg-primary);
}
.stat-num {
  font: var(--text-lg);
  color: var(--text-primary);
}
.stat-label {
  font: var(--text-xs);
  color: var(--text-secondary);
}

.block {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
.group-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.group-count {
  font-size: 12px;
  color: var(--text-secondary);
}
.empty {
  font: var(--text-sm);
}
.tiny {
  font: var(--text-xs);
}

.list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.issue {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  width: 100%;
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--border-subtle);
  border-left-width: 2px;
  border-radius: var(--radius-md);
  background: var(--bg-primary);
  text-align: left;
  cursor: pointer;
  transition: background var(--duration-fast) var(--ease-standard);
}
.issue--warning {
  border-left-color: var(--warning);
}
.issue--error {
  border-left-color: var(--error);
}
.issue:hover {
  background: var(--bg-tertiary);
}
.issue.is-active {
  border-color: var(--accent);
  background: var(--bg-tertiary);
}
.issue-top {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font: var(--text-sm);
}
.issue-top .col {
  flex: none;
  color: var(--text-secondary);
}
.issue-top .raw {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.conf {
  font-size: 12px;
  color: var(--text-secondary);
}
.issue-body {
  font: var(--text-xs);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.confirm-block {
  padding-top: var(--space-3);
  border-top: 1px solid var(--border-subtle);
}

.sel-head {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font: var(--text-sm);
}
.sel-col {
  color: var(--text-secondary);
}
.sel-arrow {
  color: var(--text-tertiary);
}
.sel-target {
  color: var(--text-primary);
}

.sel-meta {
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
.meta-row {
  display: grid;
  grid-template-columns: 68px 1fr;
  gap: var(--space-2);
  align-items: baseline;
}
.meta-row--stack {
  grid-template-columns: 1fr;
}
.meta-row dt {
  font: var(--text-xs);
  color: var(--text-tertiary);
}
.meta-row dd {
  margin: 0;
  font-size: 12px;
  color: var(--text-primary);
  word-break: break-word;
}

.review-done {
  font: var(--text-xs);
  color: var(--success);
}

.actions {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  margin-top: var(--space-1);
}
.act {
  width: 100%;
}
.remap {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}
.remap-label {
  color: var(--text-tertiary);
}
.remap-select {
  height: 34px;
  background: var(--bg-primary);
}

.foot {
  flex: none;
  padding: var(--space-3) var(--space-4);
  border-top: 1px solid var(--border-subtle);
  background: var(--glass-bg-strong);
  backdrop-filter: blur(var(--glass-blur));
  -webkit-backdrop-filter: blur(var(--glass-blur));
}
.block-btn {
  width: 100%;
}
.foot-hint {
  font: var(--text-xs);
  margin-top: var(--space-2);
  line-height: 1.4;
}

@media (max-width: 1024px) {
  .map-inspector {
    border-left: none;
  }
}
</style>