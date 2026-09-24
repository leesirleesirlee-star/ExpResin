<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import WorkbenchLayout from '../layouts/WorkbenchLayout.vue'
import ChatPanel from '../components/ChatPanel.vue'
import DynamicForm from '../components/DynamicForm.vue'
import MappingInspector from '../components/MappingInspector.vue'
import StatusBar from '../components/StatusBar.vue'
import { useToast } from '../composables/useToast.js'
import { collectIssues } from '../data/demo.js'
import {
  analyteOptions,
  confirmSession,
  initSession,
  loadSchemaColumns,
  resumeSession,
  reviewColumn,
  schemaColumns,
  sendMessage,
  session,
  uploadRawFile,
} from '../data/session.js'

const router = useRouter()
const route = useRoute()
const { show } = useToast()

const STEPS = [
  { id: 'pre', label: '实验前 · 录入' },
  { id: 'post', label: '实验后 · 识别' },
  { id: 'archive', label: '归档 · 调用' },
]

const fileInput = ref(null)
const sheetName = ref('')
const regions = ref([])
const sourceInfo = ref(null)
const selected = ref(null)
const uploading = ref(false)
const uploadElapsed = ref(0)
let uploadTimer = null

// 解析耗时以秒计，必须让等待可见，否则用户会以为页面卡死。
function startUploadClock() {
  stopUploadClock()
  uploadElapsed.value = 0
  uploadTimer = window.setInterval(() => {
    uploadElapsed.value += 1
  }, 1000)
}

function stopUploadClock() {
  if (uploadTimer !== null) {
    window.clearInterval(uploadTimer)
    uploadTimer = null
  }
}

onUnmounted(stopUploadClock)
const streaming = ref(false)
const archiving = ref(false)

const messages = computed(() => session.messages)

const issues = computed(() => collectIssues(regions.value, sourceInfo.value?.failedBlocks ?? []))

/**
 * 「待确认」只统计可由人工就地处置的列级问题。
 * 列块识别失败无法在列级处置（需重新上传），若混入此计数，用户点完所有可处置项
 * 后计数仍不为零，会误以为还有遗漏。
 */
const pendingTotal = computed(
  () =>
    issues.value.pending.length +
    issues.value.lowConfidence.length +
    issues.value.missing.length +
    issues.value.unitErrors.length +
    issues.value.analyteConflicts.length,
)

/** 识别失败的列块数单独展示，它指向的是「重试」而不是「确认」。 */
const failedTotal = computed(() => issues.value.failedBlocks.length)

const REVIEW_TOAST = {
  confirm: '已确认映射正确',
  remap: (target) => `已改判为 ${target}`,
  ignore: '已标记为非数据列',
}

/**
 * 提交人工判定。
 * 后端以「追加新版本」保存修正快照，前端用返回的快照整体刷新，保证与后端一致。
 */
async function onResolve({ block, col, action, target_field }) {
  try {
    const res = await reviewColumn(block, col, action, target_field)
    if (!res.ok) {
      show(res.reason)
      return
    }
    regions.value = session.recognized?.regions ?? regions.value
    const label =
      typeof REVIEW_TOAST[action] === 'function'
        ? REVIEW_TOAST[action](target_field)
        : REVIEW_TOAST[action]
    show(`${block} / ${col} ${label}`)
    selected.value = null
  } catch (e) {
    show(`人工判定保存失败：${e.message}`)
  }
}

const mappedStats = computed(() => {
  let total = 0
  let mapped = 0
  for (const region of regions.value) {
    for (const block of region.blocks ?? []) {
      for (const col of block.columns ?? []) {
        total += 1
        if (col.target) mapped += 1
      }
    }
  }
  return { total, mapped }
})

const statusExperiment = computed(() => ({
  id: session.drafts['01_Metadata.experiment_id']?.value || session.experimentId || '—',
  status: session.recognized ? 'reviewing' : 'draft',
  lastSaved: sourceInfo.value ? `已识别：${sourceInfo.value.file}` : '尚未上传数据',
}))

