# ExpResin 会话日志 · 2026-10-10

> 用途：记录当日工作状态、启动/停止方法与遗留事项，供下次接手时快速恢复上下文。
> 本日主题：**W9 Benchmark「幻觉任务」探针 v0 + 类型一致性提示落地**，并回填 09-25~10-09 的日志空缺。
> 老规矩：**跨会话状态一律以实际检查为准（代码 / 端口 / HTTP 探测），日志仅作线索**。

---

## 0. 服务状态与下次快速重启

**本日收工状态（2026-10-10 晚，实际探测确认）：前后端均已停止 —— 端口 8000 / 5173 无监听。**

快速重启命令与 09-24 日志 §0 完全一致（后端 uvicorn + 前端 node 直启 vite）。
补充：`dev.ps1` 已被前人修复为直接调 `node node_modules\vite\bin\vite.js`，
`.opencode/skills/expresin-dev/scripts/dev.ps1 start|stop|status` 现在可正常使用（09-24 遗留 #6 已消化）。

---

## 1. 空缺回填：09-25 ~ 10-09（依据未提交改动 + design-changelog §20-26 + 实测事实）

这段期间工作全部未写日志、**且全部未提交 git**（HEAD 停在 09-24 `e34a0d8`，
git status 现有 41 项改动 + 大量新增文件）。按可考事实回填：

| 日期 | 事项 | 证据 |
|---|---|---|
| ~09-25 | T3 记录模板：`config/record_templates/`（batch/column/electrochemical 三份 record_v1.json）+ 生成脚本 `scripts/make_record_templates.py` + 样例 `materials/record-templates/*_example_filled.xlsx` | 未提交文件 |
| ~09-25 | `standard_schema.json` 补 `potential_v` / `current_a`（electrochemical 枚举缺口关闭，09-24 遗留 #2 部分消化） | schema 实测 |
| 10-02 | UI 升级 P0–P3 全部完成（新增 BaseModal/ChatMessage/ConfirmChip/IssueList/StatGrid 等 12 个组件 + domain/ 层 + WorkbenchLayout 改版，删 HelloWorld/Inspector/TopBar） | design-changelog §20-26、`ExpResin-UI-Upgrade-Plan-v2.0.md` |
| ~10-02 | NAS 适配器 v1：`src/nas_adapter.py`（Protocol + LocalDirAdapter）+ `scripts/publish_nas.py`；归档时自动发布（app.py:902 调 `publish_experiment`，失败降级不影响归档）；`data/nas_mirror/` 已有 6 个实验镜像 | 代码 + 镜像目录实测 |
| 10-10（早间） | 三模板后端映射准确度测试：100%（14/14，conf 0.92-0.99，cached=False） | `outputs/template-mapping-accuracy.md` |

## 2. 本轮工作（10-10）

### 2.1 W9 幻觉任务探针 v0（新任务卡，已交付）

- 脚本：`expresin-pipeline/scripts/benchmark_hallucination.py`（支持 `--only batch|column|electrochemical`）
- 报告：`docs/benchmark-hallucination-v0.md`；原始 JSON：`.deepworks/tmp/hallucination/hallucination_result.json`
- 设计：三模板 × 五变体（V0 基线 / V1 无语义表头 / V2 表头移位 / V3a 空表头 / V3b 数字表头），总 token 50625
- **核心结果**：
  - V0 基线 100%（14/14）
  - **V1 幻觉率 100%（14/14 列全部被臆造映射）**，其中 5 列 conf≥0.8（最高 0.97）；幻觉 evidence 全是数据形态统计（「数值范围6.85-7.21，典型pH值」）
  - V2 语义服从率 100%，且表头-数据冲突时 conf 跌至 0.30-0.40（模型有冲突感知，但无语义时反而高置信 → 置信度对证据类型失校准）
  - V3a/V3b 均被 **L1 结构层整块拦截**（数字/空表头行不产出 region，零 LLM 消耗）——09-22 修复的防护证据
- 结论：当前幻觉防护完全系于 L1 结构层；形态合法但语义空白的表头一旦进入 LLM，必被臆造。已登记 **RO-014**（research-opportunities.md，含实验方案：温度×reasoning×证据结构化提示词多因素实验）。

### 2.2 类型一致性提示（09-24 遗留 #3，已落地）

- 新模块：`expresin-pipeline/src/checks.py`（纯函数、确定性、不落库）
  - 规则保守：只做「禁止字段」检查（batch 不应有 bed_volume/potential_v/current_a 等），不做正向断言
  - conf 阈值 0.8（与幻觉探针高置信线一致）
- 接入：`GET /v1/experiments/{id}` 响应新增 `warnings` 数组（随取随算）
- 实测：`RES-20260921-003`（声明 batch，含 2 列 BV，conf 0.98）→ 命中 1 条 warning，建议核对是否应为 column；其余 3 个实验 0 误报
- **未做**：前端展示接线（ArchiveDetailView 读 `warnings` 即可，下一轮做）

### 2.3 dev.ps1 遗留项

09-24 遗留 #6：验证发现前人已把 dev.ps1 改为 node 直启，直接从遗留清单划掉。

## 3. 环境事实与口径风险（新增）

- 幻觉探针的变体文件生成在 `.deepworks/tmp/hallucination/`（不进 git）。
- `requests` 库仍未安装；脚本一律用标准库（openpyxl + urllib）。
- 口径风险备忘（与 10-10 早间测试相同）：electrochemical `Time (s)`→`contact_time` 存在 s/min 量纲隐患，gold 如此声明故判对，但导出/计算链路需留意单位换算。
- PowerShell 控制台显示中文乱码是显示层问题（Invoke-WebRequest 按 ISO-8859-1 解码），服务端 JSON 实际正常；脚本内用 `sys.stdout.reconfigure(encoding='utf-8')`。

## 4. 遗留待办（更新版）

1. **git 提交**：09-24 后全部工作未提交（41 项改动 + 新增）。按项目工作流应每个任务卡验证后英文 commit；建议拆 3-4 个 commit：UI 升级 / T3 模板+NAS / 映射测试产物+幻觉探针+checks。**等用户确认后执行。**
2. 前端展示 `warnings`（ArchiveDetailView，读 detail API 新字段）。
3. canonical 长表分页（09-24 遗留 #4，未做；CSV 导出已有）。
4. RO-014 实验方案落地：幻觉探针扩展（温度梯度 / reasoning 配额 / 证据结构化提示词 / abstain 指令）。
5. NAS 信息待用户后补；中央大脑对接本阶段搁置。
6. electrochemical 单位换算口径（s vs min）确认。

## 5. 下次开工建议顺序

1. 读本日志 + 09-24 日志；状态一律实际探测。
2. 先处理 git 提交（§4.1，问用户）。
3. 若继续 W9：做 RO-014 的提示词对照实验（探针可直接复跑）。
4. 若做体验：前端接 warnings 展示（半天内可完）。
