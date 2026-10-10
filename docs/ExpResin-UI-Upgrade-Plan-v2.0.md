# ExpResin UI 升级方案 v2.0

> 范围：`expresin-portal/`（Vue 3 + Vite）前端界面。
> 目标：**保留全部现有功能与业务语义**，让布局更清晰、层级更明确、视觉更简约耐看。
> 方法：`interface-design`（领域探索 → 设计论点 → 层级/深度/状态）+ `ui-ux-pro-max`（Audit → Polish → Rendered Proof）。
> 前置文档：《ExpResin 界面设计规范 v1.0》《docs/design-changelog.md》《docs/ExpResin-PRD.md》。
> 性质：本文是**规划**，不含实现改动。任何偏离既有规范的终态都需要同步写入 `docs/design-changelog.md`（规范 §10.13 硬要求）。

---

## 0. 一页速览（给决策者）

| 维度 | 现状 | 升级后 |
|---|---|---|
| 信息层级 | 工作台页 `h1` 仅 16px，与正文同尺寸；卡片标题与正文同级 | 建立 page / section / card 三级标题刻度，每屏一个明确焦点 |
| 布局 | 存在**两套三栏**（`WorkbenchLayout` 与 `ApiDocsView` 各写一套） | 统一一套三栏骨架 + 一个文档骨架，栏宽走 token |
| 设计系统 | token 完整，但缺控件/z-index/focus/info 令牌；深度策略混合 | 补齐增量 token；**深度策略单一化**：面板走表面色差+极弱边框，浮层走阴影，毛玻璃仅限悬浮层 |
| 交互状态 | 列表页无 loading/error；多面板缺 busy/error；toast 单条无 tone | 全站补齐 default/hover/focus/disabled/loading/empty/error |
| 重复实现 | `.panel-head` 5 处、stats/issue/trace 3 套、字段状态判定 3 套 | 抽 5 个共享结构组件 + 单一状态判定模块 |
| 可访问性 | 触控目标多为 32/36px；tab 无 tablist 语义；缺 aria-current | 触控 ≥44px（最低 40）；补语义与键盘 |
| 死代码 | `style.css`（紫色主题冲突源）、`TopBar.vue`、`HelloWorld.vue`、`Inspector.vue` | 删除或收敛，防止升级误用 |

**结论**：这不是一次换皮，而是一次**收敛与补全**。设计语言（蓝色单强调色、状态色、间距/圆角/动效 token）保持不变；升级集中在**层级、布局统一、状态完整性、结构复用、可访问性**五件事上。

---

## 1. 设计论点（Design Thesis）

按 `ui-ux-pro-max` §2 与 `interface-design` "Intent First"：

- **Audience & job**：树脂/材料实验的科研或实验人员。使用场景是**实验前录入初始条件、实验后上传原始表格并逐列核对、以及事后检索规范档案**。典型动作是"确认"——把机器识别出的原始列/值，人工确认为可追溯的科学记录。使用频率中高，风险高（错误映射会污染科学证据层）。
- **Mode**：operational product / data workbench（操作型数据工作台）+ form flow。
- **Register**：**克制、精确、可信**（restrained / technical / clinical）。不是营销页，不应"表达个性"到干扰数据判读。
- **Dials**：
  - 密度：**偏紧凑**（工具面板 12–16px 内距），但阅读区（规范长表、档案详情）放宽到 16–24px。
  - 视觉方差：**低**——统一结构，靠层级与状态色制造对比，而非装饰。
  - 动效：**低**——仅状态变化，全部 <300ms，尊重 reduced-motion。
  - 数据显著性：**高**——数值用 tabular-nums，单位/置信度必须可见且可溯源。
  - 可访问性风险：**高**——低置信、单位异常、缺失字段是业务核心，不能只靠颜色。
- **System precedence**：完全沿用现有 token（`tokens.css`）、base 组件（`base.css`）、字段状态语义（`.field--*`）。**不引入新色相、新字体栈、新图标语言**。

