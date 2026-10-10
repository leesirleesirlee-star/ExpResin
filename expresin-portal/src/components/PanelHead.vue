<script setup>
/**
 * 统一面板头（规范 §4.x / 升级方案 §7.1）。
 *
 * 取代此前散落在 ChatPanel / DynamicForm / MappingInspector / MetadataInspector
 * 的 5 处 `.panel-head` 复制：统一 48px 高度（--panel-head-h）、caps 标题与
 * 右侧动作/计数区，避免各面板高度与内距漂移。
 */
defineProps({
  /** 左侧 caps 标题文案 */
  label: { type: String, required: true },
  /** 语义标签名，面板头本身不是标题层级，默认 span */
  as: { type: String, default: 'span' },
})
</script>

<template>
  <div class="panel-head">
    <component :is="as" class="caps">{{ label }}</component>
    <div v-if="$slots.actions" class="panel-head-actions">
      <slot name="actions" />
    </div>
  </div>
</template>

<style scoped>
.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  height: var(--panel-head-h);
  padding: 0 var(--space-4);
  border-bottom: 1px solid var(--border-subtle);
  flex: none;
}
.panel-head-actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  min-width: 0;
}
</style>
