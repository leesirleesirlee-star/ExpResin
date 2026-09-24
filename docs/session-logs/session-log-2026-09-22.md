# ExpResin 会话日志 · 2026-09-22

> 用途：记录当日工作状态、启动/停止方法与遗留事项，供下次接手时快速恢复上下文。
> 本日主题：**W8 识别确定性修复（缺陷 A/B）+ 前端修复验收 + 缺陷 C（数据值展示归位）**。
> 承接 09-21 日志第 5 节遗留的**第 5 项（failedBlocks → 404）**与**第 8 项（幽灵列非确定性）**；
> 缺陷 C 由用户提问「档案页『值』列全为空，值存到哪去了」暴露。

---

## 0. 本日收尾状态（服务仍在运行中）

| 服务 | 启动时间 | PID | 监听地址 | 状态 |
|---|---|---|---|---|
| 前端 Vite dev server | 16:12:27 | **16944** | `::1:5173`（仅 IPv6） | ✅ 运行中 |
| 后端 uvicorn (FastAPI) | 16:57:52 | **11796**（启动器 shim **8496**） | `127.0.0.1:8000` | ✅ 运行中 |

- 启动 / 停止方法与 09-21 日志第 1 节相同；后端**无控制台**，停止用 `Stop-Process -Force`（09-21 日志已论证其安全性）。
- `GET /api/health` → `{"status":"ok","service":"expresin-portal","version":"0.1.0"}`。
- 前一次运行的访问日志已归档：`.deepworks\tmp\archive\2026-09-22\api_before_rulefix.log`。

> ⚠️ **Vite 有 HMR，改 `src/` 不要重启 dev server**；后端未开 `--reload`，改 `app.py` **必须重启**（本日因规则层改动重启过一次）。

---

## 1. 缺陷 A：整块识别失败误入「列级」通道 → 404（09-21 遗留第 5 项）

### 现象与复现
列块整体识别失败的条目（`failedBlocks`）被前端映射为 `col: 'block'` 走**列级**通道，点击确认后请求打到列端点：

```
PATCH /portal/assistant/sessions/ses_6648dc8b1916/recognized-columns
body: {"block_id":"0305-600#R44-44/B1","col":"block","action":"confirm"}
→ 404，空 body
```

**根因**：`review_recognized_column` 先按 `col_letter` 查找列，查不到即 404（查找先于写库，**未污染数据**）。

### 修复（4 处）
| 层 | 文件 | 改动 |
|---|---|---|
| 前端 | `data/demo.js` `collectIssues` | `failedBlocks` 项加 `scope:'block'`，evidence 改为"该列块整体识别失败，无法通过列级判定修复，请重新上传或重试识别" |
| 前端 | `components/MappingInspector.vue` | `total` 排除 `failedBlocks`；新增 `isBlockFailed`；整块失败时「原始表头」行隐藏、动作区改为说明 + 「知道了」 |
| 前端 | `views/RecognizeView.vue` | `pendingTotal` 去掉 `failedBlocks.length`；新增 `failedTotal`；徽标「X 项待确认 · Y 块识别失败」 |
| 后端 | `server/app.py` `review_recognized_column` | `target_column is None` 且该块 `degraded` → **422** + 可操作提示；否则仍 404 |

**设计含义**：整块失败是"识别失败"而非"待人工判定"，错误语义应正确暴露（422 语义错误 ≠ 404 资源不存在）。已记入 changelog §15。

---

## 2. 缺陷 B：无表头列映射的非确定性 → 一律不自动映射（09-21 遗留第 8 项）

### 取证（推翻了「幽灵列」旧描述）
`0305-600#R44-44/B1` 的 **G 列不是空列**。L1 结构证据：
`value_type=number`、`fill_ratio=1.0`、`non_null=22`、`numeric_range=[0.0, 2249.76171784]`；
且数值上**严格 = E 列（表内自算 ppm）× 100**（稀释倍数）：E=`8.7451006944` → G=`874.5100694399999`。

6 次识别快照（`session_assets` · `recognized_blocks`）实测跳变：
**4 次 → `concentration_mg_l`(0.70/0.72)、2 次 → `None`(0.20)** —— 同输入、同模型的**非确定性**。