---

## 2. 领域探索（Domain Exploration）

在动视觉之前，先明确"这个产品属于哪个世界"。

- **Domain（≥5）**：实验记录本、试剂/配方、批次、分析物（analyte）、摩尔浓度与稀释、原始读数、规范记录（canonical record）、证据溯源、链式保管、SOP、仪器面板。
- **Color world（≥5，物理世界取色）**：实验室白瓷与玻璃、不锈钢冷灰、实验木台面暖褐、记录本米白纸、签字墨蓝黑、安全琥珀、树脂半透琥珀、仪器冷光蓝。**注意**：本项目规范锁定单一强调色 `#0066ff` 与状态色，因此"树脂琥珀"**不作为新的界面色相引入**，只作为可选、需审批的品牌点缀方向（见 §9 风险）。
- **Signature（唯一性元素）**：**溯源轨（Provenance Rail）**——每个规范字段旁一条 2px 竖向导轨，向下连到它的原始证据单元（raw cell / evidence / source_ref），顶部是置信度芯片（阈值 0.8）。这是本产品"机器识别 → 人工确认 → 科学证据"的物理化表达，换到任何通用 SaaS 都讲不通。
- **Defaults（3 个必须主动拒绝的默认做法）**：
  1. 默认「灰色系通用后台 + 五张同尺寸卡片平铺」→ 改为**错落节奏**：每屏一个焦点（首页=三步入口，识别页=待确认列）。
  2. 默认「只用字号做层级」→ 改为**字号 + 字重 + 颜色/透明度三杠杆**，并用 tabular-nums。
  3. 默认「颜色区分一切状态」→ 改为**颜色 + 图标/文本 + 形状**三重编码（低置信=琥珀+文本+左色条），满足色盲与规范 §8。

**Swap test**：把本方案的配色换成任意蓝、把布局换成标准模板，是否还认得出？——所以必须靠**溯源轨 + 规范/原始双栏对照 + 确认工作流**这三样"只属于 ExpResin"的结构立住，而不是靠颜色。

---

## 3. 现状体检（Audit Findings）

Audit 为只读结论，均附 `file:line`（根：`expresin-portal/src/`）。严重度 P0=阻断/风险，P1=体验明显受损，P2=打磨。

### 3.1 P0 — 结构性与冲突问题

- **[P0] 死代码主题冲突源**：`src/style.css` 未被任何文件导入（`main.js:2-3` 只导入 `tokens.css`/`base.css`），内含紫色 `--accent:#aa3bff`、根字号 18px、暗底 `#16171d`，与设计系统直接冲突；`components/HelloWorld.vue` 依赖它。另有 `TopBar.vue`、`Inspector.vue` 无 import（孤儿）。→ 删除，避免升级时误用。
- **[P0] 深色模式自动切换失效**：`index.html:2` 固定 `data-theme="light"`，且 `useTheme.js:3-9` 默认写死 `light`，导致 `tokens.css:150-188` 的 `prefers-color-scheme` 规则永不命中——规范 §8.7 要求的系统跟随实际未生效。
- **[P0] 字段状态判定三套并行**：`data/demo.js:219-243`（`fieldState`）、`TemplateForm.vue:61-92`（`statusOf/STATE_*`）、`DynamicForm.vue:23-42`（`toneOf/stateLabel`）规则不完全一致，存在"同一字段在不同面板显示不同状态"的风险——直接威胁 PRD 宪法 #8 / FR-18。
- **[P0] 工作台标题无焦点**：`WorkbenchLayout.vue:126` 的页面 `h1` 仅 `--text-base` 16px，与正文同尺寸；`HomeView.vue:133-149`、`ArchiveView.vue:213-216` 的卡片标题与正文同级。全站"平"，一眼看不出每屏该干什么。

### 3.2 P1 — 体验与一致性

