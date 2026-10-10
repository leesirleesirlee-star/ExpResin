<script setup>
/**
 * 溯源轨（Signature / 升级方案 §2、§7.1）。
 *
 * 本产品的唯一性元素：2px 竖向导轨 + 顶部置信度芯片，表达
 * 「机器识别 → 人工确认 → 科学证据」的链条。颜色 + 文本双重编码：
 * 低于阈值用 warning，达标用 success，缺值用中性，绝不只靠颜色区分。
 */
import { computed } from 'vue'

const props = defineProps({
  /** 置信度数值；null/undefined 表示无置信度信息 */
  confidence: { type: Number, default: null },
  /** 原始证据文本，作为 title 与可选展开内容 */
  evidence: { type: String, default: '' },
  /** 置信度阈值，默认 0.8（规范） */
  threshold: { type: Number, default: 0.8 },
})

const hasConf = computed(() => typeof props.confidence === 'number' && !Number.isNaN(props.confidence))
const ok = computed(() => hasConf.value && props.confidence >= props.threshold)
const tone = computed(() => (hasConf.value ? (ok.value ? 'ok' : 'low') : 'none'))
const chipText = computed(() => (hasConf.value ? props.confidence.toFixed(2) : '—'))
</script>

<template>
  <span class="rail" :class="`rail--${tone}`" :title="evidence || undefined">
    <span class="rail-line" aria-hidden="true"></span>
    <span class="rail-chip mono">{{ chipText }}</span>
    <span class="visually-hidden">
      {{ hasConf ? (ok ? '置信度达标' : '置信度低于阈值') : '无置信度信息' }}
    </span>
  </span>
</template>

<style scoped>
.rail {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  flex: none;
}
.rail-line {
  width: 2px;
  height: 16px;
  border-radius: var(--radius-full);
  background: var(--border-strong);
}
.rail--ok .rail-line {
  background: var(--success);
}
.rail--low .rail-line {
  background: var(--warning);
}
.rail-chip {
  font-size: 11px;
  font-variant-numeric: tabular-nums;
  color: var(--text-secondary);
}
.rail--ok .rail-chip {
  color: var(--success);
}
.rail--low .rail-chip {
  color: var(--warning);
}
.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  opacity: 0;
  pointer-events: none;
}
</style>
