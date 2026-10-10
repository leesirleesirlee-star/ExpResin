# ExpResin 设计 ChangeLog

> 依据《ExpResin 界面设计规范 v1.0》第 10.13 条：
> “任何偏离本规范的设计，必须写入 ChangeLog 并说明理由。”

---

## 2026-09-19 · PortalJarvis 三栏工作台首版实现

### 1. 毛玻璃（backdrop-filter）使用范围扩大

- **规范原文**：5.1 仅允许「模态、浮层、Top Bar」使用 `backdrop-filter: blur(12px)`。
- **实现**：将毛玻璃 token 化（`--glass-bg` / `--glass-bg-strong` / `--glass-border` / `--glass-blur`），
  应用于 Top Bar 与 Inspector 底部操作条。
- **理由**：用户明确要求 ChatGPT 风格的毛玻璃观感。
- **风险控制**：
  - 模糊半径仍统一为 12px，未引入第二档模糊；
  - 毛玻璃只用于「悬浮于内容之上」的层级（顶栏、操作条），未用于正文阅读区；
  - 深色模式下 glass 背景不透明度提升至 0.7 / 0.88，确保文字对比度 ≥ 4.5:1。

### 2. 侧栏折叠行为偏差（未达标）

- **规范原文**：3.3 要求 Chat Panel / Inspector「可折叠至 48px」。
- **实现**：当前折叠为 **0（隐藏）**，未实现 48px 紧凑竖条。
- **理由**：48px 竖条需要面板内部的紧凑态布局（图标 + 竖排标签 + 悬浮展开），属独立设计任务。
- **后续**：列为 P1，补齐后同步更新规范版本号。

### 3. 新增「列映射表」组件

- **规范原文**：第四章组件清单中未定义表格/映射表。
- **实现**：新增 `.row` 网格行，展示
  `列字母 | 原始表头 | → | 标准字段 | 值输入 | 置信度 | 状态`。
- **理由**：PortalJarvis 的核心任务是「逐列确认映射」，表格是认知负荷最低的表达形式。
- **约束**：完全复用规范既有 token（`field--*` 状态色条、`.badge`、`.input`、`--space-*`），
  未新增任何颜色、字号、间距令牌。

### 4. 新增颜色令牌说明（非新色相）

- **新增**：`--warning-bg` / `--error-bg` / `--accent-bg` / `--success-bg`（状态色 10% 透明背景）、`--overlay`。
- **理由**：规范 4.6 已明确要求「背景 `--warning` 10% / `--error` 10%」，但未给出对应令牌。
  本次仅把规范中隐含的色值显式 token 化，**未引入任何新色相**。

### 5. 尚未实现的规范项（待办清单）

| 规范条目 | 状态 | 说明 |
|---|---|---|
| 5.3 首屏入场序列 | 未实现 | 当前无独立首屏（直接进入工作台） |
| 4.8 Toast 堆叠管理 | 部分实现 | 已实现单条 + 4s 自动消失，未实现「最多同时 3 条」 |
| 4.9 模态 | 未实现 | 暂无使用场景 |
| 8.8 键盘快捷键 | 部分实现 | 仅 Enter 发送；`Cmd/Ctrl+K` 命令面板、`Cmd/Ctrl+S` 保存待实现 |
| 九、API 文档页面 | 未开始 | 属独立页面任务 |
| 5.1 骨架屏 | 部分实现 | 样式类已提供，尚未接入真实异步加载 |

---

## 2026-09-19 · 多页面重构与实验生命周期对齐

### 6. 从单页三栏扩展为多页面工作台（偏离规范 3.3）

- **规范原文**：3.3 只定义了 PortalJarvis 三栏布局。
- **实现**：拆分为 5 个页面
  | 路由 | 页面 | 职责 |
  |---|---|---|
  | `/` | 工作台首页 | 概览、三步入口、近期实验 |
  | `/setup` | 实验前 · 新建实验 | Jarvis 对话 + 初始信息表单 |
  | `/recognize` | 实验后 · 数据识别 | 上传 → 识别 → 逐列确认 |
  | `/archive` | 实验档案 | 规范文档检索与调用 |
  | `/api-docs` | API 文档 | 接口契约（规范第九章） |
- **理由**：PRD 第 8 章与推进规划 v2.0 要求覆盖「实验前录入 → 实验后识别 → 归档调用」
  的完整生命周期，全部堆在单页会造成认知负荷过高，违背规范原则 2「一屏一件事」。
- **保留**：三栏布局仅用于真正需要「对话 + 表单 + 检查」的两个页面。
- **约束**：未新增任何颜色、字号、间距令牌。

### 7. 树脂型号统一加「树脂」前缀

- 树脂型号展示为「树脂 A600」「树脂 C104」，避免与离子（SO4/Cl）、样品编号混淆。
- 实现：模板 `experiment_template_v1.json` 的 `value_labels`，保持单一数据源。

### 8. 新增设计元素（均复用既有令牌）