- **[P1] 两套三栏布局**：`WorkbenchLayout.vue` 与 `ApiDocsView.vue:263-270`（240/1fr/360）各写一套，token 布局常量 `--chat-w/--inspector-w`（`tokens.css:101-104`）未被 ApiDocs 复用。
- **[P1] 结构组件五处重复**：`.panel-head`（48px + caps）在 `ChatPanel.vue:105-113`、`DynamicForm.vue:128-136`、`Inspector.vue:134-142`、`MappingInspector.vue:319-327`、`MetadataInspector.vue:257-265`；stats/issue/trace 在三个 Inspector 各写一遍。
- **[P1] 状态覆盖不全**：列表页 `HomeView`/`ArchiveView` 无 loading 骨架、`loadArchive` 失败静默（`HomeView.vue:27`、`ArchiveView.vue:8-30`）；`MappingInspector` 的 resolve 无 busy/error；`StatusBar` 确认按钮无 saving 态且永不禁用。
- **[P1] toast 过弱**：`useToast.js:9-12` 单例单条、无 tone、错误也用 `role="status"`，与规范 §4.8"最多 3 条、4s"不符，长中文错误串（`api.js:46-48`）无法结构化展示。
- **[P1] 触控目标不足**：`AppHeader.vue:138` nav-link 32px、`RecognizeView.vue:404` sheet 输入 28px、`ArchiveDetailView.vue:299,328` 紧凑按钮 32px、`MetadataInspector.vue:372-380` mini 按钮 padding 2px8px、`ApiDocsView.vue:307` nav-item padding 8px。
- **[P1] tab 语义缺失**：`WorkbenchLayout.vue:79-93,205-231` 移动端 tab 无 `role=tablist/tab/tabpanel` 与 `aria-selected`，且无 hover/focus 态。

### 3.3 P2 — 打磨与 token 缺口

- **[P2] token 缺口**：无控件专用 token（`base.css:169-171` 直引 surface/border）、无 z-index 层级 token（全站硬编码 0/1/20/30/60）、缺 `--info-bg`（`base.css:235-238` 用 `--bg-tertiary` 代替）、无 `--focus-ring`、无密度/折叠尺寸 token；系统深色块漏 `--on-accent`（`tokens.css:165-167`）；暗色 `--accent-bg` 为 0.12 而非 10%（`tokens.css:134`）。
- **[P2] 深度策略混合**：同时使用表面色差、边框、四级阴影、毛玻璃四种手段；`.card` 一案叠加三者（`base.css:196-202`）。`interface-design` 明确要求"选一种并贯彻"。
- **[P2] 卡片缺悬停态**：`base.css:196-202` 无 `:hover`，规范 §4.3:260 要求 `shadow-md + translateY(-2px)`。
- **[P2] 硬编码偏离**：`RecognizeView.vue:394` `#64748b` 非 token（暗色对比不足）；面板头 48px 无 token；`MetadataInspector.vue:295` `999px` 应走 `--radius-full`；`App.vue:71` 移动端 48px 硬编码。
- **[P2] 规范未落地项**：模态 4.9 全仓无实现；首屏入场序列 5.3 未实现；侧栏折叠 48px 未实现（changelog §2）；`--tracking-tight` 未落到 2xl+ token（仅 3 处手工声明）。
- **[P2] a11y 细节**：`ApiDocsView` 无 `aria-current`、`<aside>` 无 label、method 靠颜色；`ArchiveDetailView.vue:164-179` stat 非语义、表格缺 `scope/caption`；`DynamicForm.vue:96-99` 可点行仅 Enter 无 Space、无 `aria-selected`。
- **[P2] 数据长度承载**：`region.title` 长句（`demo.js:38,126`）、`evidence` 长文本、`raw_text`（`MetadataInspector.vue:229-231`）溢出与截断策略不统一。

---

## 4. 升级方向（Direction）

一句话：**把"实验室记录本"的秩序感做进现有蓝色设计系统，用层级、密度、溯源结构替代装饰。**

三个可落地的支柱：

