<script setup>
import { computed, nextTick, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import WorkbenchLayout from '../layouts/WorkbenchLayout.vue'
import ChatPanel from '../components/ChatPanel.vue'
import TemplateForm from '../components/TemplateForm.vue'
import MetadataInspector from '../components/MetadataInspector.vue'
import StatusBar from '../components/StatusBar.vue'
import { useToast } from '../composables/useToast.js'
import {
  confirmSession,
  deferField,
  deferredFields,
  initSession,
  missingFields,
  preSheets,
  sendMessage,
  session,
  setField,
} from '../data/session.js'

const router = useRouter()
const { show } = useToast()

const streaming = ref(false)
const selected = ref(null)

const STEPS = [
  { id: 'pre', label: '实验前 · 录入' },
  { id: 'post', label: '实验后 · 识别' },
  { id: 'archive', label: '归档 · 调用' },
]

onMounted(initSession)

async function onSend(text) {
  streaming.value = true
  try {
    await sendMessage(text)
  } finally {
    streaming.value = false
  }
}

const focusPath = ref("")

/**
 * 从右侧录入检查面板定位字段。
 * 先清空再赋值，保证连续点击同一字段也能重新触发滚动。
 */
async function onFocusField(path) {
  if (!path) return
  focusPath.value = ""
  await nextTick()
  focusPath.value = path
}

const statusExperiment = computed(() => ({
  id: session.drafts['01_Metadata.experiment_id']?.value || session.experimentId || '—',
  status: missingFields.value.length ? 'reviewing' : 'draft',
  lastSaved: session.online ? '草稿同步到后端' : '本地草稿（未连接后端）',
}))

async function onConfirm() {
  if (missingFields.value.length) {
    show(`还有 ${missingFields.value.length} 项必填信息未填写，请先补全或标记「稍后补」。`)
    return
  }
  try {
    const exp = await confirmSession()
    if (exp.local) {
      show('本地草稿模式：未写入后端归档，请先启动后端服务。')
      return
    }
    show(`实验已归档：${exp.id}，接着上传这次实验的原始数据表格。`)
    router.push({ name: 'recognize' })
  } catch (e) {
    const missing = e.payload?.detail?.missing || []
    if (e.status === 409) {
      show(`还缺 ${missing.length} 项必填信息，无法归档`)
      return
    }
    show(`归档失败：${e.message}`)
  }
}

function onSave() {
  show('草稿已保存。Raw 数据保持只读，未被修改。')
}
</script>

<template>
  <WorkbenchLayout
    title="新建实验"
    subtitle="实验前录入初始信息，形成实验记录草稿"
    :steps="STEPS"
    active-step="pre"
  >
    <template #actions>
      <span class="badge" :class="session.online ? 'badge-success' : 'badge-warning'">
        {{ session.online ? '已连接后端' : '本地草稿模式' }}
      </span>
    </template>

    <template #chat>
      <ChatPanel
        :messages="session.messages"
        :streaming="streaming"
        placeholder="例如：今天用 120 mg 的 A600 树脂和 50 mL 溶液做 SO4 吸附"
        hint="支持中文自然语言。Jarvis 只负责记录与校验，不做科学推理。"
        @send="onSend"
      />
    </template>

    <template #form>
      <section class="pane-head">
        <span class="caps">FormDraft</span>
        <span class="muted count">
          {{ preSheets.length }} 个分区 ·
          {{ preSheets.reduce((n, s) => n + s.fields.length, 0) }} 个字段
        </span>
      </section>
      <div class="pane-body">
        <TemplateForm
          :sheets="preSheets"
          :drafts="session.drafts"
          :focus-path="focusPath"
          @change="({ field_path, value }) => setField(field_path, value)"
          @defer="(field) => deferField(field.path)"
          @focus-field="selected = { label: $event.label, path: $event.path }"
        />
      </div>
    </template>

    <template #inspector>
      <MetadataInspector
        :sheets="preSheets"
        :drafts="session.drafts"
        :missing="missingFields"
        :deferred="deferredFields"
        :selected="selected"
        @focus="onFocusField"
        @defer="(path) => deferField(path)"
        @select="selected = $event"
        @confirm="onConfirm"
      />
    </template>

    <template #status>
      <StatusBar
        :experiment="statusExperiment"
        confirm-label="确认并归档"
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
  height: 48px;
  padding: 0 var(--space-4);
  border-bottom: 1px solid var(--border-subtle);
  flex: none;
  background: var(--bg-primary);
}
.count {
  font: var(--text-xs);
}
.pane-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: var(--space-5) var(--space-5) var(--space-7);
  background: var(--bg-primary);
}
</style>