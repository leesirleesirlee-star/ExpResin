# ExpResin 项目推进规划 v2.0

> 本文继承《第一轮基准：ExpResin 项目宪法》、PRD v1.2、两大新方向规划。  
> 本轮新增三项核心要求：  
> **要求一：ExpResin 不仅是对话 Agent 页面，还必须提供完整 API。**  
> **要求二：实验数据必须能直接推送至更大的大脑（Jarvis-Core 或外部大模型系统）进行分析。**  
> **要求三：其他实验室也能方便调用这套系统，支持多租户、多实验室。**  
> 以下规划围绕这三个要求展开，同时保持与原有所有基准一致。

---

## 一、新要求带来的定位升级

### 1.1 从“一个页面”到“一个平台”

原来的 ExpResin：

```text
研究者 → PortalJarvis 对话页面 → 数据入库 → Jarvis-Core 读取
```

升级后的 ExpResin：

```text
                    ┌──────────────────────────────┐
                    │        ExpResin Platform      │
                    │                              │
研究者 ─对话─→ PortalJarvis ─┐                     │
研究者 ─API──→ Public API ───┤                     │
其他实验室 ─API→ Public API ─┤→ 数据规范化与入库    │
机器人 ─API──→ Public API ───┤                     │
                            │                     │
                            └→ 数据推送/订阅 ─→ 更大大脑（Jarvis-Core / 外部）
```

ExpResin 从“一个项目页面”升级为：

> **面向实验室的、API-first、多租户、可与任意大模型大脑对接的实验数据基础设施。**

### 1.2 三个新身份

| 身份 | 说明 |
|---|---|
| 对话式入口 | PortalJarvis 引导研究者完成实验记录 |
| 数据服务平台 | 通过 API 对外提供数据上传、查询、分析、验证 |
| 数据管道 | 把实验数据推送给更大大脑，等待分析结果回传 |

### 1.3 与原有基准的关系

- 科学不变量不变：Raw 不可覆盖、Processed 可追溯、LLM 做语义/Python 做计算、Benchmark 贯穿、人工确认不是重训。
- Benchmark 方向不变：ExpResin-Bench 继续建设。
- 交互流水线不变：PortalJarvis 继续做对话引导。
- 新增：API 平台化、数据推送、多租户。

---

## 二、总体架构升级

### 2.1 分层架构

```text
┌─────────────────────────────────────────────────────────┐
│  接入层                                                  │
│  ├── PortalJarvis（对话式 UI）                            │
│  ├── Public API（REST / OpenAPI）                        │
│  ├── SDK（Python / JS / CLI）                            │
│  └── Webhook / 消息订阅                                   │
├─────────────────────────────────────────────────────────┤
│  认证与租户层                                             │
│  ├── API Key / OAuth2                                    │
│  ├── 租户隔离（Lab / Project / User）                     │
│  ├── 配额与限流                                           │
│  └── 审计日志                                             │
├─────────────────────────────────────────────────────────┤
│  业务逻辑层                                               │
│  ├── 实验管理                                             │
│  ├── Schema Mapping                                       │
│  ├── 单位归一化                                           │
│  ├── 科学计算                                             │
│  ├── Validation Engine                                    │
│  └── Benchmark 服务                                       │
├─────────────────────────────────────────────────────────┤
│  LLM 适配层                                               │
│  ├── DeepSeek V4 Pro / Flash 路由                         │
│  ├── Trace as State 两轮推理                              │
│  ├── Function Calling                                     │
│  └── 统一接口 llm_chat / chat_with_tools                  │
├─────────────────────────────────────────────────────────┤
│  数据层                                                   │
│  ├── Raw Layer（不可覆盖）                                │
│  ├── Processed Layer（可追溯）                            │
│  ├── Metadata DB（PostgreSQL）                            │
│  ├── 向量库（ChromaDB）                                   │
│  └── 对象存储（MinIO / S3）                               │
├─────────────────────────────────────────────────────────┤
│  输出层                                                   │
│  ├── 数据推送（Webhook / 消息队列 / 流式）                │
│  ├── 更大大脑接入（Jarvis-Core / 外部 LLM）               │
│  ├── Validation Report                                    │
│  └── Evidence Package                                     │
└─────────────────────────────────────────────────────────┘
```

