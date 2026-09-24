# ExpResin 会话日志 · 2026-09-21

> 用途：记录当日收尾状态、启动/停止方法与遗留事项，供下次接手时快速恢复上下文。
> 本日前的运行日志已归档，见第 6 节。
> **后续进展见 `docs/session-logs/session-log-2026-09-22.md`** —— 已处理本日遗留**第 5 项（failedBlocks→404）**与**第 8 项（幽灵列非确定性）**。

---

## 0. 本日收尾状态

| 服务 | 版本 | 启动时间 | PID | 监听地址 | 收尾状态 |
|---|---|---|---|---|---|
| 前端 Vite dev server | v8.3.0 | 21:12:54 | **7000** | `::1:5173`（仅 IPv6） | ✅ 已停止 |
| 后端 uvicorn (FastAPI) | — | 22:27:20 | **25808**（启动器 shim **27400**） | `127.0.0.1:8000` | ✅ 已停止 |

停止方式与校验：

| 检查项 | 结果 |
|---|---|
| 端口 5173 / 8000 | 均已释放 |
| 残留 vite / uvicorn 进程 | 无 |
| `GET /api/health`、`GET :5173/` | 均不可达（符合预期） |
| SQLite `PRAGMA quick_check` | `ok` |
| SQLite sha256 停止前后 | **一致**（`b3f94597a02c2e72156a3d949d05b18df1c0c9425ef535e5e136d1296068477d`） |
| SQLite 残留 `-journal` / `-wal` / `-shm` | 无 |
| 各表行数停止前后 | 一致 |

停止顺序为「先前端、后后端」，避免停止过程中仍有在途请求。

> **说明**：后端是后台进程、无控制台，Windows 下无法投递 Ctrl+C，实际以 `Stop-Process -Force` 终止。
> 这样做是安全的，依据是两点实测：① 后端代码中**不存在** `lifespan` / `on_event` / `shutdown` 钩子（grep 无结果），没有需要优雅清理的资源；② SQLite 为 `journal_mode=delete`，事务提交即落盘，终止后 `quick_check=ok`、sha256 不变、行数不变，已证明无损坏。

---

## 1. 下次如何启动

### 前端

```powershell
powershell -File .opencode/skills/expresin-dev/scripts/dev.ps1 start
```

- 访问地址：**`http://localhost:5173/`**
- 注意：只监听 IPv6，用 `127.0.0.1:5173` **会拒连**，必须用 `localhost`
- 状态 / 日志：`dev.ps1 status`、`dev.ps1 logs`（写 `expresin-portal/.dev-logs/vite.log`）

> ⚠️ **Vite 具备 HMR。修改 `src/` 下任何代码都不要重启 dev server**，只有新增依赖、改 `vite.config.js`、端口冲突或崩溃时才 `restart`。

### 后端

```powershell
Start-Process -FilePath "python" `
  -ArgumentList "-m","uvicorn","app:app","--app-dir","expresin-pipeline\server","--port","8000" `
  -WorkingDirectory "D:\ExpResin Project Redesign" `
  -RedirectStandardOutput ".deepworks\tmp\api.log" `
  -RedirectStandardError  ".deepworks\tmp\api.err.log" `
  -WindowStyle Hidden
```

健康检查：`http://127.0.0.1:8000/api/health` → 期望 `{"status":"ok",...}`

> ⚠️ **`-RedirectStandardOutput` 会覆盖日志**。若要保留上一次运行记录，先复制 `.deepworks\tmp\api.log`，再启动。
> ⚠️ 后端改了 Python 代码**必须重启**（未使用 `--reload`）；前端改了则不用。

---

## 2. 停止前状态快照

**数据库**：`expresin-pipeline/data/expresin.db` — 331,776 字节

| 表 | 行数 |
|---|---|
| confirmation_log | 205 |
| experiments | **6** |
| form_drafts | 82 |
| messages | 90 |
| session_assets | 26 |
| sessions | 52 |

**6 条已归档实验**：

| 实验编号 | 会话 | 原始文件 | 创建时间 |
|---|---|---|---|
| RES-20260919-001 | ses_5970855db2ae | — | 2026-09-19 22:26:39 |
| RES-20260920-001 | ses_e27aac444664 | — | 2026-09-20 23:05:28 |
| RES-20260920-002 | ses_5b4f808b9889 | — | 2026-09-20 23:13:44 |
| RES-20260921-001 | ses_e3f63803d415 | `20250528 DHT Cl SO4.xlsx` | 2026-09-21 00:24:50 |
| RES-20260921-002 | ses_f60b7f19b7d1 | — | 2026-09-21 00:40:39 |
| RES-20260921-003 | ses_e5cad63018db | `20250528 DHT Cl SO4.xlsx` | 2026-09-21 21:23:24 |

---

## 3. 今日完成的工作

