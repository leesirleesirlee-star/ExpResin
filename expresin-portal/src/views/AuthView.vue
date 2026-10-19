<script setup>
import { computed, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { auth, changePassword, login, register } from '../data/auth.js'
import { useToast } from '../composables/useToast.js'

const router = useRouter()
const route = useRoute()
const { show } = useToast()

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
  mode.value = next
  error.value = ''
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
      <RouterLink to="/welcome" class="brand" aria-label="返回欢迎页">
        <span class="logo" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linejoin="round">
            <path d="M12 3 20 7.5v9L12 21 4 16.5v-9L12 3Z" />
            <path d="M12 12 20 7.5M12 12v9M12 12 4 7.5" />
          </svg>
        </span>
        <span class="brand-name">ExpResin</span>
      </RouterLink>

      <p v-if="expired" class="notice notice--warn">登录已过期，请重新登录</p>
      <p v-if="forced" class="notice notice--warn">首次登录请先修改初始密码</p>

      <!-- 登录 / 注册 切换（改密模式下隐藏） -->
      <div v-if="mode !== 'change'" class="tabs" role="tablist">
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

      <!-- 登录 -->
      <form v-if="mode === 'login'" class="form" @submit.prevent="submitLogin">
        <label class="field">
          <span class="label">用户名</span>
          <input v-model="form.username" class="input" type="text" autocomplete="username" placeholder="字母、数字或 _ . -" />
        </label>
        <label class="field">
          <span class="label">密码</span>
          <input v-model="form.password" class="input" type="password" autocomplete="current-password" placeholder="请输入密码" />
        </label>
        <p v-if="error" class="error" role="alert">{{ error }}</p>
        <button class="btn btn-primary submit" type="submit" :disabled="pending">
          {{ pending ? '登录中…' : '登录' }}
        </button>
      </form>

      <!-- 注册（开放注册，注册即登录） -->
      <form v-else-if="mode === 'register'" class="form" @submit.prevent="submitRegister">
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
        <button class="btn btn-primary submit" type="submit" :disabled="pending">
          {{ pending ? '注册中…' : '注册并进入' }}
        </button>
      </form>

      <!-- 修改密码（强制或主动） -->
      <form v-else class="form" @submit.prevent="submitChange">
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
        <button class="btn btn-primary submit" type="submit" :disabled="pending">
          {{ pending ? '提交中…' : '确认修改' }}
        </button>
      </form>
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
  width: 100%;
  max-width: 380px;
  padding: var(--space-6);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-xl, 16px);
  background: var(--bg-secondary);
  box-shadow: var(--shadow-lg);
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
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  border-radius: var(--radius-md);
  background: var(--accent-subtle);
  color: var(--accent);
}
.logo svg {
  width: 20px;
  height: 20px;
  stroke-width: 1.5;
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
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2px;
  margin-bottom: var(--space-4);
  padding: 4px;
  border: 1px solid var(--nav-track-border, var(--border-subtle));
  border-radius: var(--radius-full);
  background: var(--nav-track, var(--bg-tertiary));
}

.tab {
  min-height: 32px;
  border: none;
  border-radius: var(--radius-full);
  background: transparent;
  font: var(--text-sm);
  color: var(--text-secondary);
  cursor: pointer;
  transition: background var(--duration-fast) var(--ease-standard),
    color var(--duration-fast) var(--ease-standard);
}
.tab.is-active {
  background: var(--nav-slider, var(--bg-secondary));
  color: var(--accent);
  font-weight: 500;
  box-shadow: var(--shadow-sm);
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
