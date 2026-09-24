<script setup>
/**
 * 实验元数据录入页专用右边栏。
 *
 * 与识别页的 MappingInspector 刻意分开：录入阶段根本不存在「列映射」这件事，
 * 因此这里不显示待确认/低置信度列，而是回答录入阶段真正要回答的三个问题：
 *   1. 还差什么才能归档？（阻塞项 + 一键定位 / 稍后补）
 *   2. 哪些已填的值值得核对？（低置信度、单位异常）
 *   3. 这个值从哪来？（对话抽取 / 手动 / 模板默认 + 原始表达）
 */
import { computed } from 'vue'

const props = defineProps({
  sheets: { type: Array, default: () => [] },
  drafts: { type: Object, default: () => ({}) },
  missing: { type: Array, default: () => [] },
  deferred: { type: Array, default: () => [] },
  selected: { type: Object, default: null },
})

defineEmits(['focus', 'defer', 'select', 'confirm'])

const draftOf = (path) => props.drafts[path] || {}

/** 必填字段完成度。 */
const required = computed(() => {
  const out = []
  for (const sheet of props.sheets) {
    for (const f of sheet.fields ?? []) {
      if (f.required) out.push(f)
    }
  }
  return out
})

const filledRequired = computed(
  () => required.value.filter((f) => String(draftOf(f.path).value ?? '').trim()).length,
)

const progress = computed(() => {
  const total = required.value.length
  return total ? Math.round((filledRequired.value / total) * 100) : 100
})

const optionalFilled = computed(() => {
  let n = 0
  for (const sheet of props.sheets) {
    for (const f of sheet.fields ?? []) {
      if (!f.required && String(draftOf(f.path).value ?? '').trim()) n += 1
    }
  }
  return n
})

/** 已填但值得核对的字段：置信度偏低或单位异常。 */
const attention = computed(() => {
  const out = []
  for (const sheet of props.sheets) {
    for (const f of sheet.fields ?? []) {
      const d = draftOf(f.path)
      const value = String(d.value ?? '').trim()
      if (!value) continue
      const low = d.status === 'low_confidence' || (typeof d.confidence === 'number' && d.confidence < 0.8)
      if (low || d.status === 'unit_error') {
        out.push({
          path: f.path,
          label: f.label,
          value,
          unit: d.unit || f.unit || '',
          conf: typeof d.confidence === 'number' ? d.confidence : null,
          reason: d.status === 'unit_error' ? '单位与模板不一致' : '由对话抽取，置信度偏低',
          raw_text: d.raw_text,
        })
      }
    }
  }
  return out
})

/** 字段来源分布：让用户知道哪些值是系统替自己填的。 */
const sources = computed(() => {
  const counts = { conversation: 0, manual: 0, template_default: 0, upload: 0 }
  for (const [, d] of Object.entries(props.drafts)) {
    const key = d.source_type || 'manual'
    if (key in counts && String(d.value ?? '').trim()) counts[key] += 1
  }
  return [
    { key: 'conversation', label: '来自对话', value: counts.conversation },
    { key: 'manual', label: '手动填写', value: counts.manual },
    { key: 'template_default', label: '模板默认', value: counts.template_default },
    { key: 'upload', label: '来自上传', value: counts.upload },
  ]
})

const SOURCE_LABEL = {
  conversation: '来自对话',
  manual: '手动填写',
  template_default: '模板默认',
  upload: '来自上传',
  upload_derived: '由上传数据推导',
}

const traceSource = computed(() => {
  if (!props.selected) return []
  const d = draftOf(props.selected.path)
  return [
    { k: '当前值', v: String(d.value ?? '').trim() || '（空）' },
    { k: '来源', v: SOURCE_LABEL[d.source_type] || d.source_type || '未知' },
    { k: '原始表达', v: d.raw_text || '—' },
    { k: '置信度', v: typeof d.confidence === 'number' ? d.confidence.toFixed(2) : '—' },
    { k: '状态', v: d.status || '—' },
    { k: '单位', v: d.unit || '—' },
  ]
})