### 2.2 核心组件关系

```text
PortalJarvis ─┐
Public API ───┤
SDK ──────────┤→ ExpResin Core → Raw/Processed → 推送/订阅 → 更大大脑
机器人 API ───┤
其他实验室 ───┘
```

所有入口共用同一套：

- Schema
- Data Dictionary
- API Contract
- Benchmark
- 认证与租户模型

---

## 三、要求一：完整 API 设计

### 3.1 API 分层

| 层级 | 用途 | 认证 | 示例 |
|---|---|---|---|
| Portal API | PortalJarvis 专用 | Session | `/portal/assistant/*` |
| Internal API | 模块间调用 | 内部 Token | `/internal/*` |
| Public API | 外部实验室 / SDK | API Key / OAuth2 | `/v1/*` |
| Admin API | 租户管理 | Admin Key | `/admin/*` |
| Benchmark API | 评测服务 | API Key | `/benchmark/*` |

### 3.2 Public API 核心接口

```text
# 认证与租户
POST /v1/auth/token
GET  /v1/tenant/info
GET  /v1/tenant/quota

# 项目与实验
GET  /v1/projects
POST /v1/projects
GET  /v1/experiments
POST /v1/experiments
GET  /v1/experiments/{id}
DELETE /v1/experiments/{id}

# 数据上传
POST /v1/experiments/{id}/upload
POST /v1/experiments/{id}/upload/batch
GET  /v1/experiments/{id}/files

# 数据查询
GET  /v1/experiments/{id}/data
GET  /v1/experiments/{id}/data/raw
GET  /v1/experiments/{id}/data/processed
GET  /v1/experiments/{id}/images
GET  /v1/experiments/{id}/metrics

# 分析与映射
POST /v1/mapping/suggest
POST /v1/mapping/confirm
POST /v1/analyze/{id}
POST /v1/compare

# 验证
POST /v1/validation/tasks
GET  /v1/validation/{id}/report
GET  /v1/validation/models/{model_id}

# 推送与订阅
POST /v1/subscriptions
GET  /v1/subscriptions
DELETE /v1/subscriptions/{id}
POST /v1/webhooks
GET  /v1/webhooks

# Benchmark
GET  /v1/benchmark/tasks
POST /v1/benchmark/run
GET  /v1/benchmark/results/{run_id}

# 证据包
GET  /v1/experiments/{id}/evidence
POST /v1/experiments/{id}/publish
```

### 3.3 API 设计原则

1. **API-first**：所有功能先有 API，再有 UI。
2. **OpenAPI 3.1**：所有接口用 OpenAPI 描述，自动生成文档与 SDK。
3. **版本化**：`/v1/`、`/v2/`，破坏性变更必须新版本。
4. **幂等性**：上传、确认、发布接口支持 Idempotency-Key。
5. **分页与过滤**：列表接口支持 cursor 分页、字段过滤。
6. **错误规范**：统一错误码、错误信息、request_id。
7. **限流**：按租户、按接口限流。
8. **审计**：所有写操作记录审计日志。
9. **数据契约**：Experiment、Measurement、Prediction、ValidationTask 用 JSON Schema 定义。
10. **可测试**：每个接口有 pytest + OpenAPI 校验。

### 3.4 SDK

一期提供：

- Python SDK（`expresin`）
- CLI（`expresin-cli`）
- JavaScript SDK（可选）

SDK 必须支持：