- **页面工具条（workbar，48px）**：页面标题 + 阶段进度（实验前/实验后/归档）+ 面板折叠。
- **实验档案卡片与规范文档表格**：复用 `--radius-lg`、`--shadow-sm`、`--bg-secondary`。
- **API 文档三栏**：240px 导航树 / 最大 800px 内容 / 360px 代码示例，符合规范第九章。

### 9. 仍未实现的规范项（滚动待办）

| 条目 | 来源 | 状态 |
|---|---|---|
| 48px 紧凑折叠态 | 规范 3.3 | 未实现（当前折叠为 0） |
| `Cmd/Ctrl+K` 命令面板 | 规范 8.8 | 未实现 |
| Toast 最多 3 条堆叠 | 规范 4.8 | 未实现（当前单条） |
| 多租户与 API Key 鉴权 | v2.0 要求三 | 契约已定义，未实现 |
| Evidence Package 与 Webhook 推送 | v2.0 要求二 | 契约已定义，未实现 |
| Python / JS SDK | v2.0 3.4 | 未实现 |

---

## 2026-09-21 · W7 科学计算引擎与规范表格（后端 + 数据产物）

### 10. 新增「规范长表（canonical table）」数据产物

- **规范原文**：第四章组件清单只有「列映射表」，未定义归档后的数据产物形态。
- **实现**：新增 `canonical_table_v1` 长表（24 列），一行一个测量点，含
  实验/工作表/区域/块/行号/分析方法/离子/信号面积/表内自算浓度/引擎复算浓度/单位换算值/
  稀释倍数/偏差/是否外推/所用标定块，同时以 **CSV（utf-8-sig）** 与 **Markdown** 导出。
- **理由**：PRD 要求「可追溯」——每个数字都必须能回到 Raw 的**具体 Excel 行号**，
  这正是长表而非宽表的原因；也是推进规划 v2.0「Evidence Package」的前置数据形态。
- **约束**：不新增颜色/字号/间距令牌；表格样式复用既有 `.row` 网格与 token。

### 11. 计算结论的「不确定性必须显式暴露」原则（新增设计约束）

- **背景**：W7 复算真实实验表时发现，朴素算法会**静默给出错误但看似合理的数字**：
  - 标定曲线截距非零 → 零信号被反算成约 1.0 ppm 的"幻影浓度"；
  - 以「平均相对偏差」选择标定归属 → 被近检出限点支配而选错曲线；
  - 穿透尾端负浓度 → 被当作平衡浓度算出无物理意义的吸附容量。
- **实现**：以下信息一律**进入产物本身**，而非仅存在于日志：
  `zero_signal_concentration_ppm`、`n_scored` / `n_excluded_near_zero`、
  `extrapolated` / `extrapolation_ratio`、`equilibrium_source`、`equilibrium_extrapolated`、
  以及 `notes` 中的中文风险提示（如"尾端低浓度点不可靠""标定归属仅在 1 个可对照点上判定"）。
- **理由**：符合 PRD「低置信度必须暴露」与「输入不足的计算必须返回失败原因，绝不臆造」。
- **影响**：归档页面与规范文档必须能展示 `notes` 与不确定性字段（待接入）。

### 12. 新增只读数据端点

| 端点 | 返回 |
|---|---|
| `GET /v1/experiments/{id}/data/canonical` | 规范长表（结构化 JSON） |
| `GET /v1/experiments/{id}/data/canonical/csv` | 规范长表 CSV 下载 |

- **理由**：推进规划 v2.0 要求 API-first；规范表格须可被外部系统直接取用，
  而非只能在前端页面阅读。

---

## 2026-09-22 · W8 识别确定性修复与幽灵列收敛（前端 + 后端）

### 13. 无表头列「一律不自动映射」（新增设计约束：语义证据缺失时不得臆断）

- **背景**：W7 基准样本中发现，同一个文件、同一模型，对**无表头但有数据**的列
  （如 `sheet-01#R44-44/B1` 的 G 列；L1 证据：`number` / 填充率 1.0 / 22 个非空 /
  值域 0–2249.76）会**随机**给出 `concentration_mg_l`（置信度 0.70/0.72）或 `None`（0.20）。
  实测 6 次快照为 4:2 跳变 —— 同一输入产生两种归档结论。
- **实现**：规则层强制：`raw_header` 为空 → `target_field = None`、
  `confidence = min(confidence, 0.2)`，并把模型候选建议**完整写入 `evidence`**
  （"该列无表头，缺少语义证据，未自动映射（模型建议 X，置信度 y）；如确为有效数据列，请人工改判"）。
- **理由**：无表头即缺少语义证据；证据不足时给出确定值，会让归档结论随模型抖动。
  把不确定性交还**人工判定**（一键改判），而非交给概率采样 —— 与第 11 条「不确定性必须显式暴露」同一原则。
- **影响**：`evidence` 有意保留模型候选（信息不丢），故同一输入两次识别的 `evidence` 可能不同，
  但**决策字段（target/field/conf）完全一致**，前端分类不再跳变。

### 14. 「幽灵列」定义收窄为「空表头 **且** 无数据」