### 3.1 W7：科学计算引擎 + 规范长表（后端，已端到端验证）
- `src/compute.py`：摩尔质量表、单位换算、`linear_fit`、`removal_rate`、`adsorption_capacity_mg_g`（含物理校验：`c0<=0` 拒绝、`ce<0` 拒绝、`ce>=c0` 拒绝）。`CALCULATION_VERSION="compute_v1"`。
- `src/canonical.py`：`build_canonical()`、`render_csv()`、`render_markdown()`；标定归属用**稳健中位数 + 近零点剔除**评分，劣质候选显式标注。
- `server/app.py`：新增 `GET /v1/experiments/{id}/data/canonical` 与 `.../canonical/csv`；`/confirm` 接线 `raw_path`。

### 3.2 前端页面流转改造（5 处最小改动）
| 文件 | 改动 |
|---|---|
| `server/store.py` | `list_experiments` 投影补 `session_id` |
| `data/session.js` | 新增 `resumeSession(sid)`（续接原会话、清空识别态、回填表单） |
| `views/RecognizeView.vue` | 支持 `?session=` 续接 |
| `views/ArchiveView.vue` | `targetOf(row)`：无数据表格的档案 → `/recognize?session=` |
| `views/SetupView.vue` | 归档后跳转 `/recognize` |

### 3.3 归档详情页「统计全为 0」修复
- **根因**：详情页读 `record.regions`，但档案**列表**接口不含 `regions`，且合并语句 `regions: found?.regions` 又把它覆盖回 `undefined`；`experiments` 表本身从不持久化 `regions`。
- **修复**：改为读详情接口的 `processed.recognized_data.regions`（识别快照实际存放处）。**纯前端、单文件**。

### 3.4 档案详情页新增「返回实验档案」按钮
- 复用全局 `.btn .btn-secondary`，**零新增设计令牌**；把原来不可发现的小号面包屑升级为明确按钮。

### 3.5 文档
- `docs/design-changelog.md` → **v1.2**（新增 §10 规范长表、§11 不确定性显式暴露原则、§12 只读数据端点表）
- `docs/research-opportunities.md` → 新增 **RO-003**（幻影浓度与近检出限偏差）、**RO-004**（标定归属自动推断），均 P1

---

## 4. 验证证据摘要

| 验证项 | 结果 |
|---|---|
| `/confirm` → 生成 `RES-20260921-001` | 200，`canonical.rows=34`、`notes=5` |
| `GET .../data/canonical` | 200，`schema=canonical_table_v1`、`version=compute_v1`、rows=34 |
| `GET .../data/canonical/csv` | 200，6870 B，`text/csv; charset=utf-8`，34 行 × 25 列 |
| `GET .../data/processed/markdown` | 200，10496 字符，5 个新章节齐备 |
| 会话续接链路 | `ses_e27aac444664→RES-20260920-001`、`ses_e5cad63018db→RES-20260921-003`，form-state 10/10 字段 |
| 详情页统计（修复前） | 6 条实验**全部为 0**（复现用户现象） |
| 详情页统计（修复后） | `-001`/`-003` → 数据区 **3**、列块 **4**、已映射 **14/17**、低置信 0 |
| 返回按钮 | `npm run build` 通过（223ms）；dev server 模块与 scoped 样式 6/6 命中 |
| 后端运行日志 | 全程 **无 500**，仅 1 个 404（「该会话尚无识别列」的预期语义） |

---

## 5. 未完成 / 已知问题（下次接手起点）

**待用户确认**
1. 详情页「返回实验档案」按钮的**实际渲染未经点击验收**（我无可驱动浏览器的工具）；若 HMR 未刷新，F5 即可。
2. 该按钮位于页面顶部、**随内容滚动**。详情页内容较长，是否需要改为**吸顶（sticky）**待定。
3. `docs/design-changelog.md` **未记录** 3.2 / 3.3 / 3.4 三轮前端交互改动（按「不要改动其他方面」暂缓），是否需要补记待定。
   > **2026-09-22**：changelog 已补 **v1.3**（W8 部分，§13–§16）；3.2 / 3.3 / 3.4 三轮仍待定。

**已知缺陷 / 遗留**
4. `RES-20260921-002` 详情统计仍为 0 —— 它在**上传数据之前**就归档了，归档记录里没有识别快照。属「归档记录 = 归档时刻快照」的既有语义，**非缺陷**；若要回填，需新增后端端点去读会话最新识别资产（超出当前范围）。
5. `pendingTotal` 已计入 `failedBlocks`，但 `failedBlocks` 项的 `col: 'block'` 走列级通道仍会 **404**。
   > ✅ **2026-09-22 已修复**：failedBlocks 与列级计数解耦（加 `scope:'block'`），后端对 degraded 块的列级判定改返回 **422 + 可操作提示**。见 `session-log-2026-09-22.md` 第 1 节。
