<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../data/api.js'
import { useToast } from '../composables/useToast.js'

const router = useRouter()
const { show } = useToast()

const users = ref([])
const experiments = ref([])
const loading = ref(true)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [u, e] = await Promise.all([api.adminUsers(), api.adminExperiments()])
    users.value = u.users
    experiments.value = e.experiments
  } catch (err) {
    error.value = err.message || '加载失败'
    show(error.value, { tone: 'error' })
  } finally {
    loading.value = false
  }
}

function openExperiment(id) {
  router.push({ name: 'archive-detail', params: { id } })
}

function fmtTime(s) {
  return s ? String(s).replace('T', ' ').slice(0, 16) : '—'
}

onMounted(load)
</script>

<template>
  <main class="page">
    <div class="wrap">
      <header class="head">
        <div>
          <h1 class="title">数据管理</h1>
          <p class="subtitle">全部实验员账号与归档数据总览（仅管理员可见）</p>
        </div>
        <button class="btn btn-secondary" type="button" :disabled="loading" @click="load">
          {{ loading ? '刷新中…' : '刷新' }}
        </button>
      </header>

      <p v-if="error" class="error" role="alert">{{ error }}</p>

      <!-- 用户列表 -->
      <section class="panel">
        <h2 class="panel-title">实验员账号 <span class="count">{{ users.length }}</span></h2>
        <div class="table-wrap">
          <table class="table">
            <thead>
              <tr>
                <th>用户名</th>
                <th>姓名</th>
                <th>角色</th>
                <th class="num">归档实验数</th>
                <th>创建时间</th>
                <th>状态</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="u in users" :key="u.id">
                <td class="mono">{{ u.username }}</td>
                <td>{{ u.display_name || '—' }}</td>
                <td>
                  <span class="tag" :class="u.role === 'admin' ? 'tag--admin' : ''">
                    {{ u.role === 'admin' ? '管理员' : '实验员' }}
                  </span>
                </td>
                <td class="num">{{ u.experiment_count }}</td>
                <td class="mono muted">{{ fmtTime(u.created_at) }}</td>
                <td>
                  <span v-if="u.must_change_password" class="tag tag--warn">待改密</span>
                  <span v-else class="muted">正常</span>
                </td>
              </tr>
              <tr v-if="!loading && users.length === 0">
                <td colspan="6" class="empty">暂无用户</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <!-- 全部实验 -->
      <section class="panel">
        <h2 class="panel-title">全部归档实验 <span class="count">{{ experiments.length }}</span></h2>
        <div class="table-wrap">
          <table class="table">
            <thead>
              <tr>
                <th>实验编号</th>
                <th>标题</th>
                <th>类型</th>
                <th>归属</th>
                <th>归档时间</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="e in experiments" :key="e.id">
                <td class="mono">{{ e.id }}</td>
                <td class="ellipsis">{{ e.title || '（未命名实验）' }}</td>
                <td class="muted">{{ e.experiment_type || '—' }}</td>
                <td>
                  <span class="tag">{{ e.owner_display_name || e.owner_username || '—' }}</span>
                </td>
                <td class="mono muted">{{ fmtTime(e.created_at) }}</td>
                <td class="num">
                  <button class="btn btn-ghost view-btn" type="button" @click="openExperiment(e.id)">
                    查看
                  </button>
                </td>
              </tr>
              <tr v-if="!loading && experiments.length === 0">
                <td colspan="6" class="empty">暂无归档实验</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </div>
  </main>
</template>

<style scoped>
/* 根元素 .page 的几何由全局 base.css 控制；此处只写面板与表格 */
.head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
  margin-bottom: var(--space-5);
}

.title {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  letter-spacing: -0.01em;
}

.subtitle {
  margin: var(--space-1) 0 0;
  font: var(--text-sm);
  color: var(--text-tertiary);
}

.error {
  margin: 0 0 var(--space-4);
  font: var(--text-sm);
  color: var(--error);
}

.panel {
  margin-bottom: var(--space-5);
  padding: var(--space-4) var(--space-5);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  background: var(--bg-secondary);
}

.panel-title {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin: 0 0 var(--space-3);
  font-size: 15px;
  font-weight: 600;
}

.count {
  padding: 1px var(--space-2);
  border-radius: var(--radius-full);
  background: var(--accent-subtle);
  color: var(--accent);
  font-size: 12px;
  font-weight: 600;
}

.table-wrap {
  overflow-x: auto;
}

.table {
  width: 100%;
  border-collapse: collapse;
  font: var(--text-sm);
}

.table th {
  padding: var(--space-2) var(--space-3);
  border-bottom: 1px solid var(--border-subtle);
  color: var(--text-tertiary);
  font-weight: 500;
  text-align: left;
  white-space: nowrap;
}

.table td {
  padding: var(--space-2) var(--space-3);
  border-bottom: 1px solid var(--border-subtle);
  color: var(--text-primary);
  vertical-align: middle;
}

.table tbody tr:last-child td {
  border-bottom: none;
}

.num {
  text-align: right;
}

.mono {
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 12.5px;
}

.muted {
  color: var(--text-tertiary);
}

.ellipsis {
  max-width: 280px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tag {
  display: inline-flex;
  align-items: center;
  padding: 1px var(--space-2);
  border-radius: var(--radius-full);
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  font-size: 12px;
  white-space: nowrap;
}
.tag--admin {
  background: var(--accent-subtle);
  color: var(--accent);
  font-weight: 500;
}
.tag--warn {
  background: var(--accent-subtle);
  color: var(--accent-hover, var(--accent));
}

.empty {
  padding: var(--space-5) !important;
  text-align: center;
  color: var(--text-tertiary);
}

.view-btn {
  height: 30px;
}
</style>
