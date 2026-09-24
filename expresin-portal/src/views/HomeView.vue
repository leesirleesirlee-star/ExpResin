<script setup>
import { onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { loadArchive, session } from '../data/session.js'

const entries = [
  {
    to: '/setup',
    title: '新建实验',
    desc: '实验前：与 Jarvis 对话，录入实验初始信息与方法材料',
    step: '01',
  },
  {
    to: '/recognize',
    title: '数据识别',
    desc: '实验后：上传原始表格，识别列与单位，逐列确认',
    step: '02',
  },
  {
    to: '/archive',
    title: '实验档案',
    desc: '归档：查看规范文档，供后续研究与外部系统调用',
    step: '03',
  },
]

onMounted(loadArchive)
</script>

<template>
  <main class="page">
    <div class="wrap">
      <header class="hero">
        <h1>ExpResin 实验数据工作台</h1>
        <p class="muted">
          把实验记录拆成清晰的三步：实验前录入、实验后识别、归档调用。
          Raw 数据只读，Processed 全程可追溯。
        </p>
      </header>

      <section class="entries">
        <RouterLink v-for="e in entries" :key="e.to" :to="e.to" class="entry">
          <span class="step mono">{{ e.step }}</span>
          <h2>{{ e.title }}</h2>
          <p class="muted">{{ e.desc }}</p>
        </RouterLink>
      </section>

      <section class="recent">
        <header class="section-head">
          <h2>近期实验</h2>
          <RouterLink to="/archive" class="btn btn-ghost">查看全部</RouterLink>
        </header>

        <p v-if="!session.online" class="empty muted">
          后端服务未连接，实验档案暂不可用。启动
          <code class="mono">expresin-pipeline/server</code> 后刷新即可。
        </p>

        <p v-else-if="!session.archive.length" class="empty muted">
          还没有归档的实验。先到「新建实验」录入一次实验的初始信息。
        </p>

        <ul v-else class="list">
          <li v-for="exp in session.archive.slice(0, 5)" :key="exp.id">
            <RouterLink :to="`/archive/${exp.id}`" class="row">
              <span class="rid mono">{{ exp.id }}</span>
              <span class="rtitle">{{ exp.title || '（未命名实验）' }}</span>
              <span class="badge badge-neutral">{{ exp.experiment_type || '—' }}</span>
            </RouterLink>
          </li>
        </ul>
      </section>
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
  gap: var(--space-8);
}

.hero h1 {
  font: var(--text-2xl);
  letter-spacing: var(--tracking-tight);
}
.hero p {
  margin-top: var(--space-3);
  font: var(--text-base);
  max-width: 62ch;
  line-height: 1.6;
}

.entries {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: var(--space-4);
}
.entry {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
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
.entry:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}
.entry .step {
  font-size: 12px;
  color: var(--accent);
}
.entry h2 {
  font: var(--text-lg);
}
.entry p {
  font: var(--text-sm);
  line-height: 1.55;
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-3);
}
.section-head h2 {
  font: var(--text-lg);
}

.empty {
  font: var(--text-sm);
  padding: var(--space-4);
  border: 1px dashed var(--border-strong);
  border-radius: var(--radius-lg);
}

.list {
  list-style: none;
  margin: 0;
  padding: 0;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  overflow: hidden;
  background: var(--bg-secondary);
}
.row {
  display: grid;
  grid-template-columns: 180px minmax(0, 1fr) auto;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  border-bottom: 1px solid var(--border-subtle);
  text-decoration: none;
  color: inherit;
}
.list li:last-child .row {
  border-bottom: none;
}
.row:hover {
  background: var(--bg-tertiary);
}
.rid {
  font-size: 13px;
  color: var(--text-secondary);
}
.rtitle {
  font: var(--text-sm);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

code {
  padding: 2px 6px;
  border-radius: var(--radius-sm);
  background: var(--bg-tertiary);
  font-size: 12px;
}

@media (max-width: 640px) {
  .wrap {
    padding: var(--space-6) var(--space-4) var(--space-8);
    gap: var(--space-6);
  }
  .row {
    grid-template-columns: 1fr;
    gap: var(--space-1);
  }
}
</style>