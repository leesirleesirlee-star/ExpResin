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
import PanelHead from './PanelHead.vue'
import StatGrid from './StatGrid.vue'
import IssueList from './IssueList.vue'
import TraceList from './TraceList.vue'

const props = defineProps({
  issues: { type: Object, default: () => ({}) },
  regions: { type: Array, default: () => [] },
  selected: { type: Object, default: null },
  /** { kind: [{ key, label, unit }] } 来自标准 Schema，保证改判目标一定合法 */
  schemaColumns: { type: Object, default: () => ({}) },
  /** [{ key, label }] 列块级离子判定的候选离子 */
  analyteOptions: { type: Array, default: () => [] },
  /** 人工判定提交中：禁用操作，避免重复提交 */
  resolving: { type: Boolean, default: false },
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

/** 选中列的溯源键值行，交给共享 TraceList 渲染。 */
const selectedMeta = computed(() => {
  const s = props.selected
  if (!s) return []
  const rows = []
  if (!isBlockFailed.value) rows.push({ k: '原始表头', v: s.raw || '（空）' })
  rows.push({ k: '所属列块', v: s.block })
  if (isAnalyteRow.value) rows.push({ k: '标签列证据', v: s.expected || '—' })
  rows.push({ k: '置信度', v: typeof s.conf === 'number' ? s.conf.toFixed(2) : '—' })
  rows.push({ k: '判定证据', v: s.evidence || '—' })
  return rows
})

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
    <PanelHead label="映射确认">
      <template #actions>
        <span class="badge" :class="total ? 'badge-warning' : 'badge-success'">
          {{ total ? `${total} 项待处理` : '全部通过' }}
        </span>
      </template>
    </PanelHead>

    <div class="body">
      <!-- 概览 -->
      <StatGrid :items="stats" :columns="3" />

      <!-- 问题分组 -->
      <IssueList :groups="groups" :selected="selected" @select="$emit('select', $event)" />

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

          <TraceList :rows="selectedMeta" />

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
              :disabled="!currentValue || resolving"
              @click="resolve('confirm')"
            >
              {{ resolving ? '提交中…' : isAnalyteRow ? '确认离子判定' : '确认此映射' }}
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
                :disabled="!targetDraft || targetDraft === currentValue || resolving"
                @click="resolve('remap', targetDraft)"
              >
                应用改判
              </button>
            </div>

            <button
              v-if="!isAnalyteRow"
              class="btn btn-ghost act"
              type="button"
              :disabled="resolving"
              @click="resolve('ignore')"
            >
              标记为非数据列
            </button>
          </div>
        </template>
      </section>
    </div>

    <div class="foot">
      <button
        class="btn btn-primary block-btn"
        type="button"
        :disabled="resolving"
        @click="$emit('confirm')"
      >
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
  /* 透明，让父级 .pane--inspector 的磨砂玻璃透出；竖直分割线由布局层提供 */
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
.empty {
  font: var(--text-sm);
}
.tiny {
  font: var(--text-xs);
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
  min-height: 40px;
  background: var(--bg-primary);
}

.foot {
  flex: none;
  padding: var(--space-3) var(--space-4);
  border-top: 1px solid var(--border-subtle);
  background: var(--glass-bg-strong);
  backdrop-filter: blur(var(--glass-blur)) saturate(var(--glass-saturate));
  -webkit-backdrop-filter: blur(var(--glass-blur)) saturate(var(--glass-saturate));
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