1. **每屏一个焦点（One focal point per view）**
   - 首页：三段式入口是焦点，近期实验降级为列表。
   - 录入/识别：待确认列表是焦点，对话与检查面板为辅助。
   - 档案详情：规范记录主体是焦点，统计与导出降级。
   - 做法：焦点元素用 size+weight+color 三杠杆同时抬升，其余刻意降级（更小、更灰、更靠边）。

2. **深度策略单一化（Commit to one depth strategy）**
   - **面板/卡片**：表面色差（`--bg-secondary`）+ **极弱边框**（`--border-subtle`），不用阴影。
   - **浮层**（toast / 下拉 / 模态 / 底部操作条）：用阴影或毛玻璃。
   - **毛玻璃**：仅限"悬浮层"（顶栏 + 三个 Inspector 底部操作条），维持 changelog §1 的边界，不再扩散。
   - 决策写入 changelog。

3. **溯源即结构（Provenance as structure）**
   - 规范字段一律携带"置信度芯片 + 溯源轨"。
   - 档案详情用"规范 / 原始"双栏对照替代平铺长表。
   - 低置信/单位异常用颜色+文本+形状三重编码。

---

## 5. 设计系统升级（增量，不破坏既有值）

原则：**只新增令牌，不改既有颜色/间距/字号/圆角/阴影/动效的值**（`ui-ux-pro-max` Critical Rule 2 与规范 §10.1）。

### 5.1 新增 token（建议追加到 `tokens.css`）

| 类别 | 令牌（建议） | 用途 | 说明 |
|---|---|---|---|
| 控件 | `--control-bg` `--control-border` `--control-focus-ring` | input/select/checkbox 专用 | 让控件可独立调优，替换 `base.css:169-171` 直引 surface |
| 焦点 | `--focus-ring: 0 0 0 3px var(--accent-bg)` | 统一聚焦环 | 替换 `base.css:182` 硬编码 |
| 层级 | `--z-base:0 --z-panel:10 --z-sticky:20 --z-header:30 --z-overlay:40 --z-toast:60` | 消除 20/30/60 硬编码与冲突 | 现 `StatusBar:57` 与 `TopBar:106` 同为 z20 |
| 状态 | `--info-bg: rgba(107,114,128,0.1)` | 补齐 info 10% 背景 | 与 success/warning/error 对齐 |
| 布局 | `--panel-head-h:48px` `--topbar-h-mobile:48px` `--statusbar-h-mobile:44px` `--rail-collapsed-w:48px` | 消除硬编码高度 | 对齐规范 §3.3 |
| 密度 | `--density-compact:1` / `--density-comfortable:1.25` | 显式密度档 | 满足"先定密度"要求 |
| 毛玻璃 | 复用现有 `--glass-*` | — | 已在 tokens.css:41-44 |

### 5.2 语义澄清

- `--accent-subtle`（实色 hex）与 `--accent-bg`（rgba）语义重叠，使用点分裂（`base.css` vs `App.vue:38-39`）→ 文档明确：`--accent-subtle` 用于**填充块**，`--accent-bg` 用于**叠加/聚焦环**。
- 暗色 `--accent-bg` 由 0.12 统一为 0.1，或明确记录"暗色加深为有意为之"并写 changelog。
- 系统深色块与 `[data-theme=dark]` 块合并为单一来源（用 CSS 变量组合或抽出重复段），消除 `--on-accent` 漂移。

### 5.3 深度与圆角规范（写死规则）

- 圆角只许用 `--radius-sm/md/lg/xl/full`，嵌套时遵循 `outer = inner + padding`（`interface-design` 同心圆角）。
- 阴影只在浮层使用；面板/卡片层级靠表面色差 + 极弱边框。
- 字距：2xl 及以上统一 `--tracking-tight`，全大写用 `--tracking-caps`。

---

## 6. 布局升级

### 6.1 统一三栏骨架