onMounted(async () => {
  // 从实验档案点进来时带上 ?session=，须沿用该实验原来的会话继续识别，
  // 否则上传的数据会落到新会话，归档时实验编号冲突。
  const resumeId = typeof route.query.session === 'string' ? route.query.session : ''
  if (resumeId) {
    await resumeSession(resumeId)
  } else {
    await initSession()
  }
  await loadSchemaColumns()
  if (session.recognized?.regions?.length) {
    regions.value = session.recognized.regions
    sourceInfo.value = session.recognized.source || null
    sheetName.value = sourceInfo.value?.sheet || ''
    return
  }
  // 尚未上传时，加载链路已跑通的示例结果，便于核对界面
  try {
    const res = await fetch(`${import.meta.env.BASE_URL}data/analysis.json`, { cache: 'no-store' })
    const data = await res.json()
    const first = data.experiments?.[0]
    if (first) {
      regions.value = first.regions
      sourceInfo.value = { ...data.source, file: data.source?.file, sheet: first.sheet, demo: true }
    }
  } catch {
    /* 无示例数据时保持空态 */
  }
})

async function onPickFile(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return

  uploading.value = true
  startUploadClock()
  try {
    const res = await uploadRawFile(file, sheetName.value.trim() || null)
    if (!res.ok) {
      show(res.reason)
      return
    }
    const payload = res.result
    regions.value = payload.recognized?.regions ?? []
    sourceInfo.value = payload.recognized?.source ?? { file: file.name }
    sheetName.value = sourceInfo.value.sheet || sheetName.value

    const stats = mappedStats.value
    const sheetNote = sourceInfo.value.sheet ? `（工作表 ${sourceInfo.value.sheet}）` : ''
    const cacheNote = sourceInfo.value.cached ? '（命中缓存，未重复调用模型）' : ''
    const failed = sourceInfo.value.failedBlocks ?? []
    const failNote = failed.length
      ? `，其中 ${failed.length} 个列块识别失败（已降级为待确认，可重新上传重试）`
      : ''
    session.messages.push({
      role: 'assistant',
      content:
        `已解析《${file.name}》${sheetNote}${cacheNote}，识别到 ${regions.value.length} 个数据区、` +
        `${stats.total} 列，其中 ${stats.mapped} 列已映射到标准字段${failNote}。` +
        '请在中间栏逐列核对，低置信度与缺失项列在右侧。',
    })
    show(
      sourceInfo.value.cached
        ? '已命中识别缓存，结果与上次一致。'
        : failed.length
          ? `解析完成，但有 ${failed.length} 个列块失败，可重新上传重试。`
          : '文件解析完成，请逐列确认映射。',
    )
  } catch (e) {
    show(e.offline ? '后端服务不可达，请先启动后端再上传。' : `解析失败：${e.message}`)
  } finally {
    stopUploadClock()
    uploading.value = false
  }
}

async function onSend(text) {
  streaming.value = true
  try {
    await sendMessage(text)
  } finally {
    streaming.value = false
  }
}

async function onConfirm() {
  if (archiving.value) return
  archiving.value = true
  try {
    const exp = await confirmSession()
    if (exp.local) {
      show('本地草稿模式：未写入后端归档，请先启动后端服务。')
      return
    }
    session.messages.push({ role: 'assistant', content: `实验 ${exp.id} 已归档。` })
    show(`实验已归档：${exp.id}`)
    router.push({ name: 'archive' })
  } catch (e) {
    const missing = e.payload?.detail?.missing || []
    if (e.status === 409) {
      const labels = missing.map((m) => m.label || m.field_path).join('、')
      session.messages.push({
        role: 'assistant',
        content:
          `归档被拦截：还有 ${missing.length} 项必填信息未填写 —— ${labels}。` +
          '请到「实验前 · 新建实验」补全后再回来归档。',
      })
      show(`还缺 ${missing.length} 项必填信息，无法归档`)
    } else {
      show(`归档失败：${e.message}`)
    }
  } finally {
    archiving.value = false
  }
}

function onSave() {
  show(
    session.online
      ? '草稿已随会话自动保存到后端，Raw 文件保持只读。'
      : '本地草稿已保存。Raw 文件保持只读。',
  )
}
</script>

