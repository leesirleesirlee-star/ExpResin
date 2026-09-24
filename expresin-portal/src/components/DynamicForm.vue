<script setup>
import { fieldState } from '../data/demo.js'

defineProps({
  regions: { type: Array, required: true },
  selected: { type: Object, default: null },
})

const emit = defineEmits(['select'])

/**
 * 列填充证据：后端在识别骨架里透传 nonNull / fillRatio。
 * 识别阶段不持有数据值（column.value 恒为空），因此此处展示"该列有多少非空值"，
 * 而不是一个恒空、且输入不会被保存的「值」输入框（见缺陷 C）。
 */
function fillText(col) {
  const n = col.nonNull
  if (n === undefined || n === null) return '—'
  const ratio = col.fillRatio
  return ratio === undefined || ratio === null ? `${n}` : `${n} · ${Math.round(ratio * 100)}%`
}

function toneOf(col) {
  const state = fieldState(col)
  if (state === 'label') return 'neutral'
  if (state === 'confirmed') return 'success'
  if (state === 'unit-error') return 'error'
  return 'warning'
}

function stateLabel(state) {
  return (
    {
      confirmed: '已确认',
      pending: '待确认',
      'low-confidence': '低置信度',
      'unit-error': '单位异常',
      missing: '缺失',
      label: '标签列',
    }[state] ?? state
  )
}
</script>

<template>
  <section class="panel form" aria-label="结构化表单">
    <div class="panel-head">
      <span class="caps">Dynamic Form</span>
      <span class="muted count">
        {{ regions.reduce((n, r) => n + r.blocks.length, 0) }} 个列块 ·
        {{ regions.reduce((n, r) => n + r.blocks.reduce((m, b) => m + b.columns.length, 0), 0) }} 列
      </span>
    </div>

    <div class="body">
      <article v-for="region in regions" :key="region.id" class="region">
        <header class="region-head">
          <div class="region-title">
            <h2>{{ region.kindLabel }}</h2>
            <p class="muted mono">{{ region.title || '（无区块标题）' }}</p>
          </div>
          <span class="badge badge-neutral">{{ region.id.split('#')[1] || region.id }}</span>
        </header>

        <div v-for="block in region.blocks" :key="block.id" class="block">
          <div class="block-head">
            <span class="block-id mono">{{ block.id }}</span>
            <div class="block-meta">
              <span v-if="block.analyte" class="badge badge-accent">目标离子 {{ block.analyte }}</span>
              <span class="badge" :class="block.confidence < 0.8 ? 'badge-warning' : 'badge-success'">
                块置信度 {{ (block.confidence * 100).toFixed(0) }}%
              </span>
            </div>
          </div>

          <div class="grid">
            <div class="row row--head" aria-hidden="true">
              <span>列</span>
              <span>原始表头</span>
              <span />
              <span>标准字段</span>
              <span>填充</span>
              <span>置信度</span>
              <span>状态</span>
            </div>

            <div
              v-for="col in block.columns"
              :key="col.col"
              class="row field"
              :class="[
                `field--${fieldState(col)}`,
                { 'is-selected': selected && selected.block === block.id && selected.col === col.col },
              ]"
              role="button"
              tabindex="0"
              @click="emit('select', { ...col, block: block.id, region: region.title, analyte: block.analyte })"
              @keydown.enter="emit('select', { ...col, block: block.id, region: region.title, analyte: block.analyte })"
            >
              <span class="cell col mono">{{ col.col }}</span>
              <span class="cell raw mono" :title="col.raw">{{ col.raw || '（空）' }}</span>
              <span class="cell arrow" aria-hidden="true">→</span>
              <span class="cell target">{{ col.field || '未映射' }}</span>
              <span class="cell fill mono">{{ fillText(col) }}</span>
              <span class="cell conf mono">{{ col.conf.toFixed(2) }}</span>
              <span class="cell">
                <span class="badge" :class="`badge-${toneOf(col)}`">
                  {{ stateLabel(fieldState(col)) }}
                </span>
              </span>
            </div>
          </div>
        </div>
      </article>
    </div>
  </section>
</template>

<style scoped>
.form {
  display: flex;
  flex-direction: column;
  min-height: 0;
  min-width: 0;
  background: var(--bg-primary);
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
.count {
  font: var(--text-xs);
}

.body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: var(--space-5) var(--space-5) var(--space-7);
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}

.region-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-3);
  margin-bottom: var(--space-3);
}
.region-title h2 {
  font: var(--text-lg);
  color: var(--text-primary);
}
.region-title p {
  margin-top: var(--space-1);
  font: var(--text-xs);
  font-family: var(--font-mono);
}

.block {
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  background: var(--bg-secondary);
  box-shadow: var(--shadow-sm);
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
.block-id {
  font-size: 12px;
  color: var(--text-secondary);
}
.block-meta {
  display: flex;
  gap: var(--space-2);
}

.grid {
  display: flex;
  flex-direction: column;
}

.row {
  display: grid;
  grid-template-columns: 32px minmax(96px, 1.2fr) 20px minmax(96px, 1fr) 64px 92px;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-4);
}
.row--head {
  font: var(--text-xs);
  font-weight: 500;
  letter-spacing: var(--tracking-caps);
  text-transform: uppercase;
  color: var(--text-tertiary);
  border-bottom: 1px solid var(--border-subtle);
  padding-top: var(--space-3);
  padding-bottom: var(--space-2);
}

.row:not(.row--head) {
  cursor: pointer;
  border-bottom: 1px solid var(--border-subtle);
}
.row:not(.row--head):last-child {
  border-bottom: none;
}
.row:not(.row--head):hover {
  background: var(--bg-tertiary);
}
.row.is-selected {
  box-shadow: inset 2px 0 0 var(--accent);
}

.cell {
  min-width: 0;
  font: var(--text-sm);
}
.col {
  color: var(--text-tertiary);
}
.raw {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--text-primary);
}
.arrow {
  color: var(--text-tertiary);
  text-align: center;
}
.target {
  color: var(--text-secondary);
}
.conf {
  font-size: 12px;
  color: var(--text-secondary);
}
.fill {
  font-size: 12px;
  color: var(--text-secondary);
}

@media (max-width: 1280px) {
  .row {
    grid-template-columns: 28px minmax(80px, 1fr) 16px minmax(80px, 1fr) 52px 80px;
    gap: var(--space-2);
  }
}
</style>