```python
from expresin import ExpResinClient

client = ExpResinClient(api_key="...", base_url="...")

# 上传实验
exp = client.experiments.create(project="Ca/Na", type="batch")
client.experiments.upload(exp.id, file="data.xlsx")

# 查询数据
data = client.experiments.get_data(exp.id)

# 订阅推送
client.subscriptions.create(
    event="experiment.processed",
    webhook_url="https://brain.example.com/hook"
)
```

---

## 四、要求二：数据推送至更大大脑

### 4.1 更大大脑的定义

“更大的大脑”可以是：

- Jarvis-Core（本项目中央科学推理系统）
- 外部大模型系统（GPT、Claude、DeepSeek 等）
- 其他实验室自建的分析系统
- 未来的多模态科学推理平台

ExpResin 不绑定某一个大模型，而是提供**统一推送协议**。

### 4.2 推送模式

支持四种模式：

| 模式 | 说明 | 适用场景 |
|---|---|---|
| Webhook | 数据就绪时 POST 到指定 URL | 实时分析 |
| 消息队列 | 推送到 Kafka / Redis Streams / RabbitMQ | 高吞吐、解耦 |
| 流式 API | 更大大脑通过 SSE / WebSocket 订阅 | 实时流 |
| 拉取 API | 更大大脑主动调用 `/v1/experiments/{id}/evidence` | 批处理、按需 |

### 4.3 推送事件

```text
experiment.created
experiment.uploaded
experiment.mapped
experiment.confirmed
experiment.processed
experiment.validated
experiment.published
validation.completed
benchmark.completed
```

### 4.4 Evidence Package

推送的不是原始文件，而是**结构化证据包**：

```json
{
  "experiment_id": "RES-20260916-001",
  "tenant_id": "lab_001",
  "schema_version": "1.2",
  "raw_files": [
    {"uri": "s3://...", "hash": "sha256:..."}
  ],
  "standardized_data": {
    "uri": "s3://.../standardized.csv",
    "schema": "canonical_v1"
  },
  "derived_metrics": {
    "q": 12.3,
    "removal": 0.85,
    "mean": 12.1,
    "sd": 0.4
  },
  "figures": ["s3://.../equilibrium.png"],
  "qc": {...},
  "provenance": {...},
  "confidence": {...},
  "validation": {
    "prediction_id": "...",
    "mae": 0.12,
    "rmse": 0.18
  },
  "signature": "..."
}
```

### 4.5 回传通道

更大大脑分析完成后，可以回传：

```text
POST /v1/experiments/{id}/analysis_result
{
  "analysis_id": "...",
  "source": "jarvis_core",
  "hypothesis": "...",
  "next_experiment": "...",
  "confidence": 0.87
}
```

ExpResin 把回传结果存入 `AnalysisResult` 对象，供后续查询和审计。

### 4.6 推送安全

- 签名：HMAC-SHA256
- 重试：指数退避，最多 5 次
- 幂等：event_id 去重
- 审计：所有推送记录 `PushLog`
- 隔离：租户只能推送到自己的目标

---

## 五、要求三：多实验室 / 多租户

### 5.1 租户模型

```text
Tenant（实验室）
  ├── Project（研究项目）
  │     ├── Experiment（实验）
  │     │     ├── Sample
  │     │     ├── Measurement
  │     │     └── Asset
  │     └── Member（成员）
  ├── APIKey
  ├── Quota
  └── Subscription
```

### 5.2 隔离级别

| 级别 | 说明 |
|---|---|
| 数据隔离 | 每个租户的 Raw / Processed 物理或逻辑隔离 |
| 权限隔离 | 租户成员只能访问本租户数据 |
| API 隔离 | API Key 绑定租户 |
| 配额隔离 | 按租户限流、限存储、限 Token |
| 审计隔离 | 审计日志按租户分开 |
| Benchmark 隔离 | 租户可选择是否贡献数据到公共 Benchmark |

### 5.3 外部实验室接入流程