<template>
  <WorkbenchLayout
    title="数据识别"
    subtitle="实验后上传原始表格，系统识别列与单位，人工逐列确认"
    :steps="STEPS"
    active-step="post"
  >
    <template #actions>
      <span v-if="sourceInfo?.demo" class="badge badge-neutral">示例数据</span>
      <span class="badge badge-neutral">{{ mappedStats.mapped }}/{{ mappedStats.total }} 列已映射</span>
      <span
        class="badge"
        :class="failedTotal ? 'badge-error' : pendingTotal ? 'badge-warning' : 'badge-success'"
      >
        <template v-if="failedTotal">
          {{ pendingTotal ? `${pendingTotal} 项待确认 · ` : '' }}{{ failedTotal }} 块识别失败
        </template>
        <template v-else>{{ pendingTotal ? `${pendingTotal} 项待确认` : '全部通过' }}</template>
      </span>
    </template>

    <template #chat>
      <ChatPanel
        :messages="messages"
        :streaming="streaming"
        placeholder="说明某列的含义，或提问识别结果"
        hint="上传后系统会反向解析并填充映射；低置信度的列会在右侧列出，可在那里确认、改判或忽略。"
        show-upload
        @send="onSend"
        @upload="fileInput?.click()"
      />
    </template>

    <template #form>
      <section class="pane-head">
        <span class="caps">识别结果</span>
        <div class="head-right">
          <span v-if="sourceInfo" class="muted src mono">
            {{ sourceInfo.file }}{{ sourceInfo.sheet ? ` · ${sourceInfo.sheet}` : '' }}
          </span>
          <label class="sheet-field">
            <span class="caps">工作表</span>
            <input
              v-model="sheetName"
              class="sheet-input"
              type="text"
              placeholder="留空 = 首个"
              :disabled="uploading"
            />
          </label>
          <input
            ref="fileInput"
            class="visually-hidden"
            type="file"
            accept=".xlsx,.xls,.csv"
            @change="onPickFile"
          />
          <button class="btn btn-secondary" type="button" :disabled="uploading" @click="fileInput.click()">
            {{ uploading ? `解析中 ${uploadElapsed}s` : '上传原始数据' }}
          </button>
          <span v-if="uploading" class="upload-hint">
            列块已并行解析，通常 30–60 秒；同一文件重复上传会命中缓存（＜1 秒）
          </span>
        </div>
      </section>

      <div class="pane-body">
        <div v-if="!regions.length" class="empty">
          <div class="skeleton empty-line"></div>
          <div class="skeleton empty-line short"></div>
          <p class="muted">
            {{
              uploading
                ? `正在解析文件…已用时 ${uploadElapsed} 秒`
                : '尚未识别到数据。上传一份 Excel / CSV 原始数据开始。'
            }}
          </p>
        </div>

        <DynamicForm v-else :regions="regions" :selected="selected" @select="selected = $event" />
      </div>
    </template>

    <template #inspector>
      <MappingInspector
        :issues="issues"
        :regions="regions"
        :selected="selected"
        :schema-columns="schemaColumns"
        :analyte-options="analyteOptions"
        @select="selected = $event"
        @resolve="onResolve"
        @confirm="onConfirm"
      />
    </template>

    <template #status>
      <StatusBar
        :experiment="statusExperiment"
        confirm-label="确认识别结果"
        save-label="保存草稿"
        @save="onSave"
        @confirm="onConfirm"
      />
    </template>
  </WorkbenchLayout>
</template>

<style scoped>
.pane-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  height: 48px;
  padding: 0 var(--space-4);
  border-bottom: 1px solid var(--border-subtle);
  flex: none;
  background: var(--bg-primary);
}
.head-right {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  min-width: 0;
}
.src {
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 260px;
}
.upload-hint {
  font-size: 12px;
  color: #64748b;
}

.sheet-field {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex: none;
}
.sheet-input {
  width: 110px;
  height: 28px;
  padding: 0 var(--space-2);
  font: var(--text-sm);
  color: var(--text-primary);
  background: var(--bg-secondary);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  transition: border-color var(--transition-fast);
}
.sheet-input:focus {
  outline: none;
  border-color: var(--accent);
}
.sheet-input:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.pane-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  background: var(--bg-primary);
}
.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  opacity: 0;
  pointer-events: none;
}
.empty {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  align-items: center;
  padding: var(--space-8) var(--space-6);
}
.empty-line {
  width: 420px;
  max-width: 70%;
  height: 14px;
}
.empty-line.short {
  width: 260px;
}
.empty p {
  font: var(--text-sm);
}
</style>