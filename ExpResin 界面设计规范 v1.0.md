# ExpResin 界面设计规范 v1.0

> 本规范继承《第一轮基准：ExpResin 项目宪法》与《项目计划书 v2.1》。  
> 用于指导 AI Agent 设计 ExpResin 的 PortalJarvis 页面与 API 文档页面。  
> 设计目标：**极简、科技感、符合人机交互基本逻辑**，参考 OpenAI 与 Apple 的设计语言。  
> 本规范为可执行文件，AI Agent 必须严格遵循以下所有 token、尺寸、动效和布局规则。

---

## 一、设计原则

1. **内容优先**：界面为内容服务，装饰最小化。
2. **减少认知负荷**：一屏一件事，一屏一个主行动。
3. **物理隐喻**：可点击元素必须有可点击感（阴影、悬停、按压反馈）。
4. **清晰优于聪明**：不要隐藏关键操作，不做炫技式交互。
5. **有目的的动效**：每个动画必须解释状态变化，禁止装饰性动画。
6. **高对比可访问性**：文字对比度 ≥ 4.5:1，交互元素 ≥ 3:1。
7. **一致性**：同一语义在全站使用同一组件、同一颜色、同一动效。
8. **克制**：颜色不超过 1 个强调色 + 3 个状态色；圆角不超过 3 种；阴影不超过 3 级。

---

## 二、设计 Token

### 2.1 颜色

| Token | Light | Dark | 用途 |
|---|---|---|---|
| `--bg-primary` | #FFFFFF | #0A0A0A | 页面背景 |
| `--bg-secondary` | #FAFAFA | #141414 | 卡片、面板 |
| `--bg-tertiary` | #F5F5F5 | #1F1F1F | 输入框、代码块 |
| `--text-primary` | #0D0D0D | #F5F5F5 | 主文字 |
| `--text-secondary` | #6B6B6B | #A0A0A0 | 次要文字 |
| `--text-tertiary` | #9A9A9A | #6B6B6B | 占位符、禁用 |
| `--border-subtle` | #E5E5E5 | #1F1F1F | 分隔线 |
| `--border-strong` | #D4D4D4 | #2A2A2A | 输入框边框 |
| `--accent` | #0066FF | #3B82F6 | 主强调色 |
| `--accent-hover` | #0052CC | #2563EB | 悬停 |
| `--accent-subtle` | #EBF2FF | #1E2A4A | 强调背景 |
| `--success` | #10B981 | #34D399 | 成功 |
| `--warning` | #F59E0B | #FBBF24 | 警告、低置信度 |
| `--error` | #EF4444 | #F87171 | 错误、单位异常 |
| `--info` | #6B7280 | #9CA3AF | 中性提示 |

规则：
- 强调色全站只用一个。
- 状态色只用于状态，不用于装饰。
- 低置信度 = warning，单位异常 = error，确认成功 = success。

### 2.2 字体

| Token | 值 | 用途 |
|---|---|---|
| `--font-sans` | Inter, SF Pro Text, -apple-system, sans-serif | 全站 |
| `--font-mono` | JetBrains Mono, SF Mono, monospace | 代码、数据、实验 ID |
| `--text-xs` | 12px / 1.4 / 400 | 辅助标签 |
| `--text-sm` | 14px / 1.5 / 400 | 正文、按钮 |
| `--text-base` | 16px / 1.5 / 400 | 主正文 |
| `--text-lg` | 20px / 1.4 / 500 | 小标题 |
| `--text-xl` | 24px / 1.3 / 600 | 标题 |
| `--text-2xl` | 32px / 1.2 / 600 | 页面标题 |
| `--text-3xl` | 48px / 1.1 / 700 | 首屏标题 |
| `--text-4xl` | 64px / 1.05 / 700 | 品牌标题 |

字距：
- `--text-2xl` 及以上：`-0.02em`
- 正文：`0`
- 全大写标签：`0.05em`

### 2.3 间距

基准网格：**8px**

| Token | 值 |
|---|---|
| `--space-1` | 4px |
| `--space-2` | 8px |
| `--space-3` | 12px |
| `--space-4` | 16px |
| `--space-5` | 24px |
| `--space-6` | 32px |
| `--space-7` | 48px |
| `--space-8` | 64px |
| `--space-9` | 96px |
| `--space-10` | 128px |

规则：
- 组件内部间距用 `space-1` 到 `space-4`。
- 组件之间用 `space-5` 到 `space-6`。
- 区块之间用 `space-7` 到 `space-8`。
- 首屏用 `space-9` 到 `space-10`。

