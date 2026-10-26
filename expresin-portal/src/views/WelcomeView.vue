<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useTheme } from '../composables/useTheme.js'

const router = useRouter()
const route = useRoute()
const { theme, toggleTheme } = useTheme()

/* 未登录访问受限页会被守卫送到这里并带 ?redirect=，登录成功后原路返回 */
const redirect = computed(() => (typeof route.query.redirect === 'string' ? route.query.redirect : ''))

function enter() {
  router.push({ name: 'auth', query: redirect.value ? { redirect: redirect.value } : {} })
}

/* ---- 打字机：中央输入框装饰里循环演示 Jarvis 对话录入示例 ---- */
const PROMPTS = [
  '明天做 Ca²⁺ 批实验，初始浓度 100 mg/L，树脂 0.5 g',
  '识别 10 月 15 日的柱实验数据表，画穿透曲线',
  '三室电渗析第二轮，淡室 Ca²⁺ 浓度换 50 mg/L',
  '导出上周双极膜实验，指导教师模板格式',
]

const typed = ref('')
const state = { prompt: 0, char: 0, phase: 'typing' }
let timer = null
const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches

function schedule(ms) {
  timer = window.setTimeout(step, ms)
}

function step() {
  const full = PROMPTS[state.prompt]
  if (state.phase === 'typing') {
    state.char += 1
    typed.value = full.slice(0, state.char)
    if (state.char >= full.length) {
      state.phase = 'holding'
      schedule(2200)
    } else {
      /* 55-115ms 随机间隔，模拟真人敲键节奏 */
      schedule(55 + Math.random() * 60)
    }
  } else if (state.phase === 'holding') {
    state.phase = 'erasing'
    schedule(26)
  } else {
    state.char -= 1
    typed.value = full.slice(0, state.char)
    if (state.char <= 0) {
      state.prompt = (state.prompt + 1) % PROMPTS.length
      state.phase = 'typing'
      schedule(420)
    } else {
      schedule(26)
    }
  }
}

onMounted(() => {
  if (reducedMotion) {
    /* 减弱动效：静态展示第一条示例，不循环 */
    typed.value = PROMPTS[0]
    return
  }
  /* 等输入框入场浮现（--d 580ms + 600ms 动画）基本完成后再开打字 */
  schedule(1100)
})

onBeforeUnmount(() => {
  if (timer !== null) {
    window.clearTimeout(timer)
    timer = null
  }
})
</script>

<template>
  <main class="welcome">
    <!-- 深浅色切换（fixed 相对视口：视图根元素不设 position，见 expresin-ui 规范） -->
    <button
      class="icon-btn theme-toggle"
      type="button"
      :aria-label="theme === 'dark' ? '切换到浅色模式' : '切换到深色模式'"
      @click="toggleTheme"
    >
      <svg v-if="theme === 'dark'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="4" />
        <path d="M12 2v2m0 16v2M4.9 4.9l1.4 1.4m11.4 11.4 1.4 1.4M2 12h2m16 0h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
      </svg>
      <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round">
        <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z" />
      </svg>
    </button>

    <div class="hero">
      <!-- 1. 品牌标识 -->
      <div class="brand reveal" style="--d: 60ms">
        <img class="logo" src="/logo.png" alt="ExpResin" />
        <span class="wordmark">ExpResin</span>
      </div>

      <!-- 2. 公告条 -->
      <p class="announce reveal" style="--d: 200ms">
        <span class="spark" aria-hidden="true">✦</span>
        电化学三分支记录模板 · 账号数据隔离 已上线
      </p>

      <!-- 3. 主标题 -->
      <h1 class="headline reveal" style="--d: 340ms">让实验数据 自己归档</h1>

      <!-- 4. 副标题 -->
      <p class="sub reveal" style="--d: 460ms">对话录入 · 智能识别 · 规范归档 · 模板导出</p>

      <!-- 5. 中央输入框装饰（打字机演示） -->
      <div class="composer reveal" style="--d: 580ms">
        <p class="typing-row" aria-hidden="true">
          <span class="typing-text">{{ typed }}</span><span class="caret"></span>
        </p>
        <div class="composer-bar">
          <div class="chips">
            <span class="chip">对话式录入</span>
            <span class="chip">表格识别</span>
            <span class="chip">规范导出</span>
          </div>
          <button class="send" type="button" aria-label="进入系统" @click="enter">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 19V5M5 12l7-7 7 7" />
            </svg>
          </button>
        </div>
      </div>

      <!-- 6. 主 CTA -->
      <div class="cta reveal" style="--d: 720ms">
        <button class="btn cta-btn" type="button" @click="enter">
          进入系统
          <svg class="cta-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M5 12h14M13 6l6 6-6 6" />
          </svg>
        </button>
      </div>

      <!-- 7. 脚注 -->
      <p class="foot reveal" style="--d: 840ms">首次使用？进入后可直接注册账号 · 数据仅自己与管理老师可见</p>
    </div>
  </main>
