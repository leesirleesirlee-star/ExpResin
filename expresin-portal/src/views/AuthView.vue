<script setup>
import { computed, nextTick, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { auth, changePassword, login, register } from '../data/auth.js'
import { useToast } from '../composables/useToast.js'
import { useTheme } from '../composables/useTheme.js'

const router = useRouter()
const route = useRoute()
const { show } = useToast()
const { theme, toggleTheme } = useTheme()

/* mode: login | register | change
   change 有两种触发：URL ?mode=change（守卫强制改密 / 头像菜单主动改密）
   或登录/注册成功后发现带 must_change_password 标记（种子 admin 首登） */
const mode = ref(route.query.mode === 'change' && auth.token ? 'change' : 'login')

const forced = computed(() => mode.value === 'change' && Boolean(auth.user?.must_change_password))
const redirect = computed(() => (typeof route.query.redirect === 'string' ? route.query.redirect : ''))
const expired = computed(() => route.query.reason === 'expired')

const form = reactive({
  username: '',
  displayName: '',
  password: '',
  confirm: '',
  oldPassword: '',
  newPassword: '',
  newConfirm: '',
})
const error = ref('')
const pending = ref(false)

function switchMode(next) {
  /* 方向感知滑动：注册在登录右侧，向前切换从右滑入，后退从左滑入 */
  const ORDER = { login: 0, register: 1, change: 2 }
  formTransition.value = (ORDER[next] ?? 0) >= (ORDER[mode.value] ?? 0) ? 'form-next' : 'form-prev'
  mode.value = next
  error.value = ''
}

/* ---- 表单切换过渡：方向滑动（CSS）+ 高度平滑（WAAPI，新旧表单高度不同） ---- */
const formTransition = ref('form-next')
const formStage = ref(null)
let prevStageH = 0
const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches

function onFormBeforeLeave() {
  const el = formStage.value
  if (el) prevStageH = el.offsetHeight
}

function onFormEnter(enterEl) {
  const stage = formStage.value
  if (!stage || !prevStageH || reduceMotion) return
  nextTick(() => {
    const from = prevStageH
    const to = enterEl.offsetHeight
    prevStageH = 0
    if (!from || !to || from === to) return
    /* 快速连续切换时取消上一轮高度动画，避免 overflow 被提前清掉 */
    stage.getAnimations().forEach((a) => a.cancel())
    stage.style.overflow = 'hidden'
    const anim = stage.animate(
      [{ height: `${from}px` }, { height: `${to}px` }],
      { duration: 250, easing: 'cubic-bezier(0.4, 0, 0.2, 1)' },
    )
    const done = () => {
      stage.style.overflow = ''
    }
    anim.onfinish = done
    anim.oncancel = done
  })
}

function goHome() {
  router.push(redirect.value || { name: 'home' })
}

function afterAuth(user) {
  if (user.must_change_password) {
    mode.value = 'change'
    error.value = ''
    return
  }
  goHome()
}

async function submitLogin() {
  if (pending.value) return
  error.value = ''
  if (!form.username.trim() || !form.password) {
    error.value = '请输入用户名和密码'
    return
  }
  pending.value = true
  try {
    const user = await login(form.username.trim(), form.password)
    afterAuth(user)
  } catch (e) {
    error.value = e.message || '登录失败，请重试'
  } finally {
    pending.value = false
  }
}

async function submitRegister() {
  if (pending.value) return
  error.value = ''
  if (form.password !== form.confirm) {
    error.value = '两次输入的密码不一致'
    return
  }
  pending.value = true
  try {
    const user = await register(form.username.trim(), form.password, form.displayName)
    show(`欢迎，${user.display_name || user.username}`, { tone: 'success' })
    afterAuth(user)
  } catch (e) {
    error.value = e.message || '注册失败，请重试'
  } finally {
    pending.value = false
  }
}

async function submitChange() {
  if (pending.value) return
  error.value = ''
  if (!form.oldPassword || !form.newPassword) {
    error.value = '请输入原密码和新密码'
    return
  }
  if (form.newPassword !== form.newConfirm) {
    error.value = '两次输入的新密码不一致'
    return
  }
  pending.value = true
  try {
    await changePassword(form.oldPassword, form.newPassword)
    show('密码已更新', { tone: 'success' })
    goHome()
  } catch (e) {
    error.value = e.message || '修改失败，请重试'
  } finally {
    pending.value = false
  }
}
</script>

<template>
  <main class="auth">
    <div class="card">
      <!-- 深浅色切换（与顶栏同款，登录页无 AppHeader，需自带入口） -->
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

      <RouterLink to="/welcome" class="brand" aria-label="返回欢迎页">
        <img class="logo" src="/logo.png" alt="ExpResin" />
        <span class="brand-name">ExpResin</span>
      </RouterLink>

      <p v-if="expired" class="notice notice--warn">登录已过期，请重新登录</p>
      <p v-if="forced" class="notice notice--warn">首次登录请先修改初始密码</p>

      <!-- 登录 / 注册 切换（改密模式下隐藏）；.tab-slider 滑动胶囊指示当前页 -->
      <div v-if="mode !== 'change'" class="tabs" role="tablist">
        <span class="tab-slider" :class="{ 'is-right': mode === 'register' }" aria-hidden="true"></span>
        <button
          class="tab"
          :class="{ 'is-active': mode === 'login' }"
          type="button"
          role="tab"
          :aria-selected="mode === 'login'"
          @click="switchMode('login')"
        >
          登录
        </button>
        <button
          class="tab"
          :class="{ 'is-active': mode === 'register' }"
          type="button"
          role="tab"
          :aria-selected="mode === 'register'"
          @click="switchMode('register')"
        >
          注册
        </button>
      </div>

      <!-- 表单区：三个表单同一位置切换，方向滑动 + 高度平滑过渡 -->
      <div ref="formStage" class="form-stage">
        <Transition :name="formTransition" @before-leave="onFormBeforeLeave" @enter="onFormEnter">
          <!-- 登录 -->
          <form v-if="mode === 'login'" key="login" class="form" @submit.prevent="submitLogin">
        <label class="field">
          <span class="label">用户名</span>
          <input v-model="form.username" class="input" type="text" autocomplete="username" placeholder="字母、数字或 _ . -" />
        </label>
        <label class="field">
          <span class="label">密码</span>
          <input v-model="form.password" class="input" type="password" autocomplete="current-password" placeholder="请输入密码" />
        </label>
        <p v-if="error" class="error" role="alert">{{ error }}</p>
        <button class="btn btn-primary btn-liquid submit" type="submit" :disabled="pending">
          {{ pending ? '登录中…' : '登录' }}
        </button>
      </form>

          <!-- 注册（开放注册，注册即登录） -->
          <form v-else-if="mode === 'register'" key="register" class="form" @submit.prevent="submitRegister">
        <label class="field">
          <span class="label">用户名</span>
          <input v-model="form.username" class="input" type="text" autocomplete="username" placeholder="3-32 位字母、数字或 _ . -" />
        </label>
        <label class="field">
          <span class="label">姓名（选填）</span>
          <input v-model="form.displayName" class="input" type="text" autocomplete="name" placeholder="用于界面显示，如：张三" />
        </label>
        <label class="field">
          <span class="label">密码</span>
          <input v-model="form.password" class="input" type="password" autocomplete="new-password" placeholder="至少 6 位" />
        </label>
        <label class="field">
          <span class="label">确认密码</span>
          <input v-model="form.confirm" class="input" type="password" autocomplete="new-password" placeholder="再次输入密码" />
        </label>
        <p v-if="error" class="error" role="alert">{{ error }}</p>
        <button class="btn btn-primary btn-liquid submit" type="submit" :disabled="pending">
          {{ pending ? '注册中…' : '注册并进入' }}
        </button>
      </form>

          <!-- 修改密码（强制或主动） -->
          <form v-else key="change" class="form" @submit.prevent="submitChange">
        <label class="field">
          <span class="label">原密码</span>
          <input v-model="form.oldPassword" class="input" type="password" autocomplete="current-password" placeholder="请输入当前密码" />
        </label>
        <label class="field">
          <span class="label">新密码</span>
          <input v-model="form.newPassword" class="input" type="password" autocomplete="new-password" placeholder="至少 6 位" />
        </label>
        <label class="field">
          <span class="label">确认新密码</span>
          <input v-model="form.newConfirm" class="input" type="password" autocomplete="new-password" placeholder="再次输入新密码" />
        </label>
        <p v-if="error" class="error" role="alert">{{ error }}</p>
        <button class="btn btn-primary btn-liquid submit" type="submit" :disabled="pending">
          {{ pending ? '提交中…' : '确认修改' }}
        </button>
          </form>
        </Transition>
      </div>
    </div>
  </main>
</template>

<style scoped>
/* 视图根元素不设 position / z-index / inset（expresin-ui 规范） */
.auth {
  display: grid;
  place-items: center;
  height: 100%;
  overflow-y: auto;
  padding: var(--space-6) var(--space-4);
}

.card {
  position: relative;
  width: 100%;
  max-width: 380px;
  padding: var(--space-6);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-xl, 16px);
  background: var(--bg-secondary);
  box-shadow: var(--shadow-lg);
}

