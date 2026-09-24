<script setup>
import { computed, ref } from 'vue'

const groups = [
  {
    id: 'portal',
    label: 'Portal Assistant API',
    note: 'PortalJarvis 专用，随会话鉴权',
    items: [
      {
        id: 'templates',
        method: 'GET',
        path: '/portal/assistant/templates/{template_id}',
        desc: '获取实验记录模板 Schema（字段、必填项、单位、选项）。',
        returns: '{ template_id, version, stages[], sheets[] }',
        code: `curl "http://127.0.0.1:8000/portal/assistant/templates/expresin_template_v1"`,
      },
      {
        id: 'create-session',
        method: 'POST',
        path: '/portal/assistant/sessions',
        desc: '创建一次实验记录会话（AssistantSession），返回实验编号建议。',
        body: '{ template_id, project_id, user_id? }',
        code: `curl -X POST http://127.0.0.1:8000/portal/assistant/sessions \\
  -H "Content-Type: application/json" \\
  -d '{"template_id":"expresin_template_v1","project_id":"DHT"}'`,
      },
      {
        id: 'messages',
        method: 'POST',
        path: '/portal/assistant/sessions/{id}/messages',
        desc: '发送自然语言，抽取字段写入 FormDraft，并返回缺失项追问。',
        body: '{ text }',
        returns: '{ reply, extracted[], missing[], form_state[] }',
        code: `curl -X POST http://127.0.0.1:8000/portal/assistant/sessions/ses_xxx/messages \\
  -H "Content-Type: application/json" \\
  -d '{"text":"今天用 120 mg 的 A600 树脂和 50 mL 溶液做 SO4 吸附，初始浓度 100 mg/L"}'`,
      },
      {
        id: 'form-state',
        method: 'GET',
        path: '/portal/assistant/sessions/{id}/form-state',
        desc: '读取当前表单草稿（含置信度、单位、来源、状态）。',
        code: `curl http://127.0.0.1:8000/portal/assistant/sessions/ses_xxx/form-state`,
      },
      {
        id: 'missing',
        method: 'GET',
        path: '/portal/assistant/sessions/{id}/missing-fields',
        desc: '列出必填但尚未填写的字段，供追问与前置检查。',
        code: `curl http://127.0.0.1:8000/portal/assistant/sessions/ses_xxx/missing-fields`,
      },
      {
        id: 'upload',
        method: 'POST',
        path: '/portal/assistant/sessions/{id}/upload',
        desc: '上传 Excel / CSV 原始数据，入 Raw 层（只读），并反向解析填充草稿。',
        body: 'multipart/form-data: file, analyze',
        returns: '{ raw: {uri, sha256}, recognized: { source, regions[] } }',
        code: `curl -X POST http://127.0.0.1:8000/portal/assistant/sessions/ses_xxx/upload \\
  -F "file=@20250528 DHT Cl SO4.xlsx" \\
  -F "analyze=true"`,
      },
      {
        id: 'confirm',
        method: 'POST',
        path: '/portal/assistant/sessions/{id}/confirm',
        desc: '人工确认后写入 Processed 层，生成 ExperimentID，并留存字段级溯源。',
        returns: '{ id, title, processed, provenance }',
        code: `curl -X POST http://127.0.0.1:8000/portal/assistant/sessions/ses_xxx/confirm \\
  -H "Content-Type: application/json" \\
  -d '{"experiment_id":"RES-20260919-001"}'`,
      },
    ],
  },
  {
    id: 'v1',
    label: 'Public API v1',
    note: '供其他实验室与系统调用，API Key 鉴权',
    items: [
      {
        id: 'experiments',
        method: 'GET',
        path: '/v1/experiments',
        desc: '列出本租户下的实验档案，支持 cursor 分页。',
        code: `curl http://127.0.0.1:8000/v1/experiments \\
  -H "Authorization: Bearer $EXPRESIN_API_KEY"`,
      },
      {
        id: 'experiment-detail',
        method: 'GET',
        path: '/v1/experiments/{id}',
        desc: '获取单个实验的元数据与规范文档。',
        code: `curl http://127.0.0.1:8000/v1/experiments/RES-20260919-001 \\
  -H "Authorization: Bearer $EXPRESIN_API_KEY"`,
      },
      {
        id: 'processed',
        method: 'GET',
        path: '/v1/experiments/{id}/data/processed',
        desc: '获取规范化的 Processed 数据（canonical schema）。',
        code: `curl http://127.0.0.1:8000/v1/experiments/RES-20260919-001/data/processed \\
  -H "Authorization: Bearer $EXPRESIN_API_KEY"`,
      },
      {
        id: 'mapping-suggest',
        method: 'POST',
        path: '/v1/mapping/suggest',
        desc: '对给定表头给出标准字段映射建议与置信度。',
        body: '{ headers[], samples?[] }',
        code: `curl -X POST http://127.0.0.1:8000/v1/mapping/suggest \\
  -H "Authorization: Bearer $EXPRESIN_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{"headers":["BV","V","area","calculated  ppm"]}'`,
      },
      {
        id: 'mapping-confirm',
        method: 'POST',
        path: '/v1/mapping/confirm',
        desc: '提交人工确认后的映射，写入 MappingExample 供后续 Few-shot 检索。',
        code: `curl -X POST http://127.0.0.1:8000/v1/mapping/confirm \\
  -H "Authorization: Bearer $EXPRESIN_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{"header_hash":"...","mapping":{...}}'`,
      },
      {
        id: 'evidence',
        method: 'GET',
        path: '/v1/experiments/{id}/evidence',
        desc: '获取结构化证据包（Evidence Package），用于推送至更大大脑。',
        code: `curl http://127.0.0.1:8000/v1/experiments/RES-20260919-001/evidence \\
  -H "Authorization: Bearer $EXPRESIN_API_KEY"`,
      },
      {
        id: 'webhooks',
        method: 'POST',
        path: '/v1/webhooks',
        desc: '注册 Webhook，在 experiment.processed 等事件发生时推送证据包。',
        body: '{ url, events[], secret }',
        code: `curl -X POST http://127.0.0.1:8000/v1/webhooks \\
  -H "Authorization: Bearer $EXPRESIN_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{"url":"https://brain.example.com/hook","events":["experiment.processed"]}'`,
      },
      {
        id: 'delete-experiment',
        method: 'DELETE',
        path: '/v1/experiments/{id}',
        desc: '删除实验（保留审计记录）。',
        code: `curl -X DELETE http://127.0.0.1:8000/v1/experiments/RES-20260919-001 \\
  -H "Authorization: Bearer $EXPRESIN_API_KEY"`,
      },
    ],
  },
  {
    id: 'ops',
    label: '运维与约定',
    note: '健康检查、错误规范、版本与幂等',
    items: [
      {
        id: 'health',
        method: 'GET',
        path: '/api/health',
        desc: '健康检查，前端据此判断「在线 / 本地草稿」模式。',
        code: `curl http://127.0.0.1:8000/api/health`,
      },
      {
        id: 'errors',
        method: 'GET',
        path: '错误规范',
        desc: '统一返回 { detail, request_id }，HTTP 状态码语义化：400 参数、401 鉴权、404 不存在、409 冲突、429 限流。',
        code: `{
  "detail": "未知的 template_id: foo",
  "request_id": "req_8f2c1a"
}`,
      },
      {
        id: 'conventions',
        method: 'GET',
        path: '版本与幂等',
        desc: '破坏性变更走 /v2/；上传与确认接口支持 Idempotency-Key 头；列表接口支持 cursor 分页。',
        code: `Idempotency-Key: 6f1c-4a2b-9d31
Authorization: Bearer $EXPRESIN_API_KEY`,
      },
    ],
  },
]

