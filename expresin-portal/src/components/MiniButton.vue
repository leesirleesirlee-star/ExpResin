<script setup>
/**
 * 紧凑操作按钮（升级方案 §7.1、打磨层触控目标）。
 *
 * 取代 MetadataInspector 的 `.mini`：此前 padding 仅 2px/8px，触控目标远低于
 * 规范要求。这里把高度抬到 40px（最低触控标准），同时保持紧凑的视觉密度。
 */
defineProps({
  /** default | ghost */
  variant: { type: String, default: 'default' },
  type: { type: String, default: 'button' },
})
</script>

<template>
  <button class="mini" :class="`mini--${variant}`" :type="type">
    <slot />
  </button>
</template>

<style scoped>
.mini {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 40px;
  padding: 0 var(--space-3);
  font: var(--text-xs);
  font-weight: 500;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  background: var(--bg-secondary);
  color: var(--text-primary);
  cursor: pointer;
  transition: background var(--duration-fast) var(--ease-standard),
    border-color var(--duration-fast) var(--ease-standard);
}
.mini:hover {
  background: var(--bg-tertiary);
  border-color: var(--border-strong);
}
.mini--ghost {
  background: transparent;
  color: var(--text-secondary);
}
</style>