- 保留 `WorkbenchLayout.vue` 作为**唯一**工作台骨架（`SetupView`/`RecognizeView` 已用）。
- `ApiDocsView.vue` 抽 `DocsLayout.vue`（或复用骨架的文档变体），栏宽改走 token；不再各写一套。
- 三栏宽度统一 `--chat-w:360` / `--inspector-w:320`（已是 token）。
- 实现规范 §3.3 的**折叠 48px 紧凑态**（当前为 0，changelog §2 记为未达标）：折叠后保留图标条，而非完全消失。

### 6.2 页面壳与标题刻度

建立三级标题刻度（在现有字阶内，不改值）：

| 级别 | token | 用途 |
|---|---|---|
| Page title | `--text-xl`(24/1.3/600) 或 2xl | 页面主标题（如"实验前设置"） |
| Section title | `--text-lg`(20/1.4/500) | 面板/区块标题 |
| Card/row title | `--text-base`(16/500) + `--text-primary` | 卡片标题，靠字重与颜色而非尺寸区分正文 |

- `WorkbenchLayout.vue:126` 的 `h1` 从 `--text-base` 提升到 `--text-xl`。
- `HomeView`/`ArchiveView` 卡片标题升到 `--text-base`/500 且正文/元数据降到 `--text-secondary`。
- 每屏标题区与内容区之间用 `--space-6/7` 留白，制造节奏。

### 6.3 响应式断点统一

现状断点分散：640 / 720 / 820 / 900 / 1024 / 1180 / 1280。收敛为**四断点刻度**（对齐规范 §3.2）：`480 / 768 / 1024 / 1280`，并写进 token 注释，避免各组件各自为政。

---

## 7. 组件升级

### 7.1 抽取共享结构组件（消除重复）

| 新组件 | 取代 | 要点 |
|---|---|---|
| `PanelHead.vue` | 5 处 `.panel-head` | 统一 48px、caps 标题、右侧计数/徽章 |
| `StatGrid.vue` | `Inspector`/`MappingInspector`/`MetadataInspector` | 统一列数与数值层次，数值用 tabular-nums |
| `IssueList.vue` | `Inspector`/`MappingInspector` | 统一问题分组、左色条、按钮 |
| `TraceList.vue` | 三处溯源 `<dl>` | 统一列宽，支持长文本展开 |
| `MiniButton.vue` | `MetadataInspector` mini 按钮 | 触控 ≥40px、含 focus |
| `ConfirmChip.vue` | 三处状态标签 | 单一状态→色调映射 |
| `ProvenanceRail.vue` | 新增（signature） | 置信度芯片 + 2px 竖向导轨 + 证据悬停预览 |
| `ChatMessage.vue` | `ChatPanel` 气泡 | 支持 user/jarvis/error 三态，长文本/代码/表格渲染 |
| `DocsLayout.vue` | `ApiDocsView` 三栏 | 复用骨架语言 |

### 7.2 状态全面补齐

每个交互元素必须有 default / hover / active / focus / disabled；数据区必须有 loading / empty / error。

- 列表页（Home/Archive）：加骨架屏（复用 `base.css` 的 `.skeleton`）与 error 态；`loadArchive` 失败不再静默。
- `StatusBar`：保存/确认加 `saving` 态，进行中禁用并显示进度文案。
- `MappingInspector`：resolve 加 busy + 失败回显，避免"点了没反应"。
- `ChatPanel`：加 empty 引导态；错误消息用独立样式 + `role="alert"`。
- `TemplateForm`：`disabled` 视觉增强（不止 opacity 0.9），并纠正输入框高度至规范值。
- `DynamicForm`：可点行补 Space 键与 `aria-selected`；表头改真实语义。

### 7.3 字段状态单一事实来源

- 把 `demo.fieldState`、`TemplateForm`、`DynamicForm` 三套判定合并为 `src/domain/fieldStatus.js`（或 composable），输出统一的 `{tone, label, icon}`。
- `ConfirmChip`/`TemplateForm`/`DynamicForm`/Inspector 全部消费同一函数，保证同字段全站同状态（PRD 宪法 #8）。
- 单位异常、低置信、缺失的判定规则集中在同一文件并附单元测试。

