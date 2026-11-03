<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useTheme } from '../composables/useTheme.js'
import { useI18n } from '../composables/useI18n.js'
import LocaleSwitch from '../components/LocaleSwitch.vue'

const router = useRouter()
const route = useRoute()
const { theme, toggleTheme } = useTheme()
const { locale, t } = useI18n()

/* 未登录访问受限页会被守卫送到这里并带 ?redirect=，登录成功后原路返回 */
const redirect = computed(() => (typeof route.query.redirect === 'string' ? route.query.redirect : ''))

function enter() {
  router.push({ name: 'auth', query: redirect.value ? { redirect: redirect.value } : {} })
}

/* ---- 打字机：中央输入框装饰里循环演示 Jarvis 对话录入示例 ---- */
const PROMPT_KEYS = [
  '明天做 Ca²⁺ 批实验，初始浓度 100 mg/L，树脂 0.5 g',
  '识别 10 月 15 日的柱实验数据表，画穿透曲线',
  '三室电渗析第二轮，淡室 Ca²⁺ 浓度换 50 mg/L',
  '导出上周双极膜实验，指导教师模板格式',
]
const PROMPTS = computed(() => PROMPT_KEYS.map((item) => t(item)))

const typed = ref('')
const state = { prompt: 0, char: 0, phase: 'typing' }
let timer = null
const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches

/* 每次进入页面使用不同的相位与周期，让背景光的漂移不呈现固定循环感 */
const ambientFlowStyles = Array.from({ length: 2 }, () => ({
  animationDelay: `${-Math.random() * 30}s`,
  animationDuration: `${30 + Math.random() * 12}s`,
}))

function schedule(ms) {
  timer = window.setTimeout(step, ms)
}

function step() {
  const full = PROMPTS.value[state.prompt]
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
    typed.value = PROMPTS.value[0]
    return
  }
  /* 等输入框入场浮现（--d 580ms + 600ms 动画）基本完成后再开打字 */
  schedule(1100)
})