</template>

<style scoped>
/* 深浅色切换：fixed 右上角（视图根元素不设 position / z-index / inset） */
.theme-toggle {
  position: fixed;
  top: var(--space-5, 20px);
  right: var(--space-5, 20px);
  z-index: 20;
}
/* 视图根元素不设 position / z-index / inset（expresin-ui 规范：
   过渡几何由 App.vue 的 .page-stage 包装层控制）；背景层次全部用
   background-image 分层绘制，无需定位上下文。
   不用 place-items: center 做垂直居中：内容高于视口时居中对齐会把顶部裁到
   滚动区外的不可达位置（overflow 容器的经典居中 bug）；改为 justify-items: center
   + .hero 上下 auto 外边距「安全居中」——空间够时居中，不够时从顶部起排、完整可滚动。
   scrollbar-gutter: stable：滚动条出现/消失时内容不横向跳动。
   背景 background-attachment: fixed 固定到视口：滚动时网格/光晕不随内容重绘，
   也与各工作台页「背景固定、内容滚动」的观感一致。 */
.welcome {
  display: grid;
  justify-items: center;
  height: 100%;
  overflow-y: auto;
  scrollbar-gutter: stable;
  padding: var(--space-6) var(--space-4);
  background-image:
    radial-gradient(
      ellipse 62% 46% at 50% -4%,
      color-mix(in srgb, var(--accent) 8%, transparent),
      transparent 70%
    ),
    linear-gradient(color-mix(in srgb, var(--text-tertiary) 7%, transparent) 1px, transparent 1px),
    linear-gradient(90deg, color-mix(in srgb, var(--text-tertiary) 7%, transparent) 1px, transparent 1px);
  background-size:
    100% 100%,
    44px 44px,
    44px 44px;
  background-attachment: fixed;
}

.hero {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 100%;
  max-width: 660px;
  margin-block: auto; /* 安全垂直居中（配合 justify-items: center） */
  text-align: center;
}

/* ---- 入场编排：自上而下逐层浮现 ---- */
.reveal {
  animation: welcome-rise var(--duration-slower) var(--ease-decelerate) var(--d, 0ms) both;
  will-change: opacity, transform;
}

@keyframes welcome-rise {
  from {
    opacity: 0;
    transform: translateY(18px);
  }
  to {
    opacity: 1;
    transform: none;
  }
}

/* ---- 1. 品牌 ---- */
.brand {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.logo {
  display: block;
  width: 60px;
  height: 60px;
  filter: drop-shadow(0 4px 14px rgba(0, 0, 0, 0.14));
}

.wordmark {
  font-size: 20px;
  font-weight: 600;
  letter-spacing: -0.01em;
  color: var(--text-primary);
}

/* ---- 2. 公告条 ---- */
.announce {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin: var(--space-5) 0 0;
  padding: 5px var(--space-3);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-full);
  background: var(--bg-secondary);
  font-size: 13px;
  line-height: 1.5;
  color: var(--text-secondary);
}

.spark {
  color: var(--accent);
  font-size: 12px;
}

/* ---- 3. 主标题 ---- */
.headline {
  margin: var(--space-4) 0 0;
  font-size: clamp(30px, 5.2vw, 42px);
  font-weight: 600;
  letter-spacing: 0.1em;
  line-height: 1.3;
  color: var(--text-primary);
}

/* ---- 4. 副标题 ---- */
.sub {
  margin: var(--space-3) 0 0;
  font-size: 14px;
  line-height: 1.5;
  letter-spacing: 0.14em;
  color: var(--text-tertiary);
}

