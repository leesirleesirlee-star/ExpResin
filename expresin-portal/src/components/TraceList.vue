<script setup>
/**
 * 溯源键值列表（升级方案 §7.1）。
 *
 * 统一 MappingInspector `.sel-meta` 与 MetadataInspector `.trace` 两套
 * 定义列表：同一列宽、同一断行策略，长证据文本可自然换行而不撑破面板。
 */
defineProps({
  /** 列表顶部的字段名/标题，可空 */
  title: { type: String, default: '' },
  /** [{ k, v }]，v 可为长文本 */
  rows: { type: Array, required: true },
})
</script>

<template>
  <dl class="trace">
    <div v-if="title" class="trace-head">{{ title }}</div>
    <div v-for="row in rows" :key="row.k" class="trace-row">
      <dt>{{ row.k }}</dt>
      <dd class="mono">{{ row.v }}</dd>
    </div>
  </dl>
</template>

<style scoped>
.trace {
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
.trace-head {
  font: var(--text-sm);
  color: var(--text-primary);
  padding-bottom: var(--space-1);
  border-bottom: 1px solid var(--border-subtle);
}
.trace-row {
  display: grid;
  grid-template-columns: 68px minmax(0, 1fr);
  gap: var(--space-2);
  align-items: baseline;
}
.trace-row dt {
  font: var(--text-xs);
  color: var(--text-tertiary);
}
.trace-row dd {
  margin: 0;
  font-size: 12px;
  color: var(--text-primary);
  word-break: break-word;
}
</style>