### 2.4 圆角

| Token | 值 | 用途 |
|---|---|---|
| `--radius-sm` | 6px | 标签、徽章 |
| `--radius-md` | 8px | 按钮、输入框 |
| `--radius-lg` | 12px | 卡片、面板 |
| `--radius-xl` | 16px | 大卡片、模态 |
| `--radius-full` | 999px | 头像、胶囊按钮 |

规则：
- 全站不超过这 5 种。
- 同一层级组件使用同一圆角。

### 2.5 阴影

| Token | 值 | 用途 |
|---|---|---|
| `--shadow-xs` | 0 1px 2px rgba(0,0,0,0.04) | 输入框 |
| `--shadow-sm` | 0 2px 8px rgba(0,0,0,0.06) | 卡片 |
| `--shadow-md` | 0 8px 24px rgba(0,0,0,0.08) | 浮层、下拉 |
| `--shadow-lg` | 0 16px 48px rgba(0,0,0,0.12) | 模态、对话框 |

规则：
- Dark 模式下阴影透明度减半。
- 不使用彩色阴影。
- 悬停时阴影最多升一级。

### 2.6 动效

| Token | 值 | 用途 |
|---|---|---|
| `--ease-standard` | cubic-bezier(0.4, 0, 0.2, 1) | 通用 |
| `--ease-decelerate` | cubic-bezier(0, 0, 0.2, 1) | 进入 |
| `--ease-accelerate` | cubic-bezier(0.4, 0, 1, 1) | 退出 |
| `--ease-spring` | cubic-bezier(0.34, 1.56, 0.64, 1) | 弹性反馈 |
| `--duration-instant` | 100ms | 微反馈 |
| `--duration-fast` | 150ms | 悬停、按压 |
| `--duration-normal` | 250ms | 展开、切换 |
| `--duration-slow` | 400ms | 页面转场 |
| `--duration-slower` | 600ms | 首屏入场 |

规则：
- 悬停、按压用 `duration-fast`。
- 面板展开用 `duration-normal`。
- 页面切换用 `duration-slow`。
- 首屏元素依次入场用 `duration-slower` + stagger 50ms。
- 禁止 `linear`。
- 禁止超过 600ms 的动画。

---

## 三、布局系统

### 3.1 栅格

- 12 列栅格。
- 最大内容宽度：1440px。
- 侧边留白：桌面 64px，平板 32px，手机 16px。
- 列间距：24px。

### 3.2 断点

| 断点 | 宽度 | 布局 |
|---|---|---|
| Mobile | < 640px | 单列 |
| Tablet | 640–1024px | 单列或双列 |
| Desktop | 1024–1440px | 三栏 |
| Wide | > 1440px | 三栏 + 居中 |

### 3.3 PortalJarvis 三栏布局

```text
┌─────────────────────────────────────────────────────────────┐
│  Top Bar: Logo | Project | User | Theme | API Docs          │
├──────────────┬────────────────────────────┬─────────────────┤
│              │                            │                 │
│  Chat Panel  │      Dynamic Form          │  Inspector      │
│  360px       │      flex-1                │  320px          │
│              │                            │                 │
│  - 对话消息   │  - 按 Sheet 分组            │  - 缺失项        │
│  - 输入框     │  - 字段实时更新             │  - 字段溯源      │
│  - 上传按钮   │  - 低置信度高亮             │  - 置信度        │
│              │  - 单位异常标红             │  - 单位校验      │
│              │                            │  - 确认按钮      │
│              │                            │                 │
├──────────────┴────────────────────────────┴─────────────────┤
│  Status Bar: 实验ID | 状态 | 最后保存时间 | 保存按钮          │
└─────────────────────────────────────────────────────────────┘
```

尺寸：
- Top Bar 高度：56px。
- Status Bar 高度：48px。
- Chat Panel：固定 360px，可折叠至 48px。
- Inspector：固定 320px，可折叠至 48px。
- Dynamic Form：自适应。
- 三栏间距：1px 分隔线 + `--border-subtle`。

移动端：
- 三栏折叠为 Tab 切换：Chat / Form / Inspector。
- Top Bar 高度：48px。
- Status Bar 高度：44px。

---

## 四、组件规范

### 4.1 按钮