### 7.4 toast 升级

- `useToast.js` 支持 `{tone: success|error|info|warning, duration}`。
- 队列最多 3 条（规范 §4.8），错误 `role="alert"`，成功 `role="status"`。
- 支持关闭按钮与 hover 暂停；长错误串可换行。

---

## 8. 页面级改造要点

> 全部"保留原功能"，只动层级、布局、状态与可访问性。

- **HomeView**：hero 收窄；三步入口升为焦点（横向 Step 卡 + 清晰的步骤号）；"近期实验"降级；补 loading/error；行内信息用 `dl` 语义。
- **SetupView**：`WorkbenchLayout` 标题升级；`pane-head` 改用 `--panel-head-h`；归档失败时在表单内联提示缺失项（而非仅 toast）。
- **RecognizeView**：拆分顶部 form 栏主次（文件名/工作表/上传分两行）；`#64748b`→token；sheet 输入 ≥40px；列块失败提供就地重试；上传中加 `aria-busy`。
- **ArchiveView**：卡片标题升级并加大与 meta 对比；补 loading/error；搜索框改弹性宽度 + 清空按钮；卡片补 focus-visible。
- **ArchiveDetailView**：加区域锚点/吸顶目录；统计改 `dl`；表格补 `scope/caption`；紧凑按钮 ≥40px；统一横向滚动策略。
- **ApiDocsView**：中栏补端点 `h1`；导航用 `<nav>` + `aria-current`；小屏示例改为可折叠（不再隐藏）；消除 10/11px 与硬编码栏宽；复用 `DocsLayout`。

---

## 9. 必须保留的硬约束 / 可演进边界

### 必须保留（不得改动语义或既有 token 值）

- 《规范 v1.0》§2.1–2.6 的颜色/间距/字号/圆角/阴影/动效**既有值**。
- 单一强调色 + 状态色仅表状态（原则 8）。
- 字段状态视觉语义：已确认 / 待确认 / 低置信 / 单位异常 / 缺失（PRD 宪法 #8、FR-04、FR-18、§8.2）。
- 未经人工确认不得进入科学证据层、字段可溯源（PRD FR-19/20）。
- 对比度 ≥4.5:1、`:focus-visible` 可见（§8.2）、`prefers-reduced-motion` 降级（§8.6）。
- 多页面结构、三栏仅保留在需要的两页（changelog §6）。
- 任何偏离写 `docs/design-changelog.md`（§10.13）。

### 可演进（纯增量）

- 新增控件/焦点/z-index/info/密度/折叠尺寸 token。
- 深度策略单一化、字阶向统一比例收敛（可选）、圆角/阴影使用规则收紧。
- 把散落的 `.grid/.row/.toast/.tabs/.bubble` 抽为共享基础组件。
- 毛玻璃 `--glass-*` 正式纳入规范并限定使用范围。

### 需审批的可选项

- "树脂琥珀"作为**非语义品牌点缀**（如空态插画、登录页），需明确批准并写 changelog；**默认不引入**，以免违反单一强调色约束。

---

## 10. 实施路线图

| 阶段 | 内容 | 优先级 | 预估 |
|---|---|---|---|
| P0 清障 | 删除 `style.css`/`HelloWorld`/`TopBar`/`Inspector` 死代码；修复深色模式自动切换；收敛字段状态判定 | 阻断 | S |
| P1 系统层 | 补 token（控件/焦点/z-index/info/密度）；深度策略决策并写 changelog；统一三栏骨架；标题刻度 | 高 | M |
| P1 组件层 | 抽 `PanelHead/StatGrid/IssueList/TraceList/MiniButton/ConfirmChip/ChatMessage/DocsLayout` | 高 | L |
| P1 状态层 | 全站 loading/empty/error；`StatusBar` saving；`MappingInspector` busy/error；toast 队列+tone | 高 | M |
| P2 页面层 | 六个页面逐页应用焦点、层级、密度、响应式断点统一 | 中 | L |
| P2 签名层 | `ProvenanceRail` + 规范/原始双栏对照；档案锚点目录 | 中 | M |
| P2 打磨层 | 触控 ≥44、tab 语义、表格语义、长文本展开、同心圆角、tabular-nums | 中 | M |
| P3 规范落地 | 模态 4.9、首屏入场 5.3、（可选）48px 折叠（本方案 P1 已纳入） | 低 | S–M |

