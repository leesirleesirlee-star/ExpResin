<script setup>
/**
 * 问题分组列表（升级方案 §7.1）。
 *
 * 取代 MappingInspector 内的问题分组：统一分组标题、左色条、选中态与截断，
 * 让「哪些列需要人工处置」在一屏内可扫读。
 */
defineProps({
  /** [{ key, label, tone, items: [{ block, col, raw, conf, evidence }] }] */
  groups: { type: Array, required: true },
  /** 当前选中项 { block, col } */
  selected: { type: Object, default: null },
})

defineEmits(['select'])
</script>

<template>
  <div class="issue-groups">
    <section v-for="g in groups" :key="g.key" class="group">
      <h3 class="caps group-title">
        {{ g.label }}
        <span class="group-count">{{ g.items.length }}</span>
      </h3>
      <ul class="list">
        <li v-for="item in g.items" :key="`${g.key}-${item.block}/${item.col}`">
          <button
            class="issue"
            type="button"
            :class="[
              `issue--${g.tone}`,
              { 'is-active': selected && selected.block === item.block && selected.col === item.col },
            ]"
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
  </div>
</template>

<style scoped>
.issue-groups {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}
.group {
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
  letter-spacing: 0;
  text-transform: none;
  color: var(--text-secondary);
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
  font-variant-numeric: tabular-nums;
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
</style>
