<script setup>
import { computed } from 'vue'
import { STATUS_META } from '../data/demo.js'

const props = defineProps({
  experiment: { type: Object, required: true },
  confirmLabel: { type: String, default: '确认数据' },
  saveLabel: { type: String, default: '保存' },
  showSave: { type: Boolean, default: true },
  /** 归档/确认进行中：禁用按钮并给出进行中文案，避免重复提交与“点了没反应” */
  saving: { type: Boolean, default: false },
  savingLabel: { type: String, default: '处理中…' },
})

defineEmits(['save', 'confirm'])

const meta = computed(() => STATUS_META[props.experiment.status] ?? STATUS_META.draft)
</script>

<template>
  <footer class="statusbar">
    <div class="left">
      <span class="id mono">{{ experiment.id }}</span>
      <span class="badge" :class="`badge-${meta.tone}`">
        <span class="dot" aria-hidden="true"></span>
        {{ meta.label }}
      </span>
    </div>

    <div class="center muted">
      最后保存：{{ experiment.lastSaved }}
    </div>

    <div class="right">
      <button
        v-if="showSave"
        class="btn btn-secondary"
        type="button"
        :disabled="saving"
        @click="$emit('save')"
      >
        {{ saveLabel }}
      </button>
      <button
        class="btn btn-primary"
        type="button"
        :disabled="saving"
        :aria-busy="saving"
        @click="$emit('confirm')"
      >
        <span v-if="saving" class="spinner" aria-hidden="true"></span>
        {{ saving ? savingLabel : confirmLabel }}
      </button>
    </div>
  </footer>
</template>

<style scoped>
.statusbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  height: var(--statusbar-h);
  padding: 0 var(--space-4);
  background: var(--bg-secondary);
  border-top: 1px solid var(--border-subtle);
  z-index: var(--z-sticky);
}

.left,
.right {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.id {
  font-size: 14px;
  color: var(--text-primary);
}

.dot {
  width: 6px;
  height: 6px;
  border-radius: var(--radius-full);
  background: currentColor;
}

.spinner {
  width: 14px;
  height: 14px;
  margin-right: var(--space-2);
  border: 2px solid currentColor;
  border-top-color: transparent;
  border-radius: var(--radius-full);
  animation: spin 0.7s linear infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 480px) {
  .statusbar {
    height: var(--statusbar-h-mobile);
  }
  .center {
    display: none;
  }
}
</style>