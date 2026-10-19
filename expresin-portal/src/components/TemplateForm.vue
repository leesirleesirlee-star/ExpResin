<script setup>
/**
 * 模板字段表单（PRD 8.3 中栏）。
 * 按模板 Sheet 分组渲染，支持：
 *  - 必填校验与状态标记（缺失/待确认/低置信度/单位异常/稍后补）
 *  - value_labels：如树脂型号显示为「树脂 A600」，避免裸型号歧义
 *  - 字段来源提示（对话抽取 / 手动输入）
 */
import { computed, watch } from 'vue'
import { draftStatusOf } from '../domain/fieldStatus.js'
import ConfirmChip from './ConfirmChip.vue'

const props = defineProps({
  sheets: { type: Array, required: true },
  drafts: { type: Object, default: () => ({}) },
  disabled: { type: Boolean, default: false },
  /** 由右侧录入检查面板触发：把对应字段滚动到视野中央并聚焦 */
  focusPath: { type: String, default: '' },
})

const emit = defineEmits(['change', 'defer', 'focus-field'])

/**
 * 当前实验类型：用于 show_for 条件字段过滤。
 * 未选择类型时不做过滤（避免字段"神秘消失"，用户仍能看到全部候选项）。
 */
const currentType = computed(() => {
  const value = props.drafts['01_Metadata.experiment_type']?.value
  return String(value ?? '').trim()
})

/** 按 show_for 过滤字段：已选类型后，只显示声明包含该类型的字段与通用字段。 */
function visibleFields(sheet) {
  const list = sheet.fields ?? []
  if (!currentType.value) return list
  return list.filter((field) => !field.show_for?.length || field.show_for.includes(currentType.value))
}

// 录入页右侧点「定位」时，把字段滚到视野中央并聚焦，避免用户在上百字段里翻找
watch(
  () => props.focusPath,
  (path) => {
    if (!path) return
    const input = document.getElementById(path)
    if (!input) return
    input.closest('.frow')?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    if (typeof input.focus === 'function') input.focus({ preventScroll: true })
  },
)

function draftOf(field) {
  return props.drafts[field.path] || {}
}

function valueOf(field) {
  return draftOf(field).value ?? ''
}

function unitOf(field) {
  return draftOf(field).unit || field.unit || ''
}

/** 录入字段状态判定与文案/色调统一来自 domain/fieldStatus.js。 */
function statusOf(field) {
  return draftStatusOf(field, draftOf(field))
}

/** 带前缀的展示名：树脂型号 -> 树脂 A600 */
function displayLabel(field) {
  const value = String(valueOf(field)).trim()
  if (!value) return ''
  return field.value_labels?.[value.toLowerCase()] ?? field.value_labels?.[value] ?? ''
}

function optionLabel(field, option) {
  return field.option_labels?.[option] ?? field.value_labels?.[option] ?? option
}

/**
 * 未进入 option_groups 分组的选项：保持 options 原顺序渲染在分组之前。
 * 用于实验类型的「电化学实验」子栏（optgroup），其余类型平铺在前。
 */
function ungroupedOptions(field) {
  const grouped = new Set((field.option_groups || []).flatMap((g) => g.options || []))
  return (field.options || []).filter((o) => !grouped.has(o))
}

function emitChange(field, value) {
  emit('change', { field_path: field.path, value })
}
</script>