.theme-toggle {
  position: absolute;
  top: var(--space-4);
  right: var(--space-4);
}

.brand {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  margin-bottom: var(--space-4);
  text-decoration: none;
  color: inherit;
}

.logo {
  display: block;
  width: 40px;
  height: 40px;
}

.brand-name {
  font-size: 17px;
  font-weight: 600;
  letter-spacing: -0.01em;
}

.notice {
  margin: 0 0 var(--space-3);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-md);
  font: var(--text-sm);
  line-height: 1.5;
}
.notice--warn {
  background: var(--accent-subtle);
  color: var(--accent-hover, var(--accent));
}

.tabs {
  position: relative;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2px;
  margin-bottom: var(--space-4);
  padding: 4px;
  border: 1px solid var(--nav-track-border, var(--border-subtle));
  border-radius: var(--radius-full);
  background: var(--nav-track, var(--bg-tertiary));
}

/* 滑动胶囊：跟随当前页左右滑动（几何与 .tabs padding/gap 对应） */
.tab-slider {
  position: absolute;
  top: 4px;
  bottom: 4px;
  left: 4px;
  width: calc(50% - 5px);
  border-radius: var(--radius-full);
  background: var(--nav-slider, var(--bg-secondary));
  box-shadow: var(--shadow-sm);
  pointer-events: none;
  transition: transform var(--duration-normal) var(--ease-standard);
}
.tab-slider.is-right {
  transform: translateX(calc(100% + 2px));
}