const activeId = ref('create-session')
const flat = groups.flatMap((g) => g.items.map((i) => ({ ...i, group: g.label })))
const active = computed(() => flat.find((i) => i.id === activeId.value) || flat[0])

const METHOD_CLASS = {
  GET: 'badge-success',
  POST: 'badge-accent',
  PUT: 'badge-warning',
  DELETE: 'badge-error',
}
</script>

<template>
  <main class="docs">
    <aside class="nav">
      <h1 class="nav-title">API 文档</h1>
      <p class="nav-sub muted">
        契约版本 v0 · OpenAPI 3.1 风格。所有页面功能先有 API，再有界面。
      </p>

      <div v-for="g in groups" :key="g.id" class="nav-group">
        <h2 class="caps">{{ g.label }}</h2>
        <p class="nav-note muted">{{ g.note }}</p>
        <ul>
          <li v-for="item in g.items" :key="item.id">
            <button
              type="button"
              class="nav-item"
              :class="{ 'is-active': item.id === activeId }"
              @click="activeId = item.id"
            >
              <span class="m mono" :class="`m--${item.method.toLowerCase()}`">{{ item.method }}</span>
              <span class="p mono">{{ item.path }}</span>
            </button>
          </li>
        </ul>
      </div>
    </aside>

    <section class="content">
      <div class="endpoint">
        <span class="badge" :class="METHOD_CLASS[active.method] || 'badge-info'">
          {{ active.method }}
        </span>
        <span class="mono path">{{ active.path }}</span>
      </div>

      <p class="desc">{{ active.desc }}</p>

      <dl v-if="active.body || active.returns" class="params">
        <div v-if="active.body">
          <dt>请求体</dt>
          <dd class="mono">{{ active.body }}</dd>
        </div>
        <div v-if="active.returns">
          <dt>返回</dt>
          <dd class="mono">{{ active.returns }}</dd>
        </div>
      </dl>

      <p class="muted note">
        当前状态：Portal API 已按本文档实现，Public API v1 正在接入。前端在
        <code class="mono">/api/health</code> 不可达时自动回退为本地草稿模式。
      </p>
    </section>

    <aside class="examples">
      <h2 class="caps">示例</h2>
      <pre class="code">{{ active.code }}</pre>
    </aside>
  </main>