### 用户决策
**一律不自动映射**：空表头列规则层强制 `target=None`，LLM 候选建议写入 `evidence`，人工可一键改判。

### 修复（3 处）
| 层 | 文件 | 改动 |
|---|---|---|
| 后端 | `server/app.py` | 新增 `column_data_evidence(profile)` → `{nonNull, fillRatio, valueType}`；`build_block_payload` 中 `raw_header` 为空 → `target_field=None`、`confidence=min(conf,0.2)`、evidence 记录模型候选；所有列透传 L1 证据 |
| 后端 | `server/app.py` | `degraded_block_payload` 同样透传 `column_data_evidence(profile)` |
| 前端 | `data/demo.js` `fieldState` | 「幽灵列」收窄为**空表头且无数据**（`nonNull<=0`）；空表头但有数据 → `pending` |

### 离线验证（零 LLM 成本）
脚本 `.deepworks/tmp/verify_rule_determinism.py`，用真实 L1 数据 + 真实 `build_block_payload` 函数，
模拟 LLM 历史上跳变的两端：

| 项 | 结果 |
|---|---|
| G 列**决策字段**（target/field/conf/nonNull/valueType） | 两种 LLM 输出下**完全一致**：`target=None`、`field=None`、`conf=0.2`、`nonNull=22` |
| G 列 `evidence` | 有意保留模型候选（`concentration_mg_l`(0.7) 或空）→ 两侧可不同，**信息不丢** |
| 有表头列 E | 不受影响，仍 `concentration_ppm` / `0.97` |

前端逻辑 `verify_fieldstate.mjs`：8/8 通过（空表头有数据→pending、空表头无数据→missing、有表头→confirmed/pending、离子标签→label、低置信→low-confidence、人工忽略→ignored）。

**设计含义**：证据不足时不得臆断；把不确定性交还人工判定。已记入 changelog §13 / §14。

---

## 3. 缺陷 C：识别骨架「值」字段恒空 → 数据值展示归位（用户提问发现）

### 现象
用户在实验档案详情页看到每个列块表格里有「值」列（`ArchiveDetailView.vue:148`），
但**整列永远为空**（显示 `—`），提问"值存在哪里了"。

### 根因（契约错位，非数据丢失）
- 该列绑定 `col.value`（`ArchiveDetailView.vue:158`），而后端**硬编码为空字符串**：
  `app.py:239`（`build_block_payload`）与 `app.py:284`（`degraded_block_payload`）均为 `"value": ""`，
  **全链路无任何写入路径**。
- 语义不匹配：一个「列」对应**多行**值（如 G 列 22 个非空值），列级结构承载不了单个「值」；
  且识别阶段**本就不持有数据值**（数据值在归档时由 `build_canonical` 以 `data_only=True`
  重读原始文件 + 引擎复算，见 §6 数据流说明）。
- 同一错位的**第二处**：识别页 `DynamicForm.vue` 的同名列是输入框，但其 `edited` 仅是组件内
  `reactive({})`，**无 emit / 无提交 / 不进任何 API**（全仓 grep 仅 4 处、全在组件内）→ 输入刷新即丢。

### 数据值实际所在（对用户提问的回答）
| 位置 | 内容 |
|---|---|
| `data/raw/{session}__{file}.xlsx` | 原始全量值（唯一无损真相源） |
| `experiments.processed_json → canonical.rows` | 归档时重读 + 复算的**规整值**（`-003` 实测 34 行 × 25 列） |
| `GET /v1/experiments/{id}/data/canonical`、`/canonical/csv` | 对外取用接口 |

前端此前**没有任何页面展示 canonical**（grep 仅 `ApiDocsView.vue:101` 提及）→ "值已存，但界面看不到"。

### 修复（3 处）
| 层 | 文件 | 改动 |
|---|---|---|
| 前端 | `data/api.js` | 新增 `getCanonical(id)` |
| 前端 | `views/ArchiveDetailView.vue` | 「值」列 → **填充证据**（`nonNull · fillRatio%`）；新增**规范长表区块**（渲染 `canonical.rows`，列清单取自后端 `canonical.columns` 不硬编码，>100 行截断提示 CSV） |
| 前端 | `components/DynamicForm.vue` | 移除恒空且不保存的「值」输入框与 `edited` 副本 → 同一填充证据展示（行网格 7 列收为 6 列） |