- **原实现**：空表头即判为 `missing`（幽灵列）。
- **实现**：`fieldState` 改为需**同时**满足「空表头」与「无数据」（`nonNull <= 0`）；
  空表头但有数据的列判为 `pending`（待确认）。为此后端所有列透传 L1 证据 `nonNull` / `fillRatio` / `valueType`。
- **理由**：真实存在的派生列（如稀释换算列）没有表头但有完整数据，一律判为幽灵列会误导用户忽略有效数据。
- **兼容**：旧快照无 `nonNull` 时回退为 `missing`，不影响已归档数据。

### 15. 整块识别失败与列级判定「解耦」

- **背景**：列块整体识别失败的条目（`failedBlocks`）此前被前端塞进**列级**通道（`col: 'block'`），
  确认后请求打在列端点 → 后端列查找失败 → **404 空响应**（先查找后写库，未污染数据）。
- **实现**：
  - 前端：`failedBlocks` 增加 `scope: 'block'`，不与列级待确认计数混算；顶部徽标拆分
    「X 项待确认 · Y 块识别失败」；Inspector 对整块失败显示说明与「知道了」，「原始表头」行隐藏。
  - 后端：列端点遇 `target_column is None` 时，若该块 `degraded`，返回 **422 + 可操作提示**
    （"列块 X 识别失败（原因），无法通过人工判定修复，请重新上传或重试识别"），否则仍 404。
- **理由**：整块失败是"识别失败"而非"待人工判定"，两者处置动作不同；错误语义应正确暴露
  （422 语义错误，而非 404 资源不存在）。

### 16. 识别结果缓存引入「规则层版本号」

- **背景**：识别缓存（`data/cache/{sha}__{sheet}.json`）存的是**最终 payload**（已含规则层结论）。
  若不校验版本，规则升级会被旧缓存整体绕过 —— 第 13 条的确定性修复对已缓存文件形同虚设。
- **实现**：新增 `RECOGNITION_RULE_VERSION`，写入 payload 的 `source.ruleVersion`；
  命中缓存时版本不一致即**视为未命中并重算**。
- **理由**：缓存的收益是省 LLM 成本，但不得凌驾于规则正确性之上；
  任何改变识别结果的规则改动必须显式递增版本号。

---

## 2026-09-22 · 缺陷 C：识别骨架「值」字段恒空 → 数据值展示归位（前端）

### 17. 数据值不进「列级」结构：恒空「值」通道改为填充证据 + 规范长表展示

- **背景（用户提问暴露）**：档案详情页每个列块的表格中有一列「值」，但**整列永远为空**。
  排查确认它绑定 `column.value`，而后端在 `build_block_payload` / `degraded_block_payload` 中
  **硬编码 `"value": ""`**，全链路无写入路径；识别页的同名列是输入框，
  但其 `edited` 仅存在于组件内存（无 emit / 无提交 / 不进 API），**输入刷新即丢**。
- **根因（契约错位）**：一个「列」对应**多行**值（如 G 列 22 个非空值），列级结构承载不了单个「值」；
  且识别阶段**本就不持有数据值**（见第 10 条：数据值在归档时由 `build_canonical` 以 `data_only=True`
  重读原始文件并复算）。该字段是早期「单值字段」设计的残留，却被前端两处当作"数据值"呈现。
- **实现**：
  - 档案详情页：「值」列改为**填充证据**（`nonNull · fillRatio%`，来源为第 14 条透传的 L1 证据）；
    旧快照无该字段时显示 `—`，**不伪造数字**。
  - 档案详情页：新增**规范长表区块**，直接渲染 `canonical.rows`（列清单取自后端 `canonical.columns`，
    不硬编码），数据值**首次在界面可见**；超过 100 行截断并提示导出 CSV。
  - 识别页：移除恒空且不会被保存的「值」输入框及其 `edited` 副本，改为同一填充证据展示
    （行网格由 7 列收为 6 列）。
- **理由**：「值」在语义上必须是**逐行**的 —— 列级要么展示统计证据（填充率），要么去长表看真实数据。
  把恒空字段当数据值展示，会让用户误判"数据丢失"。符合第 11 条「不确定性必须显式暴露」：
  `—` 表示"旧快照未透传证据"，而非"没有数据"。
- **影响**：前端首次拥有规范长表视图（此前仅 `ApiDocsView` 提及该端点）。
  规范长表实际为 **25 列**（第 10 条记为 24 列，实际含 `experiment_id` 共 25 列）。
- **约束**：不新增颜色/字号/间距令牌；长表复用既有 `.grid` 表格样式，仅新增横向滚动容器与 `.hint`。

---

## 2026-09-23 · 模板填充链路（三实验类型 → Excel 导出）

### 18. 模板配置化 + 派生计算 + 填充 + 导出的四段式链路

- **背景（导师新要求）**：系统需支持**三套实验模板**——Batch / Column / Electrochemical；
  识别完成后数据要**按模板结构填入并导出**，最终汇总（NAS 适配器预留，信息后补），
  供"中央大脑"调用（本阶段搁置）。
