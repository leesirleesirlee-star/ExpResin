# ExpResin 会话日志 · 2026-09-23

> 用途：记录当日工作状态、启动/停止方法与遗留事项，供下次接手时快速恢复上下文。
> 本日主题：**导师新要求落地 —— 三实验类型模板填充链路（T1）+ 科研机会「主动发现」方针**。
> 承接 09-22 缺陷 C 收尾与客户展示；本日新开任务卡 T1（后端模板链路，全程离线可验证）。

---

## 0. 本日收尾状态（服务仍在运行中）

| 服务 | PID | 监听地址 | 状态 |
|---|---|---|---|
| 前端 Vite dev server | **14800** | `::1:5173`（仅 IPv6） | ✅ 运行中 |
| 后端 uvicorn (FastAPI) | **17496** | `127.0.0.1:8000` | ✅ 运行中（health ok） |

- 前端由用户自行启动（`dev.ps1 start` 曾超时）；`dev.ps1 status` → `RUNNING http://localhost:5173/ (pid 14800)`。
- `GET /api/health` → `{"status":"ok","service":"expresin-portal","version":"0.1.0"}`。
- 用户已完成客户展示。

> ⚠️ Vite 有 HMR，改 `src/` 不要重启 dev server；后端无 `--reload`，改 `app.py` 必须重启。

---

## 1. 导师新要求（本日核心）

1. 系统须支持**三种实验类型**：Batch / Column / Electrochemical；
2. 识别完成后，数据按**对应模板**填入；
3. 汇总到 **NAS 服务器**；
4. 提供 **API 供"中央大脑"调用**；
5. **导师提醒**：研发过程中要**尽量发现"树脂话语体系下的计算机相关科研问题"**。

### 用户决策（两轮 question）
| 问题 | 决策 |
|---|---|
| 输出格式 | **Excel `.xlsx`** |
| NAS | 先落本地目录 + 预留适配器，NAS 信息后补 |
| 中央大脑 | 本阶段先不考虑 |
| 原始数据表样例 | **无样例，由我们设计**（按模板 B 区反推） |
| 多离子 | **一个实验一个 Excel，多离子分多个 sheet** |
| 浓度口径 | **引擎复算优先，缺失回退原表值**（导出标注） |
| 模板细节 | "参考设计由你决定，不确定的问我" |

---

## 2. 本日交付：T1 模板填充链路（54 项离线验证全通过）

### 2.1 新增文件
| 文件 | 内容 |
|---|---|
| `expresin-pipeline/config/templates/batch_template_v1.json` | 三套模板配置（A/B/C 段落、role 语义、from 路径、data_policy） |
| `.../column_template_v1.json` | 同上；C 区 "Automatically Calculated" |
| `.../electrochemical_template_v1.json` | 同上 |
| `expresin-pipeline/src/derive.py` | **derive_v1** 派生计算（阈值集中、每项带 method） |
| `expresin-pipeline/src/template_fill.py` | **fill_v1** 填充器（Raw 重读 + 多离子分组 + 单位换算） |
| `expresin-pipeline/src/template_export.py` | **export_v1** Excel 导出（A/B/C + 规则 + Provenance） |

### 2.2 关键实现决策
- **数据值从 Raw 重读**：识别快照不含数据值（09-22 缺陷 C 结论），复用 `canonical._locate/_read_column`。
- **多离子分 sheet**：按 `block.analyte` 分组，展示保留原写法（"Cl" 非 "CL"）。
- **单位处理**：`time/h` → h（1 h = 3600 s，留痕）；无法识别 → **原样传递 + 提示人工核对**（禁止猜测换算）。
- **浓度口径**：engine_first（按 块+Excel行号 对齐 canonical），回退 ppm 原值时标注 `ppm≈mg/L`。
- **缺输入降级**：`value=None + reason`（如缺 flow_rate → 处理体积不可算；缺电极面积 → 电流密度不可算）。

### 2.3 验证证据
```
==== 54 passed, 0 failed ====
- Part 1 derive 单元测试（手算对照）：batch Ce=29.8 / 去除率 70.2% / qₑ=35.1 / 平衡 1800s；
  column 穿透 600s / 耗尽 2400s / 处理体积 200mL / 20 BV；ec 电荷 15C / 能耗 30J / 密度 0.5
- Part 2 真实数据回归（RES-20260921-003，34 行 canonical）：
  column 路径 → 2 sheets（SO4/Cl）；B 区 11 行；time/h → 输出 600 min ✓；C 区 Cₜ/C₀=0.008314
  batch 路径 → 去除率 99.17% / qₑ=59.50 mg/g / 平衡时间 120 min
  A 区：experiment_id / C₀=120 / 树脂 100mg / A001 ✓
- Part 3 合成 electrochemical 端到端：5 行 × 5 列；电荷 69C / 能耗 207J / 去除率 87.5% / 密度 0.13
```
验证脚本：`.deepworks/tmp/verify_template_fill.py`；产物：`.deepworks/tmp/fillout/*.xlsx`。

---

## 3. 科研机会：「主动发现」方针落地（导师提醒）