watch(locale, () => {
  if (reducedMotion) {
    typed.value = PROMPTS.value[0]
    return
  }
  if (timer !== null) window.clearTimeout(timer)
  state.prompt = 0
  state.char = 0
  state.phase = 'typing'
  typed.value = ''
  schedule(260)
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
    <!-- 背景网格与流动光场：独立于内容层 -->
    <div class="grid-field" aria-hidden="true"></div>
    <div class="ambient-lights" aria-hidden="true">
      <span class="ambient-flow ambient-flow--primary" :style="ambientFlowStyles[0]"></span>
      <span class="ambient-flow ambient-flow--accent" :style="ambientFlowStyles[1]"></span>
    </div>

    <!-- 右上角语言与深浅色入口（fixed 相对视口：视图根元素不设 position） -->
    <div class="welcome-actions">
      <LocaleSwitch />
      <button
        class="icon-btn theme-toggle"
        type="button"
        :aria-label="theme === 'dark' ? $t('切换到浅色模式') : $t('切换到深色模式')"
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
    </div>

    <div class="hero">
      <!-- 1. 品牌标识 -->
      <div class="brand reveal" style="--d: 60ms">
        <img class="logo" src="/logo.png" alt="ExpResin" />
        <span class="wordmark">ExpResin</span>
      </div>

      <!-- 2. 公告条 -->
      <p class="announce reveal" style="--d: 200ms">
        <span class="spark" aria-hidden="true">✦</span>
        {{ $t('实验新建 · AI 成长报告 · Jarvis 智能对话 已上线') }}
      </p>

      <!-- 3. 主标题 -->
      <h1 class="headline reveal" style="--d: 340ms">{{ $t('让实验数据 自己归档') }}</h1>

      <!-- 4. 副标题 -->
      <p class="sub reveal" style="--d: 460ms">
        {{ $t('对话录入 · 智能识别 · 规范归档 · 模板导出') }}
      </p>

      <!-- 5. 中央输入框装饰（打字机演示） -->
      <div class="composer reveal" style="--d: 580ms">
        <p class="typing-row" aria-hidden="true">
          <span class="typing-text">{{ typed }}</span><span class="caret"></span>
        </p>
        <div class="composer-bar">
          <div class="chips">
            <span class="chip">{{ $t('对话式录入') }}</span>
            <span class="chip">{{ $t('表格识别') }}</span>
            <span class="chip">{{ $t('规范导出') }}</span>
          </div>
          <button class="send" type="button" :aria-label="$t('进入系统')" @click="enter">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 19V5M5 12l7-7 7 7" />
            </svg>
          </button>
        </div>
      </div>

      <!-- 6. 主 CTA -->
      <div class="cta reveal" style="--d: 720ms">
        <button class="btn cta-btn" type="button" @click="enter">
          {{ $t('进入系统') }}
          <svg class="cta-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M5 12h14M13 6l6 6-6 6" />
          </svg>
        </button>
      </div>

      <!-- 7. 脚注 -->
      <p class="foot reveal" style="--d: 840ms">
        {{ $t('首次使用？进入后可直接注册账号 · 数据仅自己与管理老师可见') }}
      </p>
    </div>
  </main>
</template>

<style scoped>
/* 语言与深浅色入口：fixed 右上角（视图根元素不设 position / z-index / inset） */
.welcome-actions {
  position: fixed;
  top: var(--space-5, 20px);
  right: var(--space-5, 20px);
  z-index: 20;
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
/* 视图根元素不设 position / z-index / inset（expresin-ui 规范：
   过渡几何由 App.vue 的 .page-stage 包装层控制）；网格和流动光场由
   独立的 fixed 装饰层承载，不参与页面布局。
   不用 place-items: center 做垂直居中：内容高于视口时居中对齐会把顶部裁到
   滚动区外的不可达位置（overflow 容器的经典居中 bug）；改为 justify-items: center
   + .hero 上下 auto 外边距「安全居中」——空间够时居中，不够时从顶部起排、完整可滚动。
   scrollbar-gutter: stable：滚动条出现/消失时内容不横向跳动。
   背景 background-attachment: fixed 固定到视口：滚动时背景不随内容重绘，
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
      ellipse 66% 48% at 50% -6%,
      color-mix(in srgb, var(--accent) 7%, transparent),
      transparent 72%
    ),
    linear-gradient(
      to bottom,
      transparent 0%,
      color-mix(in srgb, var(--accent) 2%, transparent) 58%,
      color-mix(in srgb, var(--text-secondary) 3%, transparent) 100%
    );
  background-size: 100% 100%;
  background-attachment: fixed;
}

/* ---- 背景网格：64px 间距，上层清晰并向下淡出，下层模糊渐显 ---- */
.grid-field {
  position: fixed;
  inset: 0;
  z-index: 0;
  overflow: hidden;
  pointer-events: none;
}

.grid-field::before,
.grid-field::after {
  content: '';
  position: absolute;
  inset: -2px;
  background-image:
    linear-gradient(
      to right,
      color-mix(in srgb, var(--text-tertiary) 9%, transparent) 1px,
      transparent 1px
    ),
    linear-gradient(
      to bottom,
      color-mix(in srgb, var(--text-tertiary) 9%, transparent) 1px,
      transparent 1px
    );
  background-size: 64px 64px;
  background-position: center top;
}

.grid-field::before {
  opacity: 0.9;
  mask-image: linear-gradient(
    to bottom,
    #000 0%,
    rgba(0, 0, 0, 0.8) 30%,
    rgba(0, 0, 0, 0.18) 58%,
    transparent 72%
  );
  -webkit-mask-image: linear-gradient(
    to bottom,
    #000 0%,
    rgba(0, 0, 0, 0.8) 30%,
    rgba(0, 0, 0, 0.18) 58%,
    transparent 72%
  );
}

.grid-field::after {
  filter: blur(1.8px);
  opacity: 0.7;
  mask-image: linear-gradient(
    to bottom,
    transparent 26%,
    rgba(0, 0, 0, 0.35) 52%,
    rgba(0, 0, 0, 0.8) 100%
  );
  -webkit-mask-image: linear-gradient(
    to bottom,
    transparent 26%,
    rgba(0, 0, 0, 0.35) 52%,
    rgba(0, 0, 0, 0.8) 100%
  );
}

/* ---- 全屏流动光场：以橙色为主的多色不规则渐变，不使用圆形光斑 ---- */
.ambient-lights {
  position: fixed;
  inset: 0;
  z-index: 0;
  overflow: hidden;
  pointer-events: none;
}

.ambient-flow {
  position: absolute;
  inset: -30%;
  display: block;
  filter: blur(32px);
  will-change: transform, background-position;
  animation-timing-function: ease-in-out;
  animation-iteration-count: infinite;
  animation-direction: alternate;
}

.ambient-flow--primary {
  background:
    radial-gradient(
      ellipse 68% 46% at 22% 16%,
      color-mix(in srgb, var(--accent) 24%, transparent),
      transparent 70%
    ),
    radial-gradient(
      ellipse 52% 58% at 82% 58%,
      color-mix(in srgb, #ff9b63 11%, transparent),
      transparent 72%
    ),
    radial-gradient(
      ellipse 76% 42% at 42% 92%,
      color-mix(in srgb, var(--accent) 9%, transparent),
      transparent 74%
    ),
    conic-gradient(
      from 125deg at 48% 48%,
      transparent 0deg,
      color-mix(in srgb, var(--accent) 9%, transparent) 70deg,
      transparent 140deg,
      color-mix(in srgb, #f2b56f 7%, transparent) 215deg,
      transparent 300deg
    );
  background-size: 145% 145%;
  background-position: 8% 12%;
  opacity: 0.68;
  animation-name: ambient-flow-primary;
}

.ambient-flow--accent {
  inset: -38%;
  background:
    radial-gradient(
      ellipse 46% 64% at 70% 24%,
      color-mix(in srgb, #ffc08f 12%, transparent),
      transparent 70%
    ),
    radial-gradient(
      ellipse 58% 42% at 18% 74%,
      color-mix(in srgb, var(--accent) 10%, transparent),
      transparent 72%
    ),
    linear-gradient(
      112deg,
      transparent 24%,
      color-mix(in srgb, #ff8b53 9%, transparent) 34%,
      transparent 48%,
      color-mix(in srgb, var(--accent) 7%, transparent) 66%,
      transparent 82%
    );
  background-size: 172% 172%;
  background-position: 88% 72%;
  opacity: 0.55;
  animation-name: ambient-flow-accent;
}

@keyframes ambient-flow-primary {
  0% {
    transform: translate3d(-3%, -2%, 0) rotate(-4deg) scale(1.03);
    background-position: 0% 12%;
  }
  38% {
    transform: translate3d(4%, 1%, 0) rotate(2deg) scale(1.08);
    background-position: 48% 52%;
  }
  72% {
    transform: translate3d(1%, 4%, 0) rotate(5deg) scale(1.04);
    background-position: 82% 78%;
  }
  100% {
    transform: translate3d(6%, 2%, 0) rotate(8deg) scale(1.1);
    background-position: 100% 100%;
  }
}

@keyframes ambient-flow-accent {
  0% {
    transform: translate3d(4%, 2%, 0) rotate(5deg) scale(1.05);
    background-position: 92% 78%;
  }
  42% {
    transform: translate3d(-3%, 4%, 0) rotate(1deg) scale(1.1);
    background-position: 58% 42%;
  }
  74% {
    transform: translate3d(-5%, -2%, 0) rotate(-3deg) scale(1.04);
    background-position: 18% 24%;
  }
  100% {
    transform: translate3d(1%, 3%, 0) rotate(-6deg) scale(1.08);
    background-position: 0% 0%;
  }
}

.hero {
  position: relative;
  z-index: 1;
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

:global(html[lang='en']) .headline {
  letter-spacing: -0.02em;
  text-wrap: balance;
}

/* ---- 4. 副标题 ---- */
.sub {
  margin: var(--space-3) 0 0;
  font-size: 14px;
  line-height: 1.5;
  letter-spacing: 0.14em;
  color: var(--text-tertiary);
}

:global(html[lang='en']) .sub {
  letter-spacing: 0.025em;
  text-wrap: balance;
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

/* 「进入系统」（登录注册主按钮）：默认只显示文字与箭头。
   悬停/键盘聚焦时，磨砂玻璃胶囊以中心为轴同时向左右展开；玻璃层单独
   承载背景、边框、高光和背后模糊，避免文字随容器一起缩放。 */
.cta-btn {
  position: relative;
  isolation: isolate;
  min-width: 200px;
  height: 46px;
  gap: var(--space-2);
  padding: 0 var(--space-5);
  border: 0;
  border-radius: var(--radius-full);
  background: transparent;
  box-shadow: none;
  color: var(--text-primary);
  font-size: 15px;
  font-weight: 600;
  transform: translateZ(0); /* GPU 合成层，保证 backdrop-filter 渲染稳定 */
}

.cta-btn::before {
  content: '';
  position: absolute;
  inset: 0;
  z-index: -1;
  border: 1px solid var(--glass-border);
  border-radius: inherit;
  background: var(--glass-bg);
  -webkit-backdrop-filter: blur(var(--glass-blur)) saturate(var(--glass-saturate));
  backdrop-filter: blur(var(--glass-blur)) saturate(var(--glass-saturate));
  box-shadow: var(--shadow-md), var(--glass-edge);
  opacity: 0;
  transform: scaleX(0.04);
  transform-origin: center;
  transition:
    opacity 180ms var(--ease-standard),
    transform 420ms cubic-bezier(0.22, 1, 0.36, 1),
    background var(--duration-fast) var(--ease-standard),
    box-shadow var(--duration-fast) var(--ease-standard);
}

.cta-btn:hover:not(:disabled)::before,
.cta-btn:focus-visible::before {
  opacity: 1;
  transform: scaleX(1);
  background: var(--glass-bg-strong);
  box-shadow: var(--shadow-lg), var(--glass-edge);
}

/* 无悬停能力的触屏设备没有 hover 过程，直接呈现玻璃底以保证可辨识 */
@media (hover: none) {
  .cta-btn::before {
    opacity: 1;
    transform: scaleX(1);
  }
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

@media (prefers-reduced-motion: reduce) {
  .ambient-flow {
    animation: none !important;
    opacity: 0.5;
    will-change: auto;
  }
  .cta-btn::before {
    transition: none;
  }
}

@media (max-width: 560px) {
  .composer {
    padding: var(--space-3) var(--space-3) var(--space-2);
  }
  .sub {
    letter-spacing: 0.08em;
  }
  .ambient-flow {
    filter: blur(24px);
    opacity: 0.48;
  }
}
</style>