```text
Step 1  申请租户账号
Step 2  获取 API Key
Step 3  阅读 OpenAPI 文档
Step 4  安装 SDK
Step 5  调用 /v1/experiments 创建实验
Step 6  上传数据
Step 7  配置 Webhook 或订阅
Step 8  接收 Evidence Package
Step 9  可选：贡献数据到 Benchmark
```

### 5.4 多租户下的 Benchmark

- 公共 Benchmark：由主实验室维护，开放给所有租户评测；
- 私有 Benchmark：租户可上传自己的评测集；
- 联邦 Benchmark：多个实验室在不共享原始数据的前提下联合评测；
- 贡献机制：租户可选择贡献脱敏数据，换取 Benchmark 访问权。

### 5.5 多租户下的安全

- 数据加密：传输 TLS，存储加密；
- 脱敏：贡献到公共 Benchmark 时自动脱敏；
- 审计：所有跨租户操作记录；
- 合规：符合 ALCOA+ 原则；
- 删除：租户可申请删除数据，保留审计记录。

---

## 六、更新后的 16 周路线

| 周次 | 方向二：交互流水线 | 方向一：Benchmark | 平台化：API / 推送 / 多租户 |
|---|---|---|---|
| W1 | 对话 MVP 原型 | 收集真实 Excel | 定义 OpenAPI 契约 v0 |
| W2 | AssistantSession / FormDraft | 标注规范 | 租户模型 + API Key |
| W3 | Jarvis 引导填表 | Benchmark v0 | `/v1/experiments` 实现 |
| W4 | Excel 上传 + 反向解析 | 评测脚本 v1 | 上传 API + 文件存储 |
| W5 | Schema Mapping + Trace as State | 单位任务 | `/v1/mapping/*` |
| W6 | 单位归一化 + 校验 | 元数据任务 | `/v1/analyze/*` |
| W7 | 自动计算 + 规范表格 | 计算任务 | Evidence Package 定义 |
| W8 | 入库 + 溯源 | Benchmark v1 | Webhook 推送 MVP |
| W9 | 逻辑多 Agent 增强 | 幻觉任务 | 订阅 API + 消息队列 |
| W10 | 图片绑定 + 对话上传 | 工具调用任务 | Python SDK + CLI |
| W11 | 权限 + 审计 | Benchmark v2 | 多租户隔离 + 配额 |
| W12 | API + Validation MVP | 多模态任务 | `/v1/validation/*` + 回传通道 |
| W13 | Jarvis-Core 调用 | 三组对比实验 | 外部实验室试点接入 |
| W14 | 图片与多模态检索 | 失败案例分析 | 联邦 Benchmark 设计 |
| W15 | 跨实验比较 | Benchmark v3 | 多租户 Benchmark |
| W16 | 真实用户测试 + 完整 Demo | Benchmark 论文初稿 | 平台化文档 + SDK 发布 |

### 关键里程碑

| 里程碑 | 周次 | 验收 |
|---|---|---|
| M1 | W2 | OpenAPI 契约 v0 + 租户模型 |
| M2 | W4 | 对话 + 上传 + Public API 可用 |
| M3 | W8 | Evidence Package + Webhook MVP |
| M4 | W12 | Validation API + 回传通道 |
| M5 | W16 | 多租户平台 + SDK + 至少 1 篇论文初稿 |

---

## 七、更新后的可产出论文

| 优先级 | 论文方向 | 来源 | 目标会议 |
|---|---|---|---|
| P0 | ExpResin-Bench：领域专用 LLM 评测基准 | 方向一 | ACL / EMNLP / NeurIPS D&B |
| P0 | 对话式科学数据入口与规范化流水线 | 方向二 | CHI / CSCW / ACL |
| P0 | API-first 科学数据平台与多租户架构 | 平台化 | SIGMOD / VLDB / eScience |
| P1 | 异构科学表格理解与 Schema Mapping | 方向一 | ACL / EMNLP / SIGMOD |
| P1 | 大模型幻觉治理与置信度校准 | 方向一 | ACL / EMNLP / NAACL |
| P1 | Agent 工具调用可靠性 | 方向一 | NAACL / ACL / AAMAS |
| P1 | 更大大脑与实验数据平台的推送协议 | 平台化 | KDD / ICDE / eScience |
| P2 | 多模态科学实验表征与检索 | 方向二 | SIGIR / CVPR / KDD |
| P2 | 仿真—实验验证与不确定性量化 | 整合 | NeurIPS ML4Science / AAAI |
| P2 | 科学数据溯源与可复现 | 方向二 | SIGMOD / VLDB / eScience |
| P2 | 联邦 Benchmark 与隐私保护评测 | 平台化 | NeurIPS D&B / KDD |

