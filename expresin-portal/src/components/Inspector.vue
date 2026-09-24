<script setup>
import { computed } from 'vue'

const props = defineProps({
  issues: { type: Object, required: true },
  selected: { type: Object, default: null },
})

defineEmits(['select', 'confirm'])

const stats = computed(() => [
  { key: 'pending', label: '待确认', value: (props.issues.pending ?? []).length },
  { key: 'lowConfidence', label: '低置信度', value: (props.issues.lowConfidence ?? []).length },
  { key: 'missing', label: '缺失', value: (props.issues.missing ?? []).length },
  { key: 'unitErrors', label: '单位异常', value: (props.issues.unitErrors ?? []).length },
  {
    key: 'analyteConflicts',
    label: '离子存疑',
    value: (props.issues.analyteConflicts ?? []).length,
  },
])

const total = computed(() => stats.value.reduce((n, s) => n + s.value, 0))

const groups = computed(() => [
  { key: 'pending', label: '待确认映射', tone: 'warning', items: props.issues.pending },
  { key: 'lowConfidence', label: '低置信度', tone: 'warning', items: props.issues.lowConfidence },
  { key: 'missing', label: '缺失 / 幽灵列', tone: 'warning', items: props.issues.missing },
  { key: 'unitErrors', label: '单位冲突', tone: 'error', items: props.issues.unitErrors },
  {
    key: 'analyteConflicts',
    label: '离子判定存疑',
    tone: 'error',
    items: props.issues.analyteConflicts ?? [],
  },
])
</script>

<template>
  <aside class="inspector" aria-label="校验与溯源面板">
    <div class="panel-head">
      <span class="caps">Inspector</span>
      <span class="badge" :class="total ? 'badge-warning' : 'badge-success'">
        {{ total ? `${total} 项待处理` : '全部通过' }}
      </span>
    </div>

    <div class="body">
      <section class="stats">
        <div v-for="s in stats" :key="s.key" class="stat">
          <span class="stat-num">{{ s.value }}</span>
          <span class="stat-label">{{ s.label }}</span>
        </div>
      </section>

      <section v-for="g in groups" :key="g.key" class="group">
        <h3 class="caps group-title">{{ g.label }}</h3>

        <p v-if="!g.items.length" class="empty muted">无</p>

        <ul v-else class="list">
          <li v-for="item in g.items" :key="`${item.block}/${item.col}`">
            <button
              class="issue"
              type="button"
              :class="`field--${item.state}`"
              @click="$emit('select', item)"
            >
              <span class="issue-top">
                <span class="mono">{{ item.col }}</span>
                <span class="raw mono">{{ item.raw || '（空表头）' }}</span>
                <span class="conf mono">{{ item.conf.toFixed(2) }}</span>
              </span>
              <span class="issue-body muted">{{ item.evidence }}</span>
            </button>
          </li>
        </ul>
      </section>

      <section class="group">
        <h3 class="caps group-title">字段溯源</h3>

        <div v-if="!selected" class="empty muted">
          在中间表单中点击任意字段，查看其判定证据。
        </div>

        <dl v-else class="trace">
          <div class="trace-row">
            <dt>原始表头</dt>
            <dd class="mono">{{ selected.raw || '（空）' }}</dd>
          </div>
          <div class="trace-row">
            <dt>标准字段</dt>
            <dd>{{ selected.field || '未映射' }}</dd>
          </div>
          <div class="trace-row">
            <dt>目标路径</dt>
            <dd class="mono">{{ selected.target || '—' }}</dd>
          </div>
          <div class="trace-row">
            <dt>置信度</dt>
            <dd class="mono">{{ selected.conf.toFixed(2) }}</dd>
          </div>
          <div class="trace-row">
            <dt>所属块</dt>
            <dd class="mono">{{ selected.block }}</dd>
          </div>
          <div class="trace-row trace-row--stack">
            <dt>判定证据</dt>
            <dd>{{ selected.evidence }}</dd>
          </div>
        </dl>
      </section>
    </div>

    <div class="foot">
      <button class="btn btn-primary block-btn" type="button" @click="$emit('confirm')">
        确认并写入 Processed
      </button>
    </div>
  </aside>
</template>

<style scoped>
.inspector {
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
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-2);
}
.stat {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  padding: var(--space-3);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  background: var(--bg-primary);
}
.stat-num {
  font: var(--text-lg);
  font-family: var(--font-mono);
  color: var(--text-primary);
}
.stat-label {
  font: var(--text-xs);
  color: var(--text-secondary);
}

.group-title {
  margin-bottom: var(--space-2);
}
.empty {
  font: var(--text-sm);
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
.issue:hover {
  background: var(--bg-tertiary);
}
.issue-top {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font: var(--text-sm);
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

.trace {
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
.trace-row {
  display: grid;
  grid-template-columns: 76px 1fr;
  gap: var(--space-2);
  align-items: baseline;
}
.trace-row--stack {
  grid-template-columns: 1fr;
}
.trace-row dt {
  font: var(--text-xs);
  color: var(--text-tertiary);
}
.trace-row dd {
  margin: 0;
  font: var(--text-sm);
  color: var(--text-primary);
  word-break: break-word;
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

@media (max-width: 1024px) {
  .inspector {
    border-left: none;
  }
}
</style>