- **模板来源**：老师提供三份自由文本草稿（`Batch_Test.txt` / `Column_Test.txt` /
  `Electrochemical_Experiment.txt`），人工转录为配置（`config/templates/*_template_v1.json`）：
  A 实验信息 / B 时序数据 / C 派生量；列以 `role`（time/concentration/ph/potential/current）
  声明语义，字段以 `from` 声明元数据候选路径，`data_policy.concentration` 声明浓度口径。
- **四段式实现**：
  1. `src/derive.py`（**derive_v1**）：C 区派生计算——Batch（Cₑ / 去除率 / qₑ / 平衡时间）、
     Column（处理体积 / BV 倍数 / Cₜ/C₀ / 穿透 / 耗尽）、Electrochemical（电流密度 / 终浓度 /
     去除率 / 电荷 / 能耗）；阈值集中定义在模块顶部常量，每项带 `method`；
     缺输入返回 `reason` + `value=None`，绝不臆造。
  2. `src/template_fill.py`（**fill_v1**）：数据值**一律从 Raw 重读**，按块定位
     （复用 `canonical._locate/_read_column/_field_columns`）；多离子分组（一离子一 sheet）；
     单位换算；调用 derive 产出 C 区。
  3. `src/template_export.py`（**export_v1**）：openpyxl 写出 A/B/C 三段 + 数据规则 + Provenance；
     缺值留空（不写 NA）、C 区不可计算原因写在 Note 列。
  4. 离线验证：**54 项断言全通过**（derive 手算对照 + `RES-20260921-003` 真实数据回归 +
     合成 electrochemical 端到端）。
- **新增设计约束**（与前文第 11 条一脉相承）：
  - **数据值必须从 Raw 重读**：识别快照只有列映射骨架，任何导出数值必须回原始文件读取
    （`data_only=True`），绝不从快照拼接。
  - **浓度口径显式标注**：`engine_first`（引擎复算优先、缺失回退原表值），
    实际填充口径写入导出 Provenance；回退 ppm 原值时标注 `ppm≈mg/L` 假设。
  - **单位未知时禁止换算**：`time/h` 等复合表头可识别为 h 并留痕（"推断为 h，1 h = 3600 s"）；
    无法识别时**原样传递 + notes 提示人工核对**，绝不按猜测系数换算。
  - **展示保真**：离子名保留原始表写法（"Cl" 不写成 "CL"），大写分组键仅用于合并大小写变体。
- **约束**：模板为纯 JSON 配置（无代码），新增实验类型只需加配置；填充器不调用 LLM。

---

## 2026-09-24 · 模板导出接入服务端与前端下载入口（T2）

### 19. 导出端点实测 + 档案详情页「导出模板 Excel / 导出 CSV」

- **背景（状态核对方法修正）**：09-23 会话日志把「T2：填充/导出接入服务端」整项列为候选待办；
  本次实际检查发现端点代码在 09-23 22:07 已随 T1 提交（`server/app.py` 的
  `GET /v1/experiments/{id}/export/template`），日志记录滞后于代码实际状态。
  **结论：跨会话状态一律以实际检查（代码、端口、HTTP 探测）为准，日志仅作线索。**
- **后端（补实测，零改动）**：该端点此前从未经过 HTTP 层验证（09-23 的 54 项均为离线断言）。
  本次实测 **17/17 通过**：column 导出双 sheet（SO4/Cl）+ 时间 h→min 换算（末行 600 min）+
  A/B/C 三区与 Provenance 齐全；batch 导出正确；regeneration → 422（无模板类型，提示语列出可选类型）；
  无识别数据 → 404；不存在实验 → 404；Content-Type / Content-Disposition 文件名正确。
  验证脚本：`.deepworks/tmp/verify_export_endpoint.py`。
- **前端（本次新增）**：
  - `api.js`：新增 `download()` 封装——blob 接收 + 从 Content-Disposition 解析文件名，
    错误解析与 `req()` 一致（后端 detail 透传为 `Error.message`）；新增
    `api.exportTemplate(id)` / `api.exportCanonicalCsv(id)`。
  - 档案详情页：头部新增「导出模板 Excel」按钮（在线且非示例档案时显示）；
    规范长表标题行新增「导出 CSV」按钮——**同时补齐 09-22 遗留**：长表截断提示语
    「完整数据请导出 CSV」此前只有文字没有入口。导出中按钮禁用并切换文案，结果经 toast 反馈。
- **约束**：不新增颜色/字号/间距令牌；按钮复用 `.btn .btn-secondary`，
  紧凑态仅压缩高度与字号（与既有「返回」按钮同为 32px 高）。

---

## 2026-10-02 · UI 地基收敛：死代码清理 / 深色跟随 / 状态唯一来源 / token 增量

### 20. 第 0–1 阶段（对应 docs/ExpResin-UI-Upgrade-Plan-v2.0.md）

- **删除死代码**：`src/style.css`（未被 main.js 引入，且含紫色 `#aa3bff` 主题与 18px 根字号，与设计系统冲突）、
  `components/HelloWorld.vue`、`components/TopBar.vue`、`components/Inspector.vue`（全仓无引用），
  经 grep 二次确认后以 `git rm` 移除，保留历史可恢复。