const blocking = computed(() => props.missing.length)
</script>

<template>
  <aside class="meta-inspector" aria-label="录入检查面板">
    <div class="panel-head">
      <span class="caps">录入检查</span>
      <span class="badge" :class="blocking ? 'badge-warning' : 'badge-success'">
        {{ blocking ? `${blocking} 项待补` : '可以归档' }}
      </span>
    </div>

    <div class="body">
      <!-- 1. 填写进度 -->
      <section class="block">
        <div class="progress-head">
          <span class="caps">必填完成度</span>
          <span class="mono progress-num">{{ filledRequired }}/{{ required.length }}</span>
        </div>
        <div class="bar" role="progressbar" :aria-valuenow="progress" aria-valuemin="0" aria-valuemax="100">
          <div class="bar-fill" :style="{ width: `${progress}%` }" />
        </div>
        <p class="hint muted">
          另有 {{ optionalFilled }} 个选填字段已填写。归档只校验必填项。
        </p>
      </section>

      <!-- 2. 阻塞归档项 -->
      <section class="block">
        <div class="progress-head">
          <span class="caps">阻塞归档</span>
          <span class="mono progress-num">{{ missing.length }}</span>
        </div>

        <p v-if="!missing.length" class="empty muted">必填信息已齐全。</p>

        <ul v-else class="list">
          <li v-for="m in missing" :key="m.field_path" class="row row--blocking">
            <div class="row-main">
              <span class="row-title">{{ m.label }}</span>
              <span class="row-sub muted">必填项尚未填写</span>
            </div>
            <div class="row-actions">
              <button class="mini" type="button" @click="$emit('focus', m.field_path)">定位</button>
              <button class="mini mini--ghost" type="button" @click="$emit('defer', m.field_path)">
                稍后补
              </button>
            </div>
          </li>
        </ul>
      </section>

      <!-- 3. 需要核对 -->
      <section class="block">
        <div class="progress-head">
          <span class="caps">建议核对</span>
          <span class="mono progress-num">{{ attention.length }}</span>
        </div>

        <p v-if="!attention.length" class="empty muted">没有低置信度或单位异常的字段。</p>

        <ul v-else class="list">
          <li v-for="a in attention" :key="a.path">
            <button class="row row--attention" type="button" @click="$emit('select', a)">
              <span class="row-main">
                <span class="row-title">
                  {{ a.label }}
                  <span class="mono row-value">{{ a.value }}{{ a.unit ? ` ${a.unit}` : '' }}</span>
                </span>
                <span class="row-sub muted">{{ a.reason }}</span>
              </span>
              <span v-if="a.conf !== null" class="mono conf">{{ a.conf.toFixed(2) }}</span>
            </button>
          </li>
        </ul>
      </section>

      <!-- 4. 已稍后补 -->
      <section v-if="deferred.length" class="block">
        <div class="progress-head">
          <span class="caps">已标记稍后补</span>
          <span class="mono progress-num">{{ deferred.length }}</span>
        </div>
        <ul class="list">
          <li v-for="d in deferred" :key="d.field_path" class="deferred-item">
            <span class="mono">{{ d.label }}</span>
            <button class="mini mini--ghost" type="button" @click="$emit('focus', d.field_path)">
              去填写
            </button>
          </li>
        </ul>
      </section>

      <!-- 5. 来源分布 -->
      <section class="block">
        <span class="caps">字段来源</span>
        <div class="src-grid">
          <div v-for="s in sources" :key="s.key" class="src">
            <span class="mono src-num">{{ s.value }}</span>
            <span class="src-label">{{ s.label }}</span>
          </div>
        </div>
      </section>

      <!-- 6. 字段溯源 -->
      <section class="block">
        <span class="caps">字段溯源</span>
        <p v-if="!selected" class="empty muted">
          在中间表单点击任意字段，查看它由谁填入、原始表达是什么。
        </p>
        <dl v-else class="trace">
          <div class="trace-head">{{ selected.label }}</div>
          <div v-for="row in traceSource" :key="row.k" class="trace-row">
            <dt>{{ row.k }}</dt>
            <dd class="mono">{{ row.v }}</dd>
          </div>
        </dl>
      </section>
    </div>

    <div class="foot">
      <button class="btn btn-primary block-btn" type="button" @click="$emit('confirm')">
        确认并归档
      </button>
      <p v-if="blocking" class="foot-hint muted">
        还需补全 {{ blocking }} 项必填信息（可点「稍后补」跳过并说明）。
      </p>
    </div>
  </aside>