/* ---- 5. 中央输入框装饰 ---- */
.composer {
  width: 100%;
  margin-top: var(--space-6);
  padding: var(--space-4) var(--space-4) var(--space-3);
  border: 1px solid var(--border-subtle);
  border-radius: 20px;
  background: var(--bg-secondary);
  box-shadow: var(--shadow-lg);
  text-align: left;
  transition: border-color var(--duration-normal) var(--ease-standard),
    box-shadow var(--duration-normal) var(--ease-standard);
}
.composer:hover {
  border-color: color-mix(in srgb, var(--accent) 30%, var(--border-subtle));
}

.typing-row {
  margin: 0;
  min-height: calc(1.75em * 2);
  padding: 2px var(--space-1) 0;
  font-size: 15px;
  line-height: 1.75;
  color: var(--text-secondary);
  word-break: break-all;
}

.caret {
  display: inline-block;
  width: 2px;
  height: 1.05em;
  margin-left: 2px;
  vertical-align: -0.15em;
  border-radius: 1px;
  background: var(--accent);
  animation: caret-blink 1.06s steps(2, start) infinite;
}

@keyframes caret-blink {
  0%,
  49% {
    opacity: 1;
  }
  50%,
  100% {
    opacity: 0;
  }
}

.composer-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  margin-top: var(--space-2);
}

.chips {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.chip {
  padding: 4px var(--space-3);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-full);
  background: var(--bg-tertiary);
  font-size: 12.5px;
  color: var(--text-secondary);
  white-space: nowrap;
}

/* 发送键：与主页面（ChatPanel）一致的圆角矩形（squircle）上箭头钮，
   交互也对齐——hover 不提位移（只换色与阴影），按下 scale(0.92)，更跟手 */
.send {
  display: grid;
  place-items: center;
  flex: none;
  width: 40px;
  height: 40px;
  border: none;
  border-radius: var(--radius-lg);
  background: var(--accent);
  color: var(--on-accent);
  cursor: pointer;
  box-shadow: var(--shadow-xs);
  transition: background var(--duration-fast) var(--ease-standard),
    box-shadow var(--duration-fast) var(--ease-standard),
    transform var(--duration-instant) var(--ease-standard);
}
.send svg {
  width: 18px;
  height: 18px;
  stroke-width: 2;
}
.send:hover {
  background: var(--accent-hover, var(--accent));
  box-shadow: var(--shadow-sm);
}
.send:active {
  transform: scale(0.92);
}

/* ---- 6. 主 CTA ---- */
.cta {
  margin-top: var(--space-6);
}

/* 「进入系统」（登录注册主按钮）：中性磨砂玻璃，不使用橙色。
   与顶栏、对话坞共用同一套 glass token——顶部镜面高光渐变 + 暖米半透明底 + 背后模糊，
   深浅色主题与「减少透明度」系统偏好都由 token 层自动适配。 */
.cta-btn {
  min-width: 200px;
  height: 46px;
  gap: var(--space-2);
  padding: 0 var(--space-5);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-full);
  background: var(--glass-bg);
  -webkit-backdrop-filter: blur(var(--glass-blur)) saturate(var(--glass-saturate));
  backdrop-filter: blur(var(--glass-blur)) saturate(var(--glass-saturate));
  box-shadow: var(--shadow-md), var(--glass-edge);
  color: var(--text-primary);
  font-size: 15px;
  font-weight: 600;
  transform: translateZ(0); /* GPU 合成层，保证 backdrop-filter 渲染稳定 */
  transition: background var(--duration-fast) var(--ease-standard),
    border-color var(--duration-fast) var(--ease-standard),
    box-shadow var(--duration-fast) var(--ease-standard),
    transform var(--duration-instant) var(--ease-standard);
}
.cta-btn:hover:not(:disabled) {
  background: var(--glass-bg-strong);
  border-color: var(--border-strong);
  box-shadow: var(--shadow-lg), var(--glass-edge);
}

.cta-arrow {
  width: 17px;
  height: 17px;
  stroke-width: 2;
  transition: transform var(--duration-fast) var(--ease-standard);
}
.cta-btn:hover .cta-arrow {
  transform: translateX(3px);
}

/* ---- 7. 脚注 ---- */
.foot {
  margin: var(--space-4) 0 0;
  font-size: 12.5px;
  color: var(--text-tertiary);
}

@media (max-width: 560px) {
  .composer {
    padding: var(--space-3) var(--space-3) var(--space-2);
  }
  .sub {
    letter-spacing: 0.08em;
  }
}
</style>