- **深色模式回归规范 §8.7**：此前 `index.html` 固定 `data-theme="light"` 且 `useTheme.js` 默认写死 light，
  使 tokens.css 的 `prefers-color-scheme` 规则永不命中。现改为：仅当用户显式选择 light/dark 时写
  `data-theme`，否则移除属性、由系统媒体查询接管；`useTheme` 新增 `auto` 模式与系统变化监听，
  对外仍暴露 `theme`（实际生效值）与 `toggleTheme`，并新增 `setMode`。
- **字段状态唯一事实来源**：新建 `src/domain/fieldStatus.js`，集中列识别域 `fieldState` 与录入草稿域
  `draftStatusOf`，以及两套「状态 → 文案/色调」词表。`demo.js` 改为 import + re-export（兼容既有引用），
  `DynamicForm.vue`、`TemplateForm.vue` 改为消费同一词表。**判定规则与旧实现逐条等价**，仅消除
  同一语义在不同面板出现不同标签/颜色的风险（PRD 宪法 #8）。
- **token 纯增量**：新增控件（`--control-*`）、聚焦环（`--focus-ring`）、层级（`--z-*`）、
  `--info-bg`、面板头/移动端高度与折叠栏宽（`--panel-head-h` / `--topbar-h-mobile` /
  `--statusbar-h-mobile` / `--rail-collapsed-w`）。**未修改任何既有颜色/间距/字号/圆角/阴影/动效值。**
- **深度策略单一化（决策）**：静止态的面板/卡片只用「表面色差 + 极弱边框」，不再叠加阴影；
  阴影仅留给悬浮/交互抬升。据此 `.card` 移除静止阴影，补规范 §4.3 的 hover（`shadow-md` + 上移 2px）；
  `.input` 改用控件 token；`.badge-info` 改用 `--info-bg`。
- **布局与语义**：`WorkbenchLayout` 工作条高度与网格行改用 `--panel-head-h`；页面标题由 `--text-base`
  提升到 `--text-lg`/600（说明：工作条仅 48px，未采用规划中 24px 的页面标题刻度，以免在工具条内过挤，
  24px 留给真正的页面级标题）；移动端 tab 补 `role=tablist/tab`、`aria-selected`、`aria-controls`
  与 panes 的 `tabpanel`，并补 hover 态。
- **验证**：`npm run build` 通过（65 modules，无错误）。
- **已知遗留（未处理）**：`src/data/store.js` 全仓无引用，疑似死代码，但不在本次批准删除清单内，暂保留待确认。

---

## 2026-10-02 · UI 升级第 2 阶段：状态完整性 / toast / 提交反馈 / 深度收敛

### 21. 第 2 阶段（对应 docs/ExpResin-UI-Upgrade-Plan-v2.0.md）

- **toast 升级为队列 + 语义色调**：`useToast.js` 支持 `{ tone, duration }`（兼容旧的 `show(text, ms)`），
  最多同时 3 条（规范 §4.8），错误停留更久；`App.vue` 改为 `TransitionGroup` 堆叠渲染，
  带左侧色调条、可关闭按钮，错误用 `role="alert"`、其余 `role="status"`。所有调用点补 tone：
  归档/识别成功=success，必填缺失/离线=warning，异常=error。
- **列表页状态补全**：`session` 新增 `archiveLoading`，`loadArchive` 用 `finally` 归位；
  `HomeView`/`ArchiveView` 增加加载骨架、加载失败错误条（`empty--error`），与「后端未连接」「无数据」区分。
- **提交反馈**：`StatusBar` 新增 `saving` / `saving-label`，进行中禁用按钮、显示 spinner 与 `aria-busy`；
  `SetupView`、`RecognizeView` 接线 `archiving`。`MappingInspector` 新增 `resolving`，
  确认/改判/忽略与底部按钮在提交中禁用，确认按钮显示「提交中…」。
- **深度策略继续收敛**：`HomeView` 的 `.entry`、`ArchiveView` 的 `.card-item` 移除静止态阴影
  （改为表面色差 + 弱边框），hover 才抬升；与 `.card` 保持一致。
- **token 收口**：`RecognizeView` 的 `#64748b` → `var(--text-tertiary)`；
  `--border-default` / `--transition-fast` 等**不存在**的令牌 → `--control-border` /
  `--duration-fast var(--ease-standard)`；工作表输入框高度 28→36px 并用 `--control-*` 与 `--focus-ring`；
  `StatusBar`/`App` 的 z-index 与移动端高度改用 `--z-sticky` / `--topbar-h-mobile` / `--statusbar-h-mobile`。
- **验证**：`npm run build` 通过（65 modules，215ms）。

---

## 2026-10-02 · UI 升级第 3–4 阶段：共享组件 / 页面层 / 签名层 / 打磨 / P3

### 22. 组件层与页面层（对应 plan §6、§7、§8）

