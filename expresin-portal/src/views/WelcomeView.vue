<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const router = useRouter()
const route = useRoute()

/* 未登录访问受限页会被守卫送到这里并带 ?redirect=，登录成功后原路返回 */
const redirect = computed(() => (typeof route.query.redirect === 'string' ? route.query.redirect : ''))

function enter() {
  router.push({ name: 'auth', query: redirect.value ? { redirect: redirect.value } : {} })
}

const features = [
  { title: '对话式录入', desc: '用自然语言向 Jarvis 描述实验安排，自动填入表单' },
  { title: '表格智能识别', desc: '上传原始数据表，逐列确认映射，Raw 永不覆盖' },
  { title: '规范档案导出', desc: '归档生成规范长表，一键导出指导教师模板 Excel' },
]
</script>

<template>
  <main class="welcome">
    <div class="hero">
      <span class="logo" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linejoin="round">
          <path d="M12 3 20 7.5v9L12 21 4 16.5v-9L12 3Z" />
          <path d="M12 12 20 7.5M12 12v9M12 12 4 7.5" />
        </svg>
      </span>
      <h1 class="title">ExpResin</h1>
      <p class="tagline">实验室树脂数据 · 智能记录助手</p>
      <p class="desc">
        从实验前安排到实验后数据归档，一套可追溯的规范流程。
        每位实验员的数据相互隔离，归档仅自己与管理老师可见。
      </p>

      <button class="btn btn-primary enter" type="button" @click="enter">进入系统</button>

      <ul class="features">
        <li v-for="f in features" :key="f.title" class="feature">
          <span class="feature-dot" aria-hidden="true"></span>
          <div>
            <p class="feature-title">{{ f.title }}</p>
            <p class="feature-desc">{{ f.desc }}</p>
          </div>
        </li>
      </ul>

      <p class="foot">首次使用可在登录页直接注册账号；管理员账号由实验室统一发放</p>
    </div>
  </main>
</template>

<style scoped>
/* 视图根元素不设 position / z-index / inset（expresin-ui 规范：
   过渡几何由 App.vue 的 .page-stage 包装层控制） */
.welcome {
  display: grid;
  place-items: center;
  height: 100%;
  overflow-y: auto;
  padding: var(--space-6) var(--space-4);
}

.hero {
  display: flex;
  flex-direction: column;
  align-items: center;
  max-width: 520px;
  text-align: center;
}

.logo {
  display: grid;
  place-items: center;
  width: 64px;
  height: 64px;
  border-radius: var(--radius-lg);
  background: var(--accent-subtle);
  color: var(--accent);
}
.logo svg {
  width: 36px;
  height: 36px;
  stroke-width: 1.5;
}

.title {
  margin: var(--space-4) 0 0;
  font-size: 34px;
  font-weight: 600;
  letter-spacing: -0.02em;
  color: var(--text-primary);
}

.tagline {
  margin: var(--space-2) 0 0;
  font: var(--text-base);
  font-weight: 500;
  color: var(--accent);
}

.desc {
  margin: var(--space-4) 0 0;
  font: var(--text-sm);
  line-height: 1.7;
  color: var(--text-secondary);
}

.enter {
  margin-top: var(--space-6);
  min-width: 180px;
  height: 44px;
  font-size: 15px;
}

.features {
  display: grid;
  gap: var(--space-3);
  width: 100%;
  margin: var(--space-7, 40px) 0 0;
  padding: 0;
  list-style: none;
  text-align: left;
}

.feature {
  display: flex;
  gap: var(--space-3);
  align-items: flex-start;
  padding: var(--space-3) var(--space-4);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  background: var(--bg-secondary);
}

.feature-dot {
  flex: none;
  width: 8px;
  height: 8px;
  margin-top: 7px;
  border-radius: var(--radius-full);
  background: var(--accent);
}

.feature-title {
  margin: 0;
  font: var(--text-sm);
  font-weight: 600;
  color: var(--text-primary);
}

.feature-desc {
  margin: 2px 0 0;
  font: var(--text-xs, 12px);
  line-height: 1.5;
  color: var(--text-tertiary);
}

.foot {
  margin: var(--space-5) 0 0;
  font-size: 12px;
  color: var(--text-tertiary);
}
</style>