#### Primary Button
- 高度：40px
- 内边距：0 16px
- 圆角：`--radius-md`
- 背景：`--accent`
- 文字：`--text-sm`，500，白色
- 悬停：`--accent-hover` + 阴影升一级
- 按压：`transform: scale(0.98)`
- 禁用：透明度 0.4，`cursor: not-allowed`
- 聚焦：2px `--accent` outline + 2px offset

#### Secondary Button
- 高度：40px
- 内边距：0 16px
- 圆角：`--radius-md`
- 背景：透明
- 边框：1px `--border-strong`
- 文字：`--text-primary`
- 悬停：背景 `--bg-tertiary`
- 按压：`scale(0.98)`

#### Ghost Button
- 高度：36px
- 内边距：0 12px
- 背景：透明
- 文字：`--text-secondary`
- 悬停：背景 `--bg-tertiary`，文字 `--text-primary`

#### Icon Button
- 尺寸：36x36px
- 圆角：`--radius-md`
- 图标：20x20px，stroke 1.5px
- 悬停：背景 `--bg-tertiary`

#### Touch Target
- 移动端所有可点击元素：最小 44x44px。

### 4.2 输入框

- 高度：40px
- 内边距：0 12px
- 圆角：`--radius-md`
- 边框：1px `--border-strong`
- 背景：`--bg-tertiary`
- 文字：`--text-base`
- 占位符：`--text-tertiary`
- 聚焦：边框 `--accent`，外发光 0 0 0 3px `--accent-subtle`
- 错误：边框 `--error`
- 禁用：背景 `--bg-secondary`，文字 `--text-tertiary`

### 4.3 卡片

- 内边距：24px
- 圆角：`--radius-lg`
- 背景：`--bg-secondary`
- 边框：1px `--border-subtle`
- 阴影：`--shadow-sm`
- 悬停：阴影 `--shadow-md`，`transform: translateY(-2px)`，`duration-fast`

### 4.4 对话气泡

#### Jarvis 消息
- 背景：`--bg-tertiary`
- 圆角：`--radius-lg`，左上角 `--radius-sm`
- 内边距：12px 16px
- 最大宽度：80%
- 文字：`--text-base`

#### 用户消息
- 背景：`--accent`
- 文字：白色
- 圆角：`--radius-lg`，右上角 `--radius-sm`
- 内边距：12px 16px
- 最大宽度：80%
- 对齐：右

#### 入场动画
- 从下方 8px 淡入
- `duration-normal` + `ease-decelerate`

### 4.5 流式输出指示器

- 三点脉冲：三个 6px 圆点，间距 4px
- 动画：每个点依次 `opacity 0.3 → 1 → 0.3`，周期 1.2s
- 颜色：`--text-secondary`

### 4.6 字段状态

| 状态 | 视觉 |
|---|---|
| 已确认 | 左边框 2px `--success` |
| 低置信度 | 背景 `--warning` 10% + 左边框 2px `--warning` |
| 单位异常 | 背景 `--error` 10% + 左边框 2px `--error` |
| 缺失 | 虚线边框 + 占位符 |
| 待确认 | 左边框 2px `--accent` |

### 4.7 徽章

- 高度：20px
- 内边距：0 8px
- 圆角：`--radius-full`
- 字号：`--text-xs`，500
- 变体：success / warning / error / info / neutral

### 4.8 Toast

- 位置：右下角，距边缘 24px
- 宽度：320px
- 圆角：`--radius-lg`
- 阴影：`--shadow-lg`
- 入场：从右侧 16px 滑入 + 淡入，`duration-normal`
- 自动消失：4s
- 最多同时 3 条

### 4.9 模态

- 背景：`rgba(0,0,0,0.4)` + `backdrop-filter: blur(8px)`
- 容器：最大宽度 560px，圆角 `--radius-xl`，阴影 `--shadow-lg`
- 入场：`scale(0.96) → scale(1)` + 淡入，`duration-normal`
- 关闭：Esc 键、点击遮罩、关闭按钮

---

## 五、特效规范

### 5.1 允许的特效

| 特效 | 用途 | 实现 |
|---|---|---|
| Backdrop Blur | 模态、浮层、Top Bar | `backdrop-filter: blur(12px)` |
| 微妙渐变 | 首屏背景 | 径向渐变，透明度 ≤ 0.1 |
| 噪点纹理 | 首屏背景 | SVG noise，透明度 ≤ 0.03 |
| 悬停浮起 | 卡片、按钮 | `translateY(-2px)` + 阴影升级 |
| 按压缩放 | 所有可点击元素 | `scale(0.98)` |
| 流式光标 | Jarvis 输出中 | 2px 竖线，闪烁 1s |
| 骨架屏 | 数据加载 | 渐变扫光，1.5s 循环 |
| 脉冲 | 状态指示 | `opacity` 或 `scale` 循环 |
| 数字滚动 | 统计数字 | 200ms 缓动 |
| 图表入场 | 图表首次渲染 | 路径绘制 600ms |