</template>

<style scoped>
.meta-inspector {
  display: flex;
  flex-direction: column;
  min-height: 0;
  min-width: 0;
  background: var(--bg-secondary);
  border-left: 1px solid var(--border-subtle);
}

.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 48px;
  padding: 0 var(--space-4);
  border-bottom: 1px solid var(--border-subtle);
  flex: none;
}

.body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}

.block {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.progress-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.progress-num {
  font-size: 12px;
  color: var(--text-secondary);
}

.bar {
  height: 6px;
  border-radius: 999px;
  background: var(--bg-tertiary);
  overflow: hidden;
}
.bar-fill {
  height: 100%;
  background: var(--accent);
  transition: width var(--duration-normal) var(--ease-standard);
}

.hint {
  font: var(--text-xs);
  line-height: 1.4;
}
.empty {
  font: var(--text-sm);
}

.list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  width: 100%;
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--border-subtle);
  border-left-width: 2px;
  border-radius: var(--radius-md);
  background: var(--bg-primary);
  text-align: left;
}
.row--blocking {
  border-left-color: var(--warning);
}
.row--attention {
  cursor: pointer;
  border-left-color: var(--warning);
  transition: background var(--duration-fast) var(--ease-standard);
}
.row--attention:hover {
  background: var(--bg-tertiary);
}

.row-main {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
  min-width: 0;
}
.row-title {
  font: var(--text-sm);
  color: var(--text-primary);
}
.row-value {
  font-size: 12px;
  color: var(--text-secondary);
  margin-left: var(--space-1);
}
.row-sub {
  font: var(--text-xs);
  line-height: 1.35;
}

.row-actions {
  display: flex;
  gap: var(--space-1);
  flex: none;
}
.mini {
  padding: 2px 8px;
  font: var(--text-xs);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  background: var(--bg-secondary);
  color: var(--text-primary);
  cursor: pointer;
}
.mini:hover {
  background: var(--bg-tertiary);
}
.mini--ghost {
  background: transparent;
  color: var(--text-secondary);
}

.deferred-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  font: var(--text-sm);
  color: var(--text-secondary);
}

.conf {
  font-size: 12px;
  color: var(--text-secondary);
  flex: none;
}

.src-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-2);
}
.src {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  background: var(--bg-primary);
}
.src-num {
  font: var(--text-lg);
  color: var(--text-primary);
}
.src-label {
  font: var(--text-xs);
  color: var(--text-secondary);
}

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
  grid-template-columns: 68px 1fr;
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

.foot {
  flex: none;
  padding: var(--space-3) var(--space-4);
  border-top: 1px solid var(--border-subtle);
  background: var(--glass-bg-strong);
  backdrop-filter: blur(var(--glass-blur));
  -webkit-backdrop-filter: blur(var(--glass-blur));
}
.block-btn {
  width: 100%;
}
.foot-hint {
  font: var(--text-xs);
  margin-top: var(--space-2);
  line-height: 1.4;
}

@media (max-width: 1024px) {
  .meta-inspector {
    border-left: none;
  }
}
</style>