</template>

<style scoped>
.docs {
  display: grid;
  grid-template-columns: 240px minmax(0, 1fr) 360px;
  min-height: 0;
  overflow: hidden;
  position: relative;
  z-index: 1;
}

.nav {
  overflow-y: auto;
  padding: var(--space-5) var(--space-4);
  border-right: 1px solid var(--border-subtle);
  background: var(--bg-secondary);
}
.nav-title {
  font: var(--text-lg);
}
.nav-sub {
  margin-top: var(--space-2);
  font: var(--text-xs);
  line-height: 1.5;
}
.nav-group {
  margin-top: var(--space-5);
}
.nav-note {
  font: var(--text-xs);
  margin: var(--space-1) 0 var(--space-2);
  line-height: 1.4;
}
.nav-group ul {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.nav-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  width: 100%;
  padding: var(--space-2);
  border: none;
  border-radius: var(--radius-md);
  background: transparent;
  text-align: left;
  cursor: pointer;
  transition: background var(--duration-fast) var(--ease-standard);
}
.nav-item:hover {
  background: var(--bg-tertiary);
}
.nav-item.is-active {
  background: var(--accent-subtle);
}
.m {
  flex: none;
  width: 46px;
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.02em;
}
.m--get {
  color: var(--success);
}
.m--post {
  color: var(--accent);
}
.m--put {
  color: var(--warning);
}
.m--delete {
  color: var(--error);
}
.p {
  font-size: 11px;
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.content {
  overflow-y: auto;
  padding: var(--space-6) var(--space-6) var(--space-8);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  max-width: 800px;
}
.endpoint {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex-wrap: wrap;
}
.path {
  font-size: 15px;
  word-break: break-all;
}
.desc {
  font: var(--text-base);
  line-height: 1.6;
  color: var(--text-primary);
}
.params {
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-4);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  background: var(--bg-secondary);
}
.params dt {
  font: var(--text-xs);
  letter-spacing: var(--tracking-caps);
  text-transform: uppercase;
  color: var(--text-tertiary);
}
.params dd {
  margin: var(--space-1) 0 0;
  font-size: 13px;
  color: var(--text-primary);
  word-break: break-all;
}
.note {
  font: var(--text-xs);
  line-height: 1.6;
}
code {
  padding: 2px 6px;
  border-radius: var(--radius-sm);
  background: var(--bg-tertiary);
  font-size: 12px;
}

.examples {
  overflow-y: auto;
  padding: var(--space-5) var(--space-4);
  border-left: 1px solid var(--border-subtle);
  background: var(--bg-secondary);
}
.examples h2 {
  margin-bottom: var(--space-3);
}
.code {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-all;
}

@media (max-width: 1180px) {
  .docs {
    grid-template-columns: 200px minmax(0, 1fr);
  }
  .examples {
    display: none;
  }
}
@media (max-width: 820px) {
  .docs {
    grid-template-columns: minmax(0, 1fr);
    overflow-y: auto;
  }
  .nav {
    border-right: none;
    border-bottom: 1px solid var(--border-subtle);
  }
}
</style>