- **抽取 9 个共享结构组件**（`src/components/`）：`PanelHead`、`ConfirmChip`、`StatGrid`、
  `IssueList`、`TraceList`、`MiniButton`、`ChatMessage`、`ProvenanceRail`、`DocsLayout`，
  消除此前散落的 `.panel-head` / 统计 / 问题列表 / 溯源 `<dl>` / 气泡 复制。`PanelHead` 统一
  48px（`--panel-head-h`）；消费点已覆盖 `ChatPanel`、`DynamicForm`、`MappingInspector`、
  `MetadataInspector`、`SetupView`、`RecognizeView`（共 7 处，含视图层两处）。
- **标题刻度校正**：`WorkbenchLayout` 的 `h1` 由 §20 记录的 `--text-lg` 提升到 `--text-xl`（24px），
  撤销 §20 中「工作条仅 48px 故不采用页面标题刻度」的偏离 —— 实测 24px/1.3 在 48px 工作条内可容纳，
  与 plan §6.2、设计规范 §4.3 一致。页面级 `ArchiveDetailView`、`ApiDocsView` 的 `h1` 同为 `--text-xl`。
- **折叠态 48px 图标轨**：`WorkbenchLayout` 折叠栏由 0 改为 `--rail-collapsed-w`（48px），
  保留展开按钮 + 竖排 caps 标签，满足规范 §3.3（此前 changelog §2 记为未达标）。
- **响应式断点收敛**：`App`、`HomeView`、`ArchiveView`、`StatusBar`、`AppHeader`、`DocsLayout`、
  `ArchiveDetailView` 的 `640/720/820/900/1180` 统一为规范 §3.2 的 **480 / 768 / 1024 / 1280**。
- **触控目标**：`.btn-ghost`/`.icon-btn` 由 36 提升到 40px；`TemplateForm` `.fcontrol .input`、
  `RecognizeView` 工作表输入、`ArchiveDetailView` 返回/紧凑按钮均 ≥40px。

### 23. 签名层

- **`ProvenanceRail` 落地**：2px 竖向导轨 + 置信度芯片（颜色 + 文本双重编码，阈值 0.8），
  接入 `DynamicForm` 行与 `ArchiveDetailView` 列块头。
- **档案锚点目录**：`ArchiveDetailView` 头部下方新增吸顶 `nav.toc`，各区带 `id="region-*"`、
  `id="canonical"`，`scroll-padding` + `scroll-margin` 保证跳转不遮挡。
- **表格与统计语义**：统计由 `div` 改 `dl`（`dd` 数值 + `dt` 标签）；表格补 `scope="col"` 与
  `aria-label`；映射表与规范长表统一走 `.table-scroll` 横向滚动。
- **说明（偏离）**：「规范 / 原始双栏对照」未做并排两栏，改由「列映射表（原始表头 → 标准字段）+ 规范长表」
  两段递进承载。理由：原始表头到标准字段的对照已由映射表的列直接表达，并排双栏在 24+ 列时会挤压可读性，
  与「规范长表需横向滚动」的既有约束冲突。此取舍记入本变更。

### 24. 打磨层

- 表格语义、移动端 tab 语义（`role=tablist/tab/tabpanel`、`aria-selected`、`aria-controls`）已于前阶段落地；
  本阶段补 `aria-current`（ApiDocs 导航）、搜索框清空按钮与弹性宽度（ArchiveView）、
  统计数值 `tabular-nums`、`--radius-full` 收敛（MetadataInspector）、`.card` hover/focus（前阶段）。

### 25. P3 规范落地

- **首屏入场序列（规范 §5.3）**：`base.css` 新增 `.stagger-in` 工具类，`HomeView` 按
  100/200/300+i·50/500ms 对 hero 标题、副标题、三步入口、近期实验依次入场；全局
  `prefers-reduced-motion` 降级已覆盖。
- **模态（规范 §4.9）**：新增 `BaseModal.vue`（blur 遮罩、560px、`--radius-xl`、`--shadow-lg`、
  `scale(0.96)→1` 入场、Esc / 点遮罩 / 关闭按钮），并接入 `RecognizeView`：归档被 409 拦截时
  以模态列出缺失必填项并提供「去补全」跳转。
- **部分实现（记录）**：模态仅做打开时自动聚焦 + 关闭后焦点归还，未实现完整 Tab 焦点陷阱（trap）；
  待有更复杂表单模态需求时补齐。

### 26. 未处理 / 已知偏离

- `HomeView` 近期实验仍用 `ul/li`（对「实验列表」语义比 `dl` 更贴切），未按 plan §8 改 `dl`。
- `RecognizeView` 顶部栏未按 plan §8 拆为两行：`PanelHead` 固定 48px 高，换行会破坏该高度约束；
  窄屏下改用省略与 `flex` 收缩。
- `tokens.css` 的系统深色块与 `[data-theme=dark]` 块因 CSS 语法限制未合并，保持数值同步；
  暗色 `--accent-bg` 已由 0.12 统一为 0.1，并补齐两处 `--on-accent`。
- 验证：`npm run build` 通过（82 modules，约 230ms，无错误）。

---

## 2026-10-11 · 配色体系升级：暖色 Claude/Anthropic 风格 + 浅/深主题

