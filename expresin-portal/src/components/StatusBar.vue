<script setup>
import { computed } from 'vue'
import { STATUS_META } from '../data/demo.js'

const props = defineProps({
  experiment: { type: Object, required: true },
  confirmLabel: { type: String, default: '确认数据' },
  saveLabel: { type: String, default: '保存' },
  showSave: { type: Boolean, default: true },
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
        @click="$emit('save')"
      >
        {{ saveLabel }}
      </button>
      <button class="btn btn-primary" type="button" @click="$emit('confirm')">
        {{ confirmLabel }}
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
  z-index: 20;
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

@media (max-width: 640px) {
  .statusbar {
    height: 44px;
  }
  .center {
    display: none;
  }
}
</style>