---

## 八、风险与应对

| 风险 | 等级 | 应对 |
|---|---|---|
| API 设计过早固化 | 高 | 用 OpenAPI 契约先行，版本化，破坏性变更走 v2 |
| 多租户隔离漏洞 | 高 | 物理/逻辑隔离 + 审计 + 渗透测试 |
| 推送可靠性差 | 中 | 幂等 + 重试 + 死信队列 + PushLog |
| 更大大脑接口不统一 | 中 | 用 Evidence Package 标准化，适配器模式 |
| SDK 维护成本 | 中 | 用 OpenAPI 自动生成 SDK |
| 外部实验室不愿接入 | 中 | 降低接入门槛 + 提供 Demo + 文档 |
| 配额与限流复杂 | 中 | 先简单按租户限流，后细化 |
| 数据脱敏不彻底 | 高 | 贡献到公共 Benchmark 前强制脱敏 + 人工审核 |
| 回传结果污染数据 | 中 | 回传结果单独存 `AnalysisResult`，不混入 Raw/Processed |
| 论文方向分散 | 中 | 优先 P0，其他后置 |

---

## 九、给 AI Agent 的直接指令

每轮开始时，先读：

```text
第一轮基准：ExpResin 项目宪法
ExpResin_PRD_v1.2.md
ExpResin_推进规划_两方向.md
ExpResin_推进规划_v2.0_平台化.md
CHANGELOG.md
RESEARCH_OPPORTUNITIES.md
```

每轮只完成一个任务卡。每轮输出必须包含：

```text
1. 本轮 Phase / 周次
2. 对应方向（Benchmark / 交互流水线 / 平台化 / 两者整合）
3. 对应科学不变量
4. 前置验收检查
5. 任务卡
6. 代码改动
7. 测试命令与结果
8. ChangeLog 更新
9. ResearchOpportunity 更新（若触发）
10. 下一轮建议
```

若涉及 API，必须说明：OpenAPI 契约、版本、认证、租户、幂等、限流、审计。

若涉及推送，必须说明：事件类型、目标、签名、重试、幂等、PushLog。

若涉及多租户，必须说明：隔离级别、配额、审计、脱敏。

若涉及 Benchmark，必须说明：任务类型、数据来源、标注规范、评测指标、版本号。

若涉及交互流水线，必须说明：对话阶段、表单阶段、上传阶段、分析阶段、入库阶段、可追溯性。

不得跳过 Benchmark，不得覆盖 Raw，不得让 LLM 直接算数值，不得无置信度映射，不得让 PortalJarvis 越权做科学推理，不得跨租户泄漏数据。

---

## 十、结论

本轮把 ExpResin 从“一个项目页面”升级为：

> **API-first、多租户、可与任意更大大脑对接的实验数据基础设施。**

三个新要求全部纳入主线：

1. **完整 API**：OpenAPI 契约、SDK、版本化、认证、限流、审计。
2. **数据推送至更大大脑**：Evidence Package、Webhook、消息队列、流式、回传通道。
3. **多实验室调用**：租户隔离、配额、脱敏、联邦 Benchmark、开放接入。

后续每一轮 Agent 开发，都必须围绕第一轮基准、两个方向和本轮平台化要求展开；若偏离，必须写入 ChangeLog。