### 27. 暖色调色板替换冷蓝，Jarvis 温暖对话区

- **背景 / 目标**：原配色为「科技蓝 + 冷灰 + 纯黑/纯白」工业感体系，与产品「温暖的
  AI 实验伙伴」定位不符。本次按用户给定的设计说明，整体替换为温暖、克制、现代的
  琥珀橙体系，并对齐 Anthropic Claude 的视觉语言。浅/深主题切换机制不变（沿用
  `useTheme.js` 的 auto/light/dark 与 `data-theme`）。
- **调色板（tokens.css）**：
  - 新增权威调色板变量：`--bg-page` / `--bg-workbench` / `--bg-card`、
    `--brand-orange` / `--brand-orange-hover`、
    `--accent-blue` / `--accent-green` / `--accent-yellow` / `--accent-red`、
    `--text-disabled`，以及 Jarvis 专用的 `--chat-surface` / `--chat-bubble` /
    `--chat-bubble-user` / `--chat-dot`。
  - **旧语义 token 桥接到新调色板，组件零改名**：`--bg-canvas`/`--bg-primary`/
    `--bg-secondary`/`--surface-card`/`--accent`/`--accent-hover`/`--accent-subtle`/
    `--success`/`--warning`/`--error`/`--info` 全部指向暖色值，因此全站组件自动换肤，
    无需逐个文件改动。浅色 `--bg-primary = --bg-workbench`，深色 `--surface-card = --bg-card`。
  - 浅色三级层次：页面 #FAF9F5 → 工作台 #F2F0E9 → 卡片 #FFFFFF；深色：页面 #151312 →
    工作台 #1F1D1B → 卡片 #282623（不使用纯黑）。
- **状态色降饱和并保持温暖统一**：浅色状态标签用「浅底 + 深字」（如待确认 #FFF4E6 /
  #B36A3E），深色用「半透明底 + 彩字」（如 #A4B688）。低置信度=warning、单位异常=error、
  确认成功=success 的语义映射不变。
- **深度策略**：卡片/面板静止态去掉阴影，改用「表面色差 + 极淡暖边框」区分层次，
  仅悬停抬升（`--shadow-md` + translateY-2px）。阴影色由纯黑改为暖灰。
- **组件改造**（结构性，非仅换色）：
  - `base.css`：主按钮改为琥珀橙底 + 深暖色文字（`--on-accent`）；次要按钮悬停转橙
    （`--accent-subtle` 底 + `--brand-orange` 边框/文字）；输入框极淡边框 + 暖白底 +
    橙色聚焦环；`.card` 去静止阴影。
  - `PanelHead.vue`：新增 `dot` 属性，标题前渲染一枚橙色光点。
  - `ChatPanel.vue`：Jarvis 区背景改为 `--chat-surface`（与工作台一致，去掉冷灰块），
    输入框改 `--radius-full` 圆角，聚焦橙高亮；面板头启用 `dot`。
  - `ChatMessage.vue`：Jarvis 气泡改用 `--chat-bubble` 暖底 + 极淡边框；用户气泡用
    `--chat-bubble-user`。
  - `BaseModal.vue`：遮罩改用 `--overlay`，容器背景改用 `--surface-card`。
  - `AppHeader.vue`：导航结构与交互保持 v1.0 的胶囊轨道 + 平移滑块不变（曾尝试改为
    简洁文字导航，经用户指出属错误改动，已完整回退）。
  - 导航暖色呈现调优：新增 `--nav-track`（浅 #E6E1D3 / 深 #232120）、
    `--nav-track-border`（浅 #DDD7C6 / 深 #2C2926）、`--nav-slider`（浅 #FFFEFB / 深 #3B3630）
    三个 token。修正深色模式下滑块（原取自 `--surface-card` #282623）比轨道更暗导致的
    「凹陷」错觉，现滑块恒比轨道更亮，浮起感在浅/深两种模式下一致。
- **偏离与理由（规范 §十.13 要求）**：
  - 主按钮文字由「白色」改为 `--on-accent` 深暖色：琥珀橙 #D97757 上白字对比度仅约
    3.1:1，不满足规范 §八.5「对比度 ≥ 4.5:1」；深暖色 #2C1810 约 5.4:1 达标。
    此为规范 §4.1 的文字色修订，已同步更新规范文档。
  - 深色 `--success`/`--warning` 等取较亮的彩色值直接作文字色（在半透明底上），
    替代浅色模式的深字方案。
- **文档**：`docs/ExpResin-UI-Design-Spec-v1.0.md` 升版为 **v1.1**，§2.1 配色表、
  §4.1/§4.2/§4.3/§4.4/§六 相关条目同步为暖色；文件名保持不变以兼容既有引用。
- **验证**：`npm run build` 通过（无错误）。新增静态预览 `outputs/warm-theme-preview/index.html`
  用于浅/深一键对照。

---

### 28. 框架区块暖色化 + 视图副标题改为悬浮提示（2026-10-11 追加）

