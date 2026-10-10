<script setup>
/**
 * 统计数字网格（升级方案 §7.1）。
 *
 * 统一 MappingInspector 的问题计数与 MetadataInspector 的来源分布，
 * 数值一律 tabular-nums，保证多位数对齐、状态可扫读。
 */
defineProps({
  /** [{ key, label, value }] */
  items: { type: Array, required: true },
  /** 列数，默认 3；来源分布用 2 */
  columns: { type: Number, default: 3 },
})
</script>

<template>
  <div class="stat-grid" :style="{ '--stat-cols': columns }">
    <div v-for="s in items" :key="s.key" class="stat">
      <span class="stat-num">{{ s.value }}</span>
      <span class="stat-label">{{ s.label }}</span>
    </div>
  </div>
</template>

<style scoped>
.stat-grid {
  display: grid;
  grid-template-columns: repeat(var(--stat-cols, 3), minmax(0, 1fr));
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
  font-variant-numeric: tabular-nums;
  color: var(--text-primary);
}
.stat-label {
  font: var(--text-xs);
  color: var(--text-secondary);
}
</style>