.tab {
  position: relative;
  z-index: 1;
  min-height: 32px;
  border: none;
  border-radius: var(--radius-full);
  background: transparent;
  font: var(--text-sm);
  color: var(--text-secondary);
  cursor: pointer;
  transition: color var(--duration-fast) var(--ease-standard);
}
.tab.is-active {
  color: var(--accent);
  font-weight: 500;
}

/* 表单舞台：leave 表单 absolute 脱离布局（与工作台路由过渡同一方案），
   容器高度只由进入表单决定，配合 JS 高度动画——切换不跳动、旧表单不穿帮 */
.form-stage {
  position: relative;
}

/* 方向滑动：前进（登录→注册）新表单从右入，后退从左入 */
.form-next-enter-active,
.form-next-leave-active,
.form-prev-enter-active,
.form-prev-leave-active {
  transition: opacity var(--duration-normal) var(--ease-standard),
    transform var(--duration-normal) var(--ease-standard);
}
/* 离开的旧表单脱离文档流：不再撑高容器（否则高表单在切换瞬间裸露，离开结束时高度骤降跳动） */
.form-next-leave-active,
.form-prev-leave-active {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  z-index: 2;
}
.form-next-enter-from {
  opacity: 0;
  transform: translateX(24px);
}
.form-next-leave-to {
  opacity: 0;
  transform: translateX(-24px);
}
.form-prev-enter-from {
  opacity: 0;
  transform: translateX(-24px);
}
.form-prev-leave-to {
  opacity: 0;
  transform: translateX(24px);
}

.form {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.label {
  font: var(--text-sm);
  font-weight: 500;
  color: var(--text-secondary);
}

.input {
  height: 40px;
  padding: 0 var(--space-3);
  border: 1px solid var(--border-strong, var(--border-subtle));
  border-radius: var(--radius-md);
  background: var(--bg-primary, var(--bg-canvas));
  color: var(--text-primary);
  font: var(--text-sm);
  transition: border-color var(--duration-fast) var(--ease-standard),
    box-shadow var(--duration-fast) var(--ease-standard);
}
.input::placeholder {
  color: var(--text-tertiary);
}
.input:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: var(--focus-ring);
}

.error {
  margin: 0;
  font: var(--text-sm);
  color: var(--error);
}

.submit {
  width: 100%;
  height: 42px;
  margin-top: var(--space-1);
}
</style>