### 验证
- `npm run build` 通过（64 modules，204 ms）。
- API 实证：`GET .../RES-20260921-003/data/canonical` → **34 行 × 25 列**，`columns` 与后端 `CANONICAL_COLUMNS` 完全一致。
- 真实数据差异：`-002`（新快照）显示 `0 · 0%`；`-003`/`-001`（旧快照）显示 `—`（如实表示"未透传证据"，**不伪造数字**）。
- `verify_fieldstate.mjs` 8/8 通过（`fieldState` 未改动，无回归）。
- `RecognizeView.vue:338` 仅依赖 `regions/selected/@select` → 移除 `edited` 未破坏调用方。
- 已在内置浏览器打开 `http://localhost:5173/#/archive/RES-20260921-003` 目视（tab `tab_mucdvwnc_4`）。

### 设计含义
「值」在语义上必须是**逐行**的。列级要么展示统计证据（填充率），要么去长表看真实数据；
把恒空字段当数据值展示会让用户误判"数据丢失"。已记入 changelog §17（v1.4）。

---

## 4. 缓存「规则层版本号」机制（本日新发现并修复的隐患）

- **隐患**：识别缓存（`data/cache/{sha}__{sheet}.json`）存的是**最终 payload**（已含规则层结论）。
  若不校验版本，规则升级会被旧缓存**整体绕过** —— §2 的确定性修复对已缓存文件形同虚设。
- **实现**：新增 `RECOGNITION_RULE_VERSION = "rules_v2_missing_header"`，写入 payload 的 `source.ruleVersion`；
  命中缓存时版本不一致即**视为未命中并重算**。
- **实证**：现存 2 个缓存文件（`...__0305-600.json`、`...__default.json`）**均不含** `ruleVersion` → 下次上传会正确失效重算。
- 已记入 changelog §16。

> ⚠️ 若下次上传该文件，会因缓存失效**触发一次真实 LLM 识别**（历史冷启动约 80 s），属预期行为。

---

## 5. 科学发现

新增 **RO-005**（表头缺失列的确定性身份推断与派生关系识别），含 L1 证据表、逐点验证、
跳变实测、Gap、实验设计、目标会议。详见 `docs/research-opportunities.md`（版本记录已更新）。
同时 `docs/session-logs/session-log-2026-09-21.md` 第 8 项已追加「2026-09-22 更正」块。

---

## 6. 验收结果

### 5.1 09-21 的前端修复（统计全为 0 / 返回按钮）
用后端 API 实证详情页数据源（我无可驱动点击的浏览器工具，故以「后端实证 + 代码核对 + 目视」验收）：

| 实验 | 详情接口 | 统计（regions/blocks/cols/mapped/low） |
|---|---|---|
| RES-20260921-003 | 200 | **3 / 4 / 17 / 14 / 3** |
| RES-20260921-001 | 200（120 ms） | 3 个数据区 |
| RES-20260921-002 | 200（7 ms） | 3 个数据区 |

- 统计**非 0**，与 `ArchiveDetailView.vue` 的 `computed` 逻辑一致 → 修复有效。
- 首次请求 `-001` 曾 15 s 超时，重试后 **120 ms** 成功 → 那是**后端刚重启后的冷请求**（首导入），**非缺陷**。
- 已在内置浏览器打开 `http://localhost:5173/#/archive/RES-20260921-003` 供目视（tab `tab_mucdvwnc_4`）。

### 5.2 构建与代码核对
- `npm run build`（`expresin-portal/`）通过：`✓ 64 modules transformed`、`✓ built in 191ms`，无错误。
- `DynamicForm.vue` 对新语义已核对：`toneOf` pending→warning、`stateLabel` 含 pending/missing 无回归；
  但本日后续因**缺陷 C** 移除了恒空的「值」输入框（placeholder 分支随之删除），见 §3。