- **左 / 上 / 右白色区块变暖（Claude 风格）**：
  - `--glass-bg` / `--glass-bg-strong` 浅色由「近纯白」`rgba(250,249,245,…)` 改为与工作台
    同源的暖米 `rgba(242,240,233,0.78 / 0.92)`。顶部全局栏（AppHeader）与检查器吸顶头
    随之从白色变为暖米，深色不变（原本就是暖炭）。
  - 左 / 右折叠栏（`.pane--collapsed` 48px 图标轨）：背景由 `--surface-card`（白）改为
    `--bg-workbench`（与工作台同色系），并去掉 `shadow-sm`——轨道后退为「框架」而非
    白色卡片；竖排标签 `.rail-label` 颜色提为 `--text-secondary` 保证在新底色上的可读性。
  - 三处均只换底色 token / 引用，结构与交互不变。
- **四个视图大标题后的小字改为鼠标悬浮提示，并精简文案**：
  - `base.css` 新增全局 `[data-tip]` 悬浮提示工具（含 `data-tip-align="start"` 左对齐变体
    与 `h1[data-tip]` 的 help 光标暗示）；AppHeader 原有的 `.brand-wrap::after` 局部实现
    删除，改由全局工具承接（视觉一致）。
  - `WorkbenchLayout` 的 `subtitle` 不再渲染为可见小字，改为 h1 的 `data-tip`；
    SetupView / RecognizeView 随之生效。
  - HomeView / ArchiveView 的 h1 同样改为 `data-tip`，删除原 `<p class="muted">` 说明行
    及其样式。
  - 文案精简（保持原意）：工作台「三步：实验前录入、实验后识别、归档调用；Raw 只读，
    Processed 可追溯」；新建实验「录入初始信息，形成记录草稿」；数据识别「上传原始表格，
    识别列与单位，逐列确认」；实验档案「归档规范文档，供复用与 Public API 调用」。
- **验证**：`npm run build` 通过；dev server HMR 已生效。

---

## 版本记录

| 版本 | 日期 | 变更 |
|---|---|---|
| 1.0 | 2026-09-19 | 首次实现 PortalJarvis 三栏工作台，记录 5 项偏离与待办 |
| 1.1 | 2026-09-19 | 重构为多页面工作台，对齐实验生命周期；树脂型号加前缀；记录新增 4 项待办 |
| 1.2 | 2026-09-21 | W7：新增规范长表数据产物与 CSV/JSON 端点；确立「计算不确定性必须显式暴露」约束 |
| 1.3 | 2026-09-22 | W8：无表头列一律不自动映射（候选写入 evidence）；幽灵列收窄为「空表头且无数据」；整块失败与列级判定解耦（404→422）；识别缓存引入规则版本号 |
| 1.4 | 2026-09-22 | 缺陷 C：识别骨架「值」字段恒空的契约错位 —— 「值」列改为填充证据、新增规范长表展示区块、移除识别页无效「值」输入框 |
| 1.5 | 2026-09-23 | 模板填充链路：三实验类型模板配置化 + 派生计算（derive_v1）+ Raw 重读填充（fill_v1）+ Excel 导出（export_v1）；确立「数据值必须从 Raw 重读」「浓度口径显式标注」「单位未知禁止换算」「展示保真」四条约束 |
| 1.6 | 2026-09-24 | T2：模板导出端点 HTTP 实测（17/17）+ 档案详情页「导出模板 Excel」「导出 CSV」下载入口（补齐 09-22 CSV 遗留）；确立「跨会话状态以实际检查为准，日志仅作线索」方法 |
| 1.7 | 2026-10-02 | UI 升级第 0–1 阶段：移除 4 个死代码文件；修复深色模式跟随系统；字段状态收敛到 `domain/fieldStatus.js`；新增控件/聚焦/层级/info/布局 token（纯增量）；深度策略单一化（面板无阴影、悬浮才抬升）；工作台标题升到 `--text-lg`、移动端 tab 补语义 |
| 1.8 | 2026-10-02 | UI 升级第 2 阶段：toast 队列+色调+可关闭；Home/Archive 加载骨架与错误条；StatusBar `saving` 与 MappingInspector `resolving` 提交反馈；Home/Archive 卡片停止态去阴影；修正 RecognizeView 不存在令牌与硬编码色 |
| 1.9 | 2026-10-02 | UI 升级第 3–4 阶段：抽取 9 个共享组件；工作台 h1 升 `--text-xl`、折叠栏 48px 图标轨；断点收敛 480/768/1024/1280；签名层 ProvenanceRail + 档案锚点目录 + 表格/统计语义；首屏入场序列与 BaseModal（§4.9，部分实现）；首页搜索清空、触控目标 40px |
| 2.0 | 2026-10-11 | 配色体系升级：科技蓝 → 暖色琥珀橙（Claude/Anthropic 风格），新增浅/深两套暖色调色板；旧语义 token 桥接新色板实现全站换肤；状态色降饱和改暖；卡片去静止阴影；主按钮橙底深暖字（对比度达标）；Jarvis 温暖对话区（橙色光点 + 暖气泡 + 圆角输入框）；设计规范升 v1.1 |