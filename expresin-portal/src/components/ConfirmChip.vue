<script setup>
/**
 * 字段/草稿状态芯片（升级方案 §7.1、§7.3）。
 *
 * 状态到「文案 + 色调」的唯一映射已经集中在 src/domain/fieldStatus.js；
 * 本组件只负责把映射结果渲染成统一的徽章，避免各面板各写一份 :class。
 * 同一字段在全站任意面板都会得到相同标签与颜色（PRD 宪法 #8）。
 */
import { computed } from 'vue'
import { fieldStateMeta, draftStateMeta } from '../domain/fieldStatus.js'

const props = defineProps({
  /** 状态键，如 confirmed / pending / low-confidence / unit-error / missing */
  state: { type: String, default: '' },
  /** 判定域：列识别域 field，或录入草稿域 draft */
  domain: { type: String, default: 'field' },
})

const meta = computed(() =>
  props.domain === 'draft' ? draftStateMeta(props.state) : fieldStateMeta(props.state),
)
</script>

<template>
  <span v-if="meta.label" class="badge" :class="`badge-${meta.tone}`">{{ meta.label }}</span>
</template>