- `docs/research-opportunities.md` 新增**方针小节**：由"被动登记"升级为"主动发现"，
  附 4 条判别标准（经验阈值 / 多策略未量化 / 人肉可自动化 / 系统性偏差或非确定性）。
- 新登记 4 条（均来自本轮工程实践，v3）：

| 编号 | 主题 | 触发点 |
|---|---|---|
| RO-006 | 穿透/耗尽/平衡事件的稳健检测与不确定区间 | derive.py 经验阈值（5%/95%/连续2点）对非均匀采样与噪声脆弱 |
| RO-007 | 记录值 vs 复算值冲突的谱系裁决 | engine_first 是单向优先级，缺证据化裁决 |
| RO-008 | 自由文本实验方案 → 可执行数据契约的编译 | 三份老师模板人工转 JSON，命名/单位不一致 |
| RO-009 | 离子价态感知的当量换算与量纲校验 | 跨模板单位换算 + ppm≈mg/L 假设缺少显式建模 |

- **主动扫描第二轮（同日追加）**：按 4 条判别标准对 `llm.py` / `mapping.py` / `l1_structure.py` /
  `canonical.py` / `derive.py` / `server/services.py` / `compute.py` 七个模块逐一扫描；
  方针再升级：新增**发现雷达**（树脂话语区 → 问题族 → RO 对照表）、**每轮扫描清单**（6 条）、
  草案登记模板与观察池 2 条（缓存可复现性、改判传播）。新登记 4 条（v4）：

| 编号 | 主题 | 触发点 |
|---|---|---|
| RO-010 | 多块异构实验表的确定性结构切分与块类型判定 | L1 启发式：表头判定 / `blank_tolerance=3` / 空列分块 / 关键词块类型；块 ID 依赖行号，解析器升级后历史快照静默失配 |
| RO-011 | Trace as State 的条件增益与自适应推理预算 | `map_block(use_trace=False)` 默认关闭，两轮增益从未在本任务测量；pro reasoning≈1323 tokens |
| RO-012 | 平衡浓度（Ce）的平台估计与 q 的不确定度传播 | `derive`/`canonical` 均取"最后一个有效/正浓度点"作 Ce，未做平台估计与误差传播（与 RO-006 时间判定互补） |
| RO-013 | 人工改判的检索化复用（草案，P2） | "人工确认不是重训" + FR-05 示例库尚未接回识别链路 |

---

## 4. 数据观察（待后续处理）

1. **声明类型 vs 数据结构不一致**：`-003` 表单类型是 `batch`，但数据表含 `bed_volume (BV)` 与
   `time/h`（小时级）列；浓度序列为动力学衰减（46.4 → 1.09 → ~1.0 ppm），与 batch 判定一致，
   但 BV 列的存在提示：**类型选择错误会导致模板填错区域**，建议后续加类型一致性提示。
2. `contact_time` 原始单位 `time/h`（小时），此前被降级处理；本次修复后可正确换算（B 区 10 h → 600 min）。
3. 样本浓度另有两列（`稀释2倍(mol/L)`、表内自算），填充时优先 `concentration_ppm` 列 + canonical 复算值，
   **不混用摩尔浓度列**（避免量纲混用，见 RO-009）。

---

## 5. 文件变更清单

| 类型 | 路径 |
|---|---|
| 新增（配置） | `expresin-pipeline/config/templates/{batch,column,electrochemical}_template_v1.json` |
| 新增（代码） | `expresin-pipeline/src/{derive,template_fill,template_export}.py` |
| 新增（文档） | `docs/session-log-2026-09-23.md`（本文件） |
| 更新（文档） | `docs/research-opportunities.md`（方针 + 发现雷达/扫描清单 + RO-006~013 + v3/v4） |
| 更新（文档） | `docs/design-changelog.md`（§18 + v1.5） |
| 验证脚本（非交付） | `.deepworks/tmp/{probe_cache,probe_db,probe_processed,verify_template_fill}.py` |

---

## 6. 遗留 / 待办（下次接手起点）

1. **T2 候选**：把填充/导出接入服务端（导出端点 + 前端下载入口）；改 `app.py` 需重启后端。
2. **T3 候选**：原始数据表模板设计（用户确认"由我们设计"）+ NAS 适配器预留接口。
3. `standard_schema.json` 扩展：当前 `block_kinds` 与 `experiment_type` 枚举**缺 electrochemical**
   （识别链路仍按旧枚举，模板链路已支持）。
4. 类型一致性提示（第 4 节观察 1）。
5. 09-22 遗留：canonical 长表无分页/导出按钮（截断 100 行 + CSV 提示）。
6. NAS 信息待用户后补；中央大脑对接本阶段搁置。

---

## 7. 下次开工建议顺序

1. 读本日志 + `research-opportunities.md` 方针与「每轮扫描清单」（收尾前对照发现雷达主动扫描科研问题）。
2. 确认 T2/T3 优先级（问用户），再动服务端接入或原始表模板设计。
3. 后端改动后重启 uvicorn（方法见 09-21 日志第 1 节）。

