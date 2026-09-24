<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { loadArchive, session } from '../data/session.js'

const keyword = ref('')

async function ensureData() {
  await loadArchive()
  if (session.archive.length) return
  // 后端未连接时，用链路导出的真实识别结果作为示例档案，保证页面可核对
  try {
    const res = await fetch(`${import.meta.env.BASE_URL}data/analysis.json`, { cache: 'no-store' })
    const data = await res.json()
    session.archive = (data.experiments || []).map((e) => ({
      id: e.id,
      title: `${e.sheet} 实验数据`,
      experiment_type: e.regions?.[0]?.kindLabel || '—',
      operator: '—',
      date_start: (data.generatedAt || '').slice(0, 10),
      status: 'demo',
      source_file: e.sourceFile,
      regions: e.regions,
    }))
  } catch {
    /* 保持空态 */
  }
}

onMounted(ensureData)

const rows = computed(() => {
  const list = session.archive
  const k = keyword.value.trim().toLowerCase()
  if (!k) return list
  return list.filter((r) => `${r.id} ${r.title} ${r.operator}`.toLowerCase().includes(k))
})

const isDemo = computed(() => session.archive.some((r) => r.status === 'demo'))

/**
 * 卡片去向：
 * - 只有元数据、还没上传数据表格的实验 → 直接进入「数据识别」，接着把流程走完；
 * - 已上传数据表格的（以及示例档案）→ 进入规范文档详情。
 * session_id 用于回到该实验原来那个会话，避免数据关联到新会话。
 */
function targetOf(row) {
  if (row.status === 'demo' || !row.session_id || row.raw_file) return `/archive/${row.id}`
  return `/recognize?session=${encodeURIComponent(row.session_id)}`
}
</script>

<template>
  <main class="page">
    <div class="wrap">
      <header class="head">
        <div>
          <h1>实验档案</h1>
          <p class="muted">
            归档后的规范文档，供后续研究复用，也可通过 Public API 供外部系统调用。
          </p>
        </div>
        <div class="head-actions">
          <input
            v-model="keyword"
            class="input search"
            type="search"
            placeholder="搜索实验编号或标题"
            aria-label="搜索实验档案"
          />
          <RouterLink to="/setup" class="btn btn-primary">新建实验</RouterLink>
        </div>
      </header>

      <p v-if="isDemo" class="notice">
        后端服务未连接，以下为识别链路已跑通的示例档案（数据真实，尚未经人工确认入库）。
      </p>

      <p v-if="!rows.length" class="empty muted">
        没有匹配的实验档案。先到「新建实验」录入一次实验的初始信息。
      </p>

      <ul v-else class="cards">
        <li v-for="row in rows" :key="row.id">
          <RouterLink :to="targetOf(row)" class="card-item">
            <div class="card-top">
              <span class="rid mono">{{ row.id }}</span>
              <span class="badge" :class="row.status === 'demo' ? 'badge-neutral' : 'badge-success'">
                {{ row.status === 'demo' ? '示例' : '已归档' }}
              </span>
            </div>
            <h2>{{ row.title || '（未命名实验）' }}</h2>
            <dl class="meta">
              <div>
                <dt>类型</dt>
                <dd>{{ row.experiment_type || '—' }}</dd>
              </div>
              <div>
                <dt>实验员</dt>
                <dd>{{ row.operator || '—' }}</dd>
              </div>
              <div>
                <dt>日期</dt>
                <dd>{{ row.date_start || '—' }}</dd>
              </div>
            </dl>
          </RouterLink>
        </li>
      </ul>
    </div>
  </main>
</template>

<style scoped>
.page {
  min-height: 0;
  overflow-y: auto;
  position: relative;
  z-index: 1;
}
.wrap {
  max-width: 1080px;
  margin: 0 auto;
  padding: var(--space-8) var(--space-6) var(--space-9);
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}

.head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--space-5);
  flex-wrap: wrap;
}
.head h1 {
  font: var(--text-2xl);
  letter-spacing: var(--tracking-tight);
}
.head p {
  margin-top: var(--space-2);
  font: var(--text-sm);
  max-width: 58ch;
  line-height: 1.6;
}
.head-actions {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}
.search {
  width: 240px;
  background: var(--bg-secondary);
}
.head-actions a {
  text-decoration: none;
}

.notice {
  padding: var(--space-3) var(--space-4);
  border-left: 2px solid var(--warning);
  background: var(--warning-bg);
  border-radius: var(--radius-md);
  font: var(--text-xs);
  line-height: 1.5;
}

.empty {
  font: var(--text-sm);
  padding: var(--space-5);
  border: 1px dashed var(--border-strong);
  border-radius: var(--radius-lg);
}

.cards {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: var(--space-4);
}
.card-item {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  height: 100%;
  padding: var(--space-5);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  background: var(--bg-secondary);
  box-shadow: var(--shadow-sm);
  text-decoration: none;
  color: inherit;
  transition: box-shadow var(--duration-fast) var(--ease-standard),
    transform var(--duration-fast) var(--ease-standard);
}
.card-item:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}
.card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}
.rid {
  font-size: 12px;
  color: var(--text-secondary);
}
.card-item h2 {
  font: var(--text-base);
  font-weight: 500;
}

.meta {
  display: flex;
  gap: var(--space-4);
  margin: 0;
  margin-top: auto;
}
.meta dt {
  font: var(--text-xs);
  color: var(--text-tertiary);
}
.meta dd {
  margin: 2px 0 0;
  font: var(--text-sm);
}

@media (max-width: 640px) {
  .wrap {
    padding: var(--space-6) var(--space-4) var(--space-8);
  }
  .search {
    width: 100%;
  }
}
</style>