<template>
  <div class="tform">
    <section v-for="sheet in sheets" :key="sheet.id" class="sheet">
      <header class="sheet-head">
        <h2>{{ sheet.label }}</h2>
        <span class="badge badge-neutral mono">{{ sheet.id }}</span>
      </header>

      <div class="fields">
        <div
          v-for="field in visibleFields(sheet)"
          :key="field.path"
          class="frow field"
          :class="[
            `field--${statusOf(field)}`,
            {
              'is-disabled': disabled || field.type === 'derived' || field.type === 'file',
              'is-focused': focusPath === field.path,
            },
          ]"
          @click="emit('focus-field', field)"
        >
          <div class="flabel">
            <label :for="field.path">
              {{ field.label }}
              <span v-if="field.required" class="req" aria-hidden="true">*</span>
            </label>
            <span v-if="field.hint" class="fhint muted">{{ field.hint }}</span>
          </div>

          <div class="fcontrol">
            <select
              v-if="field.type === 'enum'"
              :id="field.path"
              class="input"
              :value="valueOf(field)"
              :disabled="disabled"
              @change="emitChange(field, $event.target.value)"
            >
              <option value="">请选择</option>
              <template v-if="field.option_groups?.length">
                <option v-for="o in ungroupedOptions(field)" :key="o" :value="o">
                  {{ optionLabel(field, o) }}
                </option>
                <optgroup v-for="g in field.option_groups" :key="g.label" :label="g.label">
                  <option v-for="o in g.options" :key="o" :value="o">
                    {{ optionLabel(field, o) }}
                  </option>
                </optgroup>
              </template>
              <template v-else>
                <option v-for="o in field.options || []" :key="o" :value="o">
                  {{ optionLabel(field, o) }}
                </option>
              </template>
            </select>

            <textarea
              v-else-if="field.type === 'text'"
              :id="field.path"
              class="input textarea"
              :value="valueOf(field)"
              :placeholder="field.placeholder || ''"
              :disabled="disabled"
              @input="emitChange(field, $event.target.value)"
            />

            <input
              v-else
              :id="field.path"
              class="input"
              :type="field.type === 'number' ? 'text' : field.type === 'date' ? 'date' : 'text'"
              :inputmode="field.type === 'number' ? 'decimal' : undefined"
              :value="valueOf(field)"
              :placeholder="field.placeholder || ''"
              :disabled="disabled || field.type === 'derived'"
              @input="emitChange(field, $event.target.value)"
            />

            <span v-if="unitOf(field)" class="unit mono">{{ unitOf(field) }}</span>
          </div>

          <div class="fmeta">
            <span v-if="displayLabel(field)" class="badge badge-accent">{{ displayLabel(field) }}</span>
            <ConfirmChip domain="draft" :state="statusOf(field)" />
            <span v-if="draftOf(field).source_type === 'conversation'" class="badge badge-neutral">
              来自对话
            </span>
            <span v-else-if="draftOf(field).source_type === 'upload'" class="badge badge-neutral">
              来自上传
            </span>
            <button
              v-if="field.required && !String(valueOf(field)).trim()"
              class="defer"
              type="button"
              @click.stop="emit('defer', field)"
            >
              稍后补
            </button>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.tform {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}

.sheet-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding-bottom: var(--space-2);
  border-bottom: 1px solid var(--border-subtle);
  margin-bottom: var(--space-2);
}
.sheet-head h2 {
  font: var(--text-lg);
}

.fields {
  display: flex;
  flex-direction: column;
}

.frow {
  display: grid;
  grid-template-columns: minmax(140px, 1.1fr) minmax(160px, 1.4fr) minmax(120px, 1fr);
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-3);
  border-bottom: 1px solid var(--border-subtle);
}
.frow:last-child {
  border-bottom: none;
}
.frow:hover {
  background: var(--bg-tertiary);
}
.frow.is-disabled {
  opacity: 0.68;
}
.frow.is-disabled .flabel label {
  color: var(--text-secondary);
}
.frow.is-focused {
  background: var(--bg-tertiary);
  box-shadow: inset 2px 0 0 var(--accent);
}

.flabel {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}
.flabel label {
  font: var(--text-sm);
  color: var(--text-primary);
}
.req {
  color: var(--error);
  margin-left: 2px;
}
.fhint {
  font: var(--text-xs);
  line-height: 1.35;
}

.fcontrol {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  min-width: 0;
}
.fcontrol .input {
  height: 40px;
  background: var(--bg-primary);
}
.textarea {
  height: auto;
  min-height: 64px;
  padding: var(--space-2) var(--space-3);
  resize: vertical;
  line-height: 1.5;
}
.unit {
  flex: none;
  font-size: 12px;
  color: var(--text-secondary);
}

.fmeta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
}
.defer {
  border: none;
  background: transparent;
  font: var(--text-xs);
  color: var(--text-tertiary);
  text-decoration: underline;
  cursor: pointer;
  padding: 0;
}
.defer:hover {
  color: var(--accent);
}

@media (max-width: 1280px) {
  .frow {
    grid-template-columns: minmax(120px, 1fr) minmax(140px, 1.3fr);
  }
  .fmeta {
    grid-column: 1 / -1;
    justify-content: flex-end;
  }
}
</style>