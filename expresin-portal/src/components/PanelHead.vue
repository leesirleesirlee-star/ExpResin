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
  /** 标题前显示一枚琥珀橙光点（用于 Jarvis 等「有温度的 AI」面板） */
  dot: { type: Boolean, default: false },
})
</script>

<template>
  <div class="panel-head">
    <component :is="as" class="caps panel-title">
      <span v-if="dot" class="panel-dot" aria-hidden="true"></span>
      {{ label }}
    </component>
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
.panel-title {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
}
/* 橙色光点：强化「有温度的 AI 助手」而非冷系统模块 */
.panel-dot {
  width: 7px;
  height: 7px;
  border-radius: var(--radius-full);
  background: var(--chat-dot);
  box-shadow: 0 0 0 3px var(--accent-bg);
}
.panel-head-actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  min-width: 0;
}
</style>