- 归档快照未被新规则误伤：`-003`/`-001` 快照仍为旧格式（无 `nonNull`），其空 `target` 列均为
  「有表头但无数据的离子标签列」（A='SO4'、E='Cl'）或人工 ignore 列，**非**本规则场景；
  `-002` 因 09-22 重新处理而含 `nonNull/fillRatio/valueType`，说明新规则已在真实链路上产出。

---

## 7. 文件变更清单

| 文件 | 变更 |
|---|---|
| `expresin-pipeline/server/app.py` | 新增 `RECOGNITION_RULE_VERSION`；缓存命中校验版本；`column_data_evidence`；`build_block_payload` 空表头不映射；`degraded_block_payload` 透传证据；`review_recognized_column` degraded→422 |
| `expresin-portal/src/data/demo.js` | `fieldState` 幽灵列收窄；`collectIssues` failedBlocks 加 `scope:'block'` |
| `expresin-portal/src/data/api.js` | 新增 `getCanonical(id)` |
| `expresin-portal/src/views/ArchiveDetailView.vue` | 「值」列 → 填充证据；新增规范长表区块 |
| `expresin-portal/src/components/DynamicForm.vue` | 移除恒空的「值」输入框与 `edited`；改为填充证据 |
| `expresin-portal/src/components/MappingInspector.vue` | `total` 排除 failedBlocks；`isBlockFailed` 分支 |
| `expresin-portal/src/views/RecognizeView.vue` | `pendingTotal`/`failedTotal` 解耦；徽标文案 |
| `docs/design-changelog.md` | **v1.3**（§13–§16）、**v1.4**（§17 缺陷 C） |
| `docs/research-opportunities.md` | 新增 **RO-005** |
| `docs/session-logs/session-log-2026-09-21.md` | 第 8 项追加更正块；遗留项状态标注 |
| `.deepworks/tmp/verify_rule_determinism.py`、`verify_fieldstate.mjs`、`probe_archive_snapshot.py` | 只读/离线验证脚本 |

---

## 8. 遗留 / 待办（下次接手起点）

1. **端到端真实验收未跑**：本日规则修复为**离线验证**（真实数据 + 真实函数，零 LLM）。
   若需端到端确认，重新上传 `20250528 DHT Cl SO4.xlsx`（会因缓存失效触发 1 次 LLM 识别，约 80 s），
   预期：G 列 `target=None`、`nonNull=22`，`source.ruleVersion="rules_v2_missing_header"`。
2. **后端 422 分支未经真实数据触发**：真实档案当前无 `degraded` 块，仅代码审查 + 构造论证；
   需构造一个识别失败的块，或以单测覆盖 `review_recognized_column` 的 degraded 路径。
3. **09-21 遗留第 3 项**：`design-changelog` 仍未记录 09-21 的 3.2/3.3/3.4（前端流转 / 统计修复 / 返回按钮）。
   本日已补 v1.3 的 W8 部分，是否补记该三轮仍待定。
4. **09-21 遗留第 7 项**：三个 UI 信号仍未完整实测（离子判定冲突、缓存命中、failedBlocks 降级）。
5. **返回按钮**的吸顶（sticky）问题仍待定（09-21 遗留第 2 项）。
6. **安全**：`.env` 中 `DEEPSEEK_API_KEY` 已明文出现在会话中，**需轮换**（09-21 遗留第 13 项）。
7. 09-21 遗留第 9~12 项（冷启动进度、`canonical.py` 清理、`0121` 近零点汇总、准确率验证暂停）**未处理**。
8. ✅ **缺陷 C 已修**：档案页「值」列改为填充证据 + 新增规范长表区块；识别页无效输入框移除。
   仍缺：规范长表无分页 / 无导出按钮（当前截断 100 行 + 提示走 CSV 端点）。

---

## 9. 下次开工建议顺序

1. 确认前后端存活（`/api/health`、`localhost:5173`）；后端改过代码先重启。
2. 若要端到端收口本日修复，做第 8 节第 1 项的真实上传验收。
3. 补第 8 节第 2 项的 422 路径测试。
4. 决定是否推进 RO-003 / RO-004 / RO-005，以及是否补记 changelog 的更早改动。