6. `DynamicForm.vue` 使用 `fieldState`，对 `remapped` / `ignored` / `block-failed` 的容错**未确认**。
   > ✅ **2026-09-22 已核对**：`toneOf`（pending→warning）、`stateLabel`、placeholder 分支在新语义下均无回归，无需改动。
7. 三个 UI 信号**未完整实测**：离子判定冲突、缓存命中、failedBlocks 降级。
8. **幽灵列行为不稳定**：`0305-600#R44-44/B1` 的 `G ''` 曾在 `concentration_mg_l`(0.7) 与 `None`(0.2) 间跳变（LLM 非确定性）。

   > ⚠️ **2026-09-22 更正（实测推翻了「幽灵列」这一描述）**
   >
   > G 列**不是空列**。L1 结构证据：`value_type=number`、`fill_ratio=1.0`、`non_null=22`、
   > `numeric_range=[0.0, 2249.76171784]`，且数值上**严格等于 E 列（`calculated  ppm`，表内自算）× 100**（稀释倍数）：
   > E=`8.7451006944` → G=`874.5100694399999`；E=`22.4976171784` → G=`2249.76171784`。
   >
   > 它实际是「**无表头但有完整数据的派生列**」（稀释 100 倍后的原液质量浓度），
   > 此前把它当作"整列为空的幽灵列"是**错的**（`demo.js` 中的演示数据同此描述有误）。
   >
   > 6 次识别快照（`session_assets` · `recognized_blocks`）实测跳变：
   > **4 次 → `concentration_mg_l`(0.70/0.72)、2 次 → `None`(0.20)**，即**同输入、同模型下的非确定性**。
   >
   > 缺陷实为两层：① 列级映射在**表头缺失**时非确定性；② 前端 `fieldState` **仅按 `raw` 是否为空判定**，
   > 把所有"空表头有数据列"一律误标为"幽灵列"。
   >
   > 科学发现已登记为 **RO-005**，见 `docs/research-opportunities.md`。
   >
   > ✅ **2026-09-22 已修复**：空表头列在规则层一律 `target=None`（模型候选写入 `evidence`），
   > 前端「幽灵列」收窄为「空表头**且**无数据」；离线验证证明决策字段已确定性收敛。
   > 见 `session-log-2026-09-22.md` 第 2 节。
9. **冷启动仍无分块级进度**，只有秒表；最近一次冷启动上传 80.2 s。
10. `canonical.py` 遗留：`_FIELD_TO_COLUMN` 未被使用（仅留档）；`_build_samples` 内 `value_of` 为循环内闭包。
11. `0121` 的 `summary` 仍包含全部 11 个近零点（mean 26.49 / median 0.0044），是否在汇总层排除近零点**未决定**。
12. **准确率验证已由用户选择「先暂停」**（当前数字：列级 100% / 129；唯一有客观真值的 analyte 指标 84.6%；仅同源域内，泛化未验证）。

**安全**
13. `.env` 中的 `DEEPSEEK_API_KEY` **已明文出现在会话中，需轮换**。

---

## 6. 日志归档

运行日志会在下次启动时被覆盖，故停止前已归档至：

```
.deepworks\tmp\archive\2026-09-21\
```

| 文件 | 大小 | 原始位置 |
|---|---|---|
| `api.log` | 15,876 B | `.deepworks/tmp/api.log`（后端访问日志，189 行） |
| `api.err.log` | 885 B | `.deepworks/tmp/api.err.log`（启动信息 + 1 次客户端断开噪声） |
| `vite.log` | 2,096 B | `expresin-portal/.dev-logs/vite.log`（启动 514ms + HMR 记录） |
| `vite.err.log` | 0 B | `expresin-portal/.dev-logs/vite.err.log`（空） |
| `pre_stop_state.json` | — | 停止前快照（含 DB 哈希、完整性、行数、实验清单） |
| `post_stop_state.json` | — | 停止后快照（用于哈希/行数比对） |

`api.err.log` 中唯一一处异常是 `ConnectionResetError: [WinError 10054]` —— 客户端（浏览器）主动断开连接产生的 asyncio proactor 噪声，**非业务错误**，可忽略。

**未清理的历史日志**（未删除，供你决定）：
`.deepworks/tmp/api.out.log`（09-20）、`api2.log` / `api3.log`（09-19）、`expresin-portal/.dev-logs/vite.out.log`（09-21 00:44）。

---

## 7. 下次开工建议顺序

1. 按第 1 节启动前后端，先跑一次 `/api/health` 确认。
2. 打开 `http://localhost:5173/#/archive`，验收 3.3 / 3.4 两处前端修复（详情页统计非 0、左上角返回按钮）。
3. 处理第 5 节的第 5、8 项（都是同一条「幽灵列 / failedBlocks」链路上的确定性问题）。
4. 决定是否补记 `design-changelog`，以及是否推进 RO-003 / RO-004 的科研工作。