### 5.2 禁止的特效

- 粒子背景（除非透明度 ≤ 0.02）
- 视差滚动
- 3D 翻转
- 彩虹渐变
- 发光霓虹
- 自动播放视频
- 弹跳动画超过 1 次
- 任何超过 600ms 的动画
- 任何 `linear` 缓动

### 5.3 首屏入场序列

```text
0ms    背景淡入
100ms  Logo 淡入 + 上移 8px
200ms  标题淡入 + 上移 8px
300ms  副标题淡入 + 上移 8px
400ms  主按钮淡入 + 上移 8px
500ms  次按钮淡入 + 上移 8px
```

总时长：600ms。

---

## 六、Top Bar 规范

- 高度：56px（桌面）/ 48px（移动）
- 背景：`--bg-primary` + `backdrop-filter: blur(12px)`
- 底部边框：1px `--border-subtle`
- 左侧：Logo 24x24px + 项目名 `--text-sm` 500
- 中间：当前 Project 名称，点击可切换
- 右侧：主题切换、API Docs 链接、用户头像 32x32px
- 滚动时：背景从透明变为 `--bg-primary` + 阴影 `--shadow-xs`

---

## 七、Status Bar 规范

- 高度：48px
- 背景：`--bg-secondary`
- 顶部边框：1px `--border-subtle`
- 左侧：实验 ID（mono 字体）+ 状态徽章
- 中间：最后保存时间
- 右侧：保存按钮（Primary）+ 确认按钮（Secondary）

---

## 八、可访问性

1. 所有交互元素可通过 Tab 聚焦。
2. 聚焦状态必须可见：2px `--accent` outline + 2px offset。
3. 所有图标按钮必须有 `aria-label`。
4. 所有表单字段必须有 `label`。
5. 颜色对比度 ≥ 4.5:1。
6. 支持 `prefers-reduced-motion`：关闭所有非必要动画。
7. 支持 `prefers-color-scheme`：自动切换 Light / Dark。
8. 键盘快捷键：
   - `Cmd/Ctrl + K`：打开命令面板
   - `Cmd/Ctrl + S`：保存草稿
   - `Cmd/Ctrl + Enter`：发送消息
   - `Esc`：关闭模态

---

## 九、API 文档页面规范

- 左侧：导航树，宽度 240px。
- 中间：内容区，最大宽度 800px。
- 右侧：代码示例，宽度 360px，可折叠。
- 代码块：
  - 背景 `--bg-tertiary`
  - 圆角 `--radius-md`
  - 内边距 16px
  - 字体 `--font-mono`，`--text-sm`
  - 右上角复制按钮，悬停显示
- 请求方法徽章：
  - GET：`--success`
  - POST：`--accent`
  - PUT：`--warning`
  - DELETE：`--error`
- 响应示例：可折叠 JSON 树。

---

## 十、给 AI Agent 的直接指令

设计 ExpResin 页面时，必须：

1. 严格遵守本规范的所有 token，不得自定义颜色、字号、间距。
2. 优先使用规范中的组件，不得自创组件。
3. 每个动画必须解释状态变化，禁止装饰性动画。
4. 保持三栏布局，移动端折叠为 Tab。
5. 所有交互元素必须有悬停、按压、聚焦、禁用四态。
6. 所有可点击元素必须符合最小尺寸。
7. 所有文字必须符合对比度要求。
8. 所有图标必须使用 1.5px stroke 线性图标。
9. 所有页面必须支持 Light / Dark 模式。
10. 所有页面必须支持 `prefers-reduced-motion`。
11. 不得使用规范禁止的特效。
12. 首屏入场序列必须按规范执行。
13. 任何偏离本规范的设计，必须写入 ChangeLog 并说明理由。

---

## 十一、结论

本规范定义了 ExpResin 的视觉语言、交互逻辑、组件系统和动效规则。  
AI Agent 必须严格遵循本规范，产出极简、科技感、符合人机交互基本逻辑的界面。  
后续任何设计变更，必须更新本规范版本号并写入 ChangeLog。