> token 名与组件名均为建议，落地时以代码评审为准。每个阶段结束需有 rendered proof（见 §11）。

---

## 11. 验收与验证（Rendered Proof）

按 `ui-ux-pro-max` §5 与 `interface-design` "The checks"：

- **渲染证据**：`npm run dev` 启动，桌面（≥1280）与移动（≤480）各截一张；核对无空白、无重叠、无截断、无对比度不足、无 focus 丢失、动画遵守 reduced-motion。可复用 DeepWorks 内置浏览器。
- **Swap test**：把配色换任意蓝、布局换标准模板，是否仍能认出 ExpResin？靠溯源轨与确认流立住才算过。
- **Squint test**：眯眼后层级仍可读、无刺眼元素。
- **Signature test**：能指出 ≥5 处溯源轨/置信度芯片/双栏对照的落点。
- **Token test**：CSS 变量应与产品世界相关（本次不新增色相则以现有语义命名为准）。
- **一致性核对**：逐条对照《规范 v1.0》§2–§8 与 `design-changelog.md`，确认偏离项均已记录。
- **可访问性**：键盘走查（Tab/Enter/Space/Esc）、对比度抽查、`aria-current/selected`、触控目标 ≥44（最低 40）。

---

## 12. 风险与对策

| 风险 | 影响 | 对策 |
|---|---|---|
| 字段状态合并改变既有视觉 | 高（业务核心） | 合并逻辑先与规范 §4.6 逐项对照，保留原色调映射；加单测；灰度先走识别页 |
| 深度策略单一化导致某些层级不可见 | 中 | 先做一屏 before/after 验证再推广；弱边框 opacity 可调 |
| 统一三栏影响 ApiDocs 阅读体验 | 中 | `DocsLayout` 保留其独立栏宽，只共享语言不强行同宽 |
| 删除"死代码"误删 | 中 | 删除前全仓 grep 二次确认 import；保留 git 历史 |
| 引入新 token 与规范字面冲突 | 低 | 全部按"增量"处理并写 changelog；不改既有值 |
| 深色模式修复改变默认外观 | 中 | 明确产品对"系统跟随"的期望；提供显式 light/dark/auto 三态 |

---

## 附录 A：文件级改动清单（速查）

| 文件 | 动作 |
|---|---|
| `src/style.css` | 删除（死代码 + 主题冲突） |
| `src/components/HelloWorld.vue`、`TopBar.vue`、`Inspector.vue` | 删除（无引用） |
| `src/styles/tokens.css` | 增量 token；合并重复深色块；文档化 accent 语义 |
| `src/styles/base.css` | 控件走新 token；`.card` 补 hover/focus；深度策略收紧；`.grid/.row` 抽离 |
| `src/composables/useTheme.js` | 修复默认与系统跟随；localStorage 容错 |
| `src/composables/useToast.js` | 队列 + tone + 关闭 |
| `src/domain/fieldStatus.js`（新） | 单一字段状态判定 |
| `src/layouts/WorkbenchLayout.vue` | 标题刻度、48px 折叠、tab 语义、高度 token |
| `src/layouts/DocsLayout.vue`（新） | 取代 ApiDocs 自建三栏 |
| `src/components/*`（新 9 个） | PanelHead / StatGrid / IssueList / TraceList / MiniButton / ConfirmChip / ProvenanceRail / ChatMessage |
| `src/views/*.vue` | 逐页应用焦点、层级、状态、响应式 |
| `docs/design-changelog.md` | 记录深度策略、token 增量、折叠态、可选方向等全部偏离 |
