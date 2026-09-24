# ExpResin_PRD_v1.2.md

 本 PRD 继承 第一轮基准：ExpResin 项目宪法。  
 若本 PRD 与第一轮基准冲突，以第一轮基准为准。  
 后续每一轮 Agent 开发、评审、实验、论文写作，都必须先复述本轮基准中的“科学不变量”和“16 周末验收”，再执行任务。  
 本 PRD 的目标：指导 AI Agent 在单位算力高质量、逐步添加功能的条件下，完成 ExpResin 初期开发，并系统性地产出计算机交叉方向论文。

---

## 0. 文档元信息

 项  内容 
------
 项目  ExpResin 
 定位  Experimental Evidence & Validation Layer 
 版本  PRD v1.2 
 状态  AI Agent 开发指导文件 
 上位文件  第一轮基准：ExpResin 项目宪法 
 核心原则  Raw 不可覆盖；Processed 可追溯；LLM 做语义，Python 做计算；人工确认不是重训；Benchmark 贯穿；API-first；最小闭环优先；科研产出贯穿 
 一期目标  16 周完成 Agent-ready 最小科学记忆闭环 + 至少 1 个可投稿论文方向 
 开发策略  API-first、单位算力高质量、缓存优先、重组件后置、单实验类型先行、受控多 Agent 
 LLM 后端  DeepSeek V4（ProFlash 路由） 
 推理增强  Trace as State 两轮推理 
 科研产出  工程阻碍 → 论文方向自动总结机制 

---

## 0.1 ChangeLog

```text
变更ID：CHG-20260912-002
变更类型：补充
变更内容：
1. 新增科研论文产出机制：工程阻碍自动总结、论文方向推荐、相关内容生成。
2. 新增 Trace as State 两轮推理方法，应用于 Agent 调用，提高上下文推理精确匹配率。
3. LLM 后端从 Qwen 切换为 DeepSeek V4（ProFlash 路由）。
4. 新增 ResearchOpportunity 数据对象和 research API。
5. 新增 TraceState 数据对象和两轮推理工作流。
6. 更新 16 周计划、验收标准、Agent 工作协议。
影响范围：
- PRD 第4、5、6、7、9、10、11、12、13、15节。
科学理由：
(1) 工程阻碍是论文切入点的重要来源，需系统性捕获和总结。
(2) Trace as State 在 DeepSeek V4 Pro 上将精确匹配从 29.2% 提升至 81.8%，适合 ExpResin 长上下文实验数据推理场景。
(3) DeepSeek V4 支持 OpenAI 风格 Function Calling，1M 上下文窗口，缓存命中成本极低，适合 Agent 循环。
替代方案：
若 Trace as State 在本项目场景无质量增益，回退单轮推理 + Few-shot。
验收：
工程阻碍总结覆盖率 100%；论文方向推荐可操作性；Trace as State 精确匹配率提升可量化；DeepSeek V4 调用成功。
```

---

## 1. 项目宪法：AI 必须遵守的科学不变量

AI Agent 在每一轮任务中必须检查以下条款：

1. Raw 不可覆盖：原始 Excel、CSV、仪器文件、图片永不修改。
2. Processed 可追溯：每个派生值必须能追溯到 Raw、公式、标定、方法和版本。
3. LLM 做语义，Python 做计算：q、removal、mean、SD、MAE、RMSE、单位换算不得让 LLM 直接算。
4. 人工确认不是重训模型：前 8 周只用 Few-shot 示例库；超过 200 条且 Prompt 见顶后再评估云端微调。
5. 基准先行：第 1 周建立 Laboratory Spreadsheet Benchmark，后续所有算法在同一基准评测。
6. API-first  Tool-first：Jarvis-Core 不读文件夹，只通过稳定 APITool 访问 ExpResin。
7. 单位与变量对齐：仿真—实验对比前必须做单位归一化和变量对齐。
8. 低置信度必须暴露：映射置信度低于阈值时前端高亮，不允许 LLM 猜测。
9. 最小闭环优先：先跑通“上传→映射→计算→查询→验证”，再扩展多模态、具身、微调。
10. 每次迭代更新 ChangeLog：Prompt、Schema、API、数据字典、Benchmark 均版本化。
11. 科研产出贯穿：每遇到科学界无完善方法的阻碍，必须捕获、总结、推荐论文方向。

---

## 2. 项目目标与非目标

### 2.1 一期目标
用 16 周完成：

 真实 Excel图片上传 → PortalJarvis 对话补全 → 解析与 Schema Mapping → 人工确认 → RawProcessed 分层存储 → 自动计算与作图 → APITool 调用 → 与 VirtualResin 最小验证 → Jarvis-Core 可读 → 至少 1 个可投稿论文方向。

### 2.2 非目标
一期不做：

- 本地大模型微调 LoRAQLoRA；
- 全自动无人审核的 Schema Mapping；
- 全自动具身实验；
- 大规模多模态视觉理解；
- 完整 MCP 协议集成；
- Kubernetes  复杂微服务；
- 物理拆分多个独立大模型部署。

这些作为二期或后续扩展。

---

## 3. 用户与核心场景

### 3.1 研究生  实验人员
通过网页上传 ExcelCSV、实验图片、仪器结果和备注；通过 PortalJarvis 对话补全实验记录；确认系统自动识别的列、单位和样品映射；获得 ExperimentID。

### 3.2 教师  PI
通过 Jarvis-Core 查询实验数据、比较实验、调取图片、验证 VirtualResin 预测。

### 3.3 Jarvis-Core  中央 Agent
通过 ExpResin APITool：搜索实验、获取数据、获取图片、分析实验、比较实验、读取 validation report、发布 evidence。

### 3.4 PortalJarvis  实验记录助手
在 ExpResin 网页内：与研究人员对话、抽取实验字段、填写 FormDraft、提醒缺失项、初检单位与范围、引导人工确认、确认后写入数据库。

### 3.5 VirtualResin
输出结构化 PredictionObject，由 ExpResin 映射到实验变量空间并完成 simulation-experiment comparison。

### 3.6 Research Opportunity Agent  科研产出 Agent
监控工程阻碍、科学界未解问题、LLM 犯错模式、Benchmark 瓶颈，自动总结为论文方向。

---

## 4. LLM 后端与推理增强

### 4.1 DeepSeek V4 模型路由

 模型  用途  参数  上下文  定价（输入输出，每百万 token） 
---------------
 DeepSeek-V4-Pro  复杂推理、Schema Mapping、Validation 分析、论文方向总结  1.6T 总参  49B 激活  1M  12元（未命中）1元（命中）；输出24元 
 DeepSeek-V4-Flash  简单抽取、对话追问、格式化输出、缺失项检测  284B 总参  13B 激活  1M  1元（未命中）0.2元（命中）；输出2元 

路由原则：
- 简单字段抽取、追问生成、模板填充 → V4-Flash；
- Schema Mapping 决策、单位歧义消解、Validation 报告生成、论文方向总结 → V4-Pro；
- 缓存命中优先，自动前缀缓存可降低输入成本 120 倍；
- Function Calling 使用 OpenAI 兼容的 `tools` 数组和 `tool_calls` 响应。

### 4.2 Trace as State 两轮推理

#### 4.2.1 原理
Causal Transformer 按顺序处理 Token，前面的表示在形成时不知道后面会出现什么任务。长上下文推理中，模型第一次读的时候还不知道自己应该记什么，导致“看过但答错”。

Trace as State 的核心：先让模型推理一遍，产出 Reasoning Trace；第二轮将 Trace 放在上下文之前，让模型带着任务状态重新阅读上下文。

#### 4.2.2 在 ExpResin 中的应用场景

 场景  第一轮 Trace  第二轮 Context  预期收益 
------------
 Excel Schema Mapping  初读 Excel 表头和样本，推断可能的映射关系  Trace + 完整 Excel 表头 + 样本 + 标准 Schema  提高异构表格映射精确匹配率 
 实验异常分析  初读实验数据，识别异常模式  Trace + 完整实验数据 + 标定信息  提高异常归因准确率 
 Validation 报告  初读 Prediction 和 Experiment 数据  Trace + Prediction + Experiment + 单位  提高变量对齐和误差分析精度 
 论文方向总结  初读工程阻碍日志  Trace + 阻碍日志 + 科学文献摘要  提高论文方向相关性 

#### 4.2.3 工作流

```text
第一轮：Context → LLM → Reasoning Trace
第二轮：Trace → Context → Question → LLM → 最终输出
```

实验数据：DeepSeek V4 Pro Preview 在 GraphWalks Parents 任务上，精确匹配从初始 29.2% 提升至 81.8%。

#### 4.2.4 实现约束
- Trace 由第一轮 LLM 生成，必须是结构化文本；
- Trace 长度控制在 500–2000 tokens，超出时压缩；
- 第二轮必须使用同一模型（或同系列模型）；
- Trace 保存到 `TraceState` 对象，用于审计和后续 Few-shot；
- 若质量无提升，回退单轮推理。

---

## 5. 科研论文产出机制

### 5.1 核心原则
 工程阻碍 = 论文切入点。科学界没有完善方法的地方，就是研究机会。

### 5.2 触发条件

Research Opportunity Agent 在以下情况触发：

1. Agent 反复失败或需要人工多次干预；
2. Benchmark 指标低于预期且现有方法无法解决；
3. LLM 出现系统性错误（幻觉、单位混淆、表头误解）；
4. 科学界无现成解决方案；
5. 工程瓶颈可转化为研究问题；
6. 用户明确标注“这里有研究机会”。

### 5.3 输出内容

每次触发后，Research Opportunity Agent 输出：

```text
ResearchOpportunity
- id 唯一标识
- trigger_type 触发类型
- description 阻碍问题描述
- existing_methods 现有方法综述
- gap 现有方法不足
- proposed_direction 建议论文方向
- core_research_question 核心研究问题
- experiment_design 实验设计建议
- related_work 相关工作
- target_venue 目标会议期刊
- priority 优先级
- status 待评估进行中已完成已放弃
```

### 5.4 论文方向优先级

基于第一轮基准和整体可研方案，优先级排序：

 优先级  方向  对应工程阻碍  目标会议 
------------
 P0  A 科学表格理解与数据入口  Schema Mapping 准确率  ACLEMNLPSIGMODKDD 
 P0  C Agent 接口与编排  工具调用可靠性  NAACLACLAAMAS 
 P1  H 大模型幻觉治理  置信度+知识库抑制  ACLEMNLPNAACL 
 P1  B 多模态科学实验表征与检索  RAG 检索策略  SIGIRACLKDDCVPR 
 P2  D 仿真—实验验证与不确定性量化  Validation Engine  NeurIPS ML4ScienceAAAIICLR 
 P2  E 科学数据溯源与可复现  RawProcessed 追溯  SIGMODVLDBeScience 

### 5.5 科研产出节奏

 阶段  周次  科研任务 
---------
 起步  W1–4  建立 Benchmark，记录所有工程阻碍 
 积累  W5–8  总结 Schema Mapping 和单位归一化问题，形成论文方向 A 
 突破  W9–12  总结 Agent 工具调用和 Validation 问题，形成论文方向 C 
 产出  W13–16  三组对比实验数据，完成至少 1 篇论文初稿框架 

### 5.6 三组对比实验设计
- Baseline：传统正则规则匹配；
- LLM-only：纯大模型；
- LLM+RAG：增强大模型。
- 指标：Accuracy、Recall、F1、用户满意度、人工修正次数。

---

## 6. 低算力策略：单位算力高质量

低算力不是“少做功能”，而是：

 在相同算力预算下，通过模型路由、缓存、结构化输出、规则引擎、Few-shot、RAG、验证器、多角色协作、上下文压缩、Trace as State、批处理和置信度校准，提高准确率、完整率和可追溯性。

必须记录以下指标：

- 每 1000 tokens 有效字段数；
- 每次实验人工修正次数；
- 一次填表完成率；
- 单位转换准确率；
- 缺失项召回率；
- 对话轮次；
- 小模型处理简单任务比例；
- 缓存命中率；
- Trace as State 精确匹配提升率。

低算力开发策略：

 模块  单位算力高质量策略 
------
 LLM  DeepSeek V4 路由：简单任务 Flash，复杂任务 Pro；自动前缀缓存 
 本地训练  前 8 周不做任何微调；先积累 Few-shot 示例库 
 向量库  ChromaDB 本地，先小知识库 20–50 文档 
 Embedding  优先 API embedding；本地用 BGE-small 
 数据库  开发期允许 SQLite，SQLAlchemy 抽象，生产迁移 PostgreSQL 
 文件存储  先用本地 `dataraw`、`dataprocessed`，MinIO 后置 
 缓存  先 SQLite 缓存 LLM 响应；Redis 后置 
 前端  先 FastAPI Swagger + 极简 HTML；Vue 3 后置 
 部署  先本地 uvicorn；DockerNginx 后置 
 Agent  逻辑多 Agent，物理单模型优先；Function Calling 起步；Trace as State 两轮推理 
 图片  先存引用和元数据；视觉模型后置 

原则：能缓存就缓存，能批处理就批处理，能 API 就不本地部署，能后置就后置，但每次输出必须可验收、可追溯、可比较。

---

## 7. Multi-Agent 策略

Multi-Agent 允许，但必须受控：

1. 逻辑多 Agent，物理单模型优先：初期用 DeepSeek V4 + 不同 system prompt + 工具，扮演多个角色。
2. 多 Agent 必须证明质量增益：若准确率、完整率、修正次数没有改善，回退单 Agent。
3. 角色边界清晰：每个 Agent 有输入、输出、工具、验收。
4. 禁止为多而多：一期不拆分独立部署的多个大模型。
5. 后期可物理拆分：当算力允许，再将高频、高价值角色拆为独立 Agent 或不同模型。

建议角色：

 角色  职责  模型路由  工具 
------------
 Orchestrator  路由、状态机、决定下一步  Flash  无 
 Extractor  从自然语言抽取实验字段  Flash  LLM + JSON Schema 
 Validator  单位、范围、必填、重复校验  Flash + Python  Python 规则 
 Missing-Info  生成缺失项追问  Flash  LLM + 模板 
 Mapping  列名到标准 Schema 映射  Pro + Trace as State  LLM + Few-shot 
 Audit  字段溯源、ChangeLog  Flash  DB 
 Research Opportunity  工程阻碍总结、论文方向推荐  Pro  LLM + 文献检索 
 Portal Assistant  对话采集、表单填写、确认引导  Flash  上述工具组合 

---

## 8. Portal Jarvis：网页内实验记录助手

### 8.1 命名与边界

- 显示名：Jarvis（ExpResin 实验记录助手）
- 内部代号：`PortalJarvis`
- 中央大脑：`Jarvis-Core`

 项  PortalJarvis  Jarvis-Core 
---------
 位置  ExpResin 网页  中央科学推理系统 
 职责  对话采集、表单填写、缺失提醒、单位初检、确认引导  科学推理、假设生成、跨模块调用、验证决策 
 权限  只能读写当前用户 FormDraft  ExperimentDraft  通过 ExpResin API 读取已确认数据 
 是否做科学推理  否  是 
 是否调用 VirtualResin  否  是 
 是否发布 evidence  否，只有确认后写入数据库  是，通过 publish_evidence 
 共享  Experiment Schema、Data Dictionary、API Contract  同左 

关键原则：PortalJarvis 的对话日志只是草稿和审计材料，不是科学证据。只有人工确认后的字段才进入 ExpResin 数据库。

### 8.2 核心场景

研究人员说：“Jarvis，我今天要做这个实验，准备用 120 mg 树脂和 50 mL 溶液混合，测 Ca 的吸附。”

PortalJarvis 应：
1. 抽取：树脂质量 120 mg、溶液体积 50 mL、目标离子 Ca、实验类型推测 Batch。
2. 填入 FormDraft。
3. 检查第一轮 Excel 模板 `01_Metadata`、`02_Method_Materials`、`04_RawData` 必填项。
4. 追问缺失项。
5. 用户回答后继续补全。
6. 低置信度字段标黄，单位异常标红。
7. 用户确认后写入数据库，生成 ExperimentID。
8. 保存字段来源、对话日志、确认记录。

### 8.3 界面要求

网页三栏：
- 左：对话面板。
- 中：动态表单，按 Excel 模板 Sheet 分组。
- 右：缺失项清单、字段溯源、置信度、单位校验。

移动端可折叠为单列。

必须支持：中文自然语言、上传 Excel 后反向解析并对话确认、“我不知道稍后补”标记、自动生成 ExperimentID 建议、模板版本绑定、确认后写入、所有字段显示来源。

---

## 9. 功能需求

### P0：一期必须完成

#### FR-01 项目与实验元数据
- 创建 Project、Experiment。生成唯一 ExperimentID。

#### FR-02 文件上传
- 支持 ExcelCSV、图片、PDF、仪器文件。Raw 保存后不可覆盖。返回 URI 和 hash。

#### FR-03 Excel 解析
- pandas 读取多 Sheet、提取列名和前 3–5 行样本、处理合并表头、缺失值预览。

#### FR-04 Schema Mapping
- 构造 Prompt：标准 Schema + 用户表头 + 样本数据 + Few-shot。严格 JSON 输出。置信度 0.8 高亮。缓存表头哈希 + 映射结果。使用 Trace as State 两轮推理。

#### FR-05 人工确认
- 前端确认或修改映射。确认结果写入 MappingExample。动态检索最相似 3–5 条作为 Few-shot。

#### FR-06 单位归一化与校验
- 规则引擎兜底 + LLM 校验。支持温度、压力、时间、浓度、质量、体积。

#### FR-07 Raw  Processed 分层
- Raw 不修改。Processed 记录来源 Raw 版本与方法。

#### FR-08 自动计算与作图
- Batch test：q = (C0 - Ce)Vm；Removal%；meanSD；mass balance。数值计算必须 Python 实现。

#### FR-09 图片与资产绑定
- 图片绑定 ExperimentSample。API 可按实验或样品返回图片引用。

#### FR-10 Agent Tools  Function Calling
一期工具不超过 10 个：`list_projects`、`search_experiments`、`get_experiment`、`get_experiment_data`、`get_experiment_images`、`analyze_experiment`、`compare_experiments`、`compare_simulation_experiment`、`create_validation_task`、`get_validation_report`。
- 使用 DeepSeek V4 OpenAI 兼容 Function Calling。
- 工具描述精准；返回值统一 JSON；超时重试 3 次；异常降级。
- 支持 Trace as State 两轮推理。

#### FR-11 API
必须实现：`GET projects`、`POST experimentsupload`、`GET experiments{id}`、`GET experiments{id}data`、`GET experiments{id}images`、`POST mappingsuggest`、`POST mappingconfirm`、`POST analyze{id}`、`POST validationtasks`、`GET validation{id}report`

#### FR-12 Validation Engine MVP
- Prediction Object 和 ValidationTask。计算 MAE、RMSE、relative error、curve RMSE。输出 validation report。使用 Trace as State 两轮推理。

#### FR-13 Benchmark 与评估
- 第 1 周收集 10–20 份真实 Excel，目标 100–200 份。标注标准映射。三组对比：Baseline、LLM-only、LLM+RAG。

#### FR-14 日志与审计
- ChangeLog、Deviation、QC。

#### FR-15 对话式表单初始化
- 加载模板 Schema。识别必填项和依赖项。创建 AssistantSession 和 FormDraft。

#### FR-16 自然语言字段抽取
- 从用户话语抽取字段、值、单位、置信度。输出严格 JSON。不猜测缺失值。

#### FR-17 缺失项追问
- 根据模板必填项和当前草稿，生成最少必要追问。支持“稍后补”。

#### FR-18 单位与范围初检
- 规则引擎兜底，LLM 只解释。异常标红，低置信度标黄。

#### FR-19 字段级溯源
- 每个字段保存来源类型、来源引用、原始文本、模型版本、时间戳、确认人。

#### FR-20 确认写入
- 只有用户确认后才写入 Experiment  Measurement。未确认字段不进入科学证据层。

#### FR-21 对话上传
- 用户可在对话中上传 Excel、图片、仪器文件。系统解析后反向填充草稿。

#### FR-22 PortalJarvis 与 Jarvis-Core 隔离
- PortalJarvis 不调用 VirtualResin、不生成科学假设、不发布 evidence。

#### FR-23 科研论文产出
- 捕获工程阻碍。总结现有方法 gap。推荐论文方向。生成核心研究问题、实验设计、相关工作、目标会议。

#### FR-24 Trace as State 推理
- 实现两轮推理工作流。保存 TraceState。支持 FlashPro 路由。若质量无提升，回退单轮。

#### FR-25 DeepSeek V4 集成
- 统一 LLM 适配层。支持 V4-Pro 和 V4-Flash 路由。自动前缀缓存。OpenAI 兼容 Function Calling。

### P1：后续添加
Redis 缓存、MinIO、Docker + Nginx、Vue 3 完整界面、RAG 知识库、多实验比较增强、权限系统、Embodied AI 日志接口、逻辑多 Agent 增强 PortalJarvis。

### P2：二期扩展
云端微调、本地微调、物理拆分 Multi-Agent、MCP、视觉模型、具身实验、Column  CO2 Capture  Electrochemistry 扩展。

---

## 10. 非功能需求

 类型  要求 
------
 可复现  RawProcessed 分离，公式、Prompt、模型版本记录 
 可追溯  每个 Processed 可追溯到 Raw 
 安全  API Key 环境变量；Token 上限；recursion_limit 
 成本  LLM 响应缓存；DeepSeek V4 自动前缀缓存；模型路由 
 性能  上传接口异步；Excel 解析不阻塞 
 可靠性  外部调用 try-except、超时、降级 
 可测试  每个 P0 功能有 pytest 
 可协作  API 契约先定，前后端 Mock 并行 
 可维护  docstring、README、ChangeLog 

---

## 11. 数据模型

必须实现以下对象：

```text
Project, Experiment, Sample, Measurement, Asset,
MappingExample, Prediction, ValidationTask,
QC, Deviation, ChangeLog, DataDictionary,
AssistantSession, FormDraft, FieldProvenance,
MissingField, ConfirmationLog,
ResearchOpportunity, TraceState
```

核心字段：

- Experiment：id, project_id, title, type, operator, date_start, status, raw_file_uri, method_sop, resin_type, resin_batch, bed_volume, objective, reviewer。
- Measurement：id, experiment_id, sample_id, record_id, analyte, raw_signal, unit, concentration, time, volume, temperature, ph, replicate。
- MappingExample：id, header_hash, raw_headers, mapping_json, confidence, confirmed_by, created_at。
- Prediction：id, model_id, condition_json, target_variable, predicted_value, predicted_curve_uri, uncertainty, created_at。
- ValidationTask：id, prediction_id, experiment_id, status, metrics_json, report_uri。
- AssistantSession：id, user_id, project_id, template_id, status, created_at, updated_at。
- FormDraft：id, session_id, field_path, value, unit, confidence, status, updated_at。
- FieldProvenance：id, draft_id, field_path, source_type, source_ref, raw_text, model_version, timestamp, confirmed_by。
- MissingField：id, session_id, field_path, required, reason, asked_at, answered_at, status。
- ConfirmationLog：id, session_id, field_path, old_value, new_value, confirmed_by, timestamp。
- ResearchOpportunity：id, trigger_type, description, existing_methods, gap, proposed_direction, core_research_question, experiment_design, related_work, target_venue, priority, status, created_at。
- TraceState：id, session_id, pass_number, trace_text, model_used, context_hash, created_at。

---

## 12. API

新增 PortalJarvis API：

```text
POST portalassistantsessions
POST portalassistantsessions{id}messages
GET  portalassistantsessions{id}form-state
GET  portalassistantsessions{id}missing-fields
POST portalassistantsessions{id}upload
POST portalassistantsessions{id}confirm
GET  portalassistanttemplates{template_id}
```

新增科研产出 API：

```text
POST researchopportunities
GET  researchopportunities
GET  researchopportunities{id}
POST researchsummarize
POST researchpaper-direction
```

核心 ExpResin API：

```text
GET  projects
POST experimentsupload
GET  experiments{id}
GET  experiments{id}data
GET  experiments{id}images
POST mappingsuggest
POST mappingconfirm
POST analyze{id}
POST validationtasks
GET  validation{id}report
```

Jarvis-Core 扩展 API：

```text
create_validation_task(model_id, experiment_spec)
get_simulation_prediction(model_id, condition)
compare_simulation_experiment(validation_id)
get_validation_report(model_id)
get_robot_experiment_log(experiment_id)
publish_evidence(experiment_id)
```

---

## 13. Agent 工作协议

每一轮 Agent 必须执行：

1. 复述本轮对应 Phase  周次。
2. 引用第一轮基准中的科学不变量。
3. 检查前置验收是否通过。
4. 只做一个任务卡。
5. 先写测试验收，再实现。
6. 输出改动文件、diff、测试命令、结果。
7. 更新 ChangeLog、BENCHMARK、PROMPTS、API_CONTRACT、RESEARCH_OPPORTUNITIES。
8. 未通过验收，不进入下一阶段。

任务卡模板：

```text
任务ID：W05-MAP-01
科学问题：异构表格列名语义映射
输入：Benchmark Excel、标准Schema、Few-shot示例
输出：JSON映射 + 置信度 + 人工确认界面 + TraceState
验收：Benchmark v0 映射准确率≥80%；低置信度0.8全部高亮；人工修正次数记录；Trace as State 精确匹配提升可量化
禁止：LLM直接计算；覆盖Raw；无置信度输出；猜测null
变更：若修改Schema，写入ChangeLog
科研：若遇阻碍，生成 ResearchOpportunity
```

若涉及 Multi-Agent，必须说明：本任务使用哪些逻辑角色、是否物理单模型、预期质量增益、若质量不升回退方案。

若涉及 PortalJarvis，必须遵守：只做表单采集、追问、校验、确认；不调用 VirtualResin；不生成科学假设；不发布 evidence；对话日志不等于科学证据；人工确认后才写入数据库。

若涉及 Trace as State，必须说明：第一轮 Trace 内容、第二轮 Context、预期精确匹配提升、回退方案。

若涉及科研产出，必须输出：ResearchOpportunity 对象，包含 trigger_type、description、existing_methods、gap、proposed_direction、core_research_question、experiment_design、target_venue、priority。

必须维护文件：

```text
AGENTS.md
PROJECT_CHARTER.md
DATA_DICTIONARY.md
API_CONTRACT.md
BENCHMARK.md
CHANGELOG.md
RESEARCH_OPPORTUNITIES.md
PROMPTS
TESTS
```

---

## 14. 迭代路线

 阶段  周次  目标  单位算力高质量策略 
------------
 M0  W1  Hello Agent + 骨架 + Benchmark v0 + DeepSeek V4 接入  只调 API，不训练；PRD v1.2 + ChangeLog；Trace as State 原型 
 M1  W2–4  数据模型 + 上传 + Excel 解析 + PortalJarvis 对话 MVP  SQLite + 本地文件；单 Agent + 抽取 + 追问 
 M2  W5–8  Schema Mapping + 人工确认 + 单位 + 计算 + 图 + PredictionValidation Schema  Few-shot + 缓存；Excel 上传反向解析 + 对话确认；Trace as State 用于 Mapping 
 M3  W9–12  Function Calling + API + Validation Engine MVP + 逻辑多 Agent + 科研产出  工具≤10；Orchestrator  Extractor  Validator  Missing-Info  Research Opportunity 
 M4  W13–16  Jarvis-Core 对接 + 图片 + 比较 + 真实测试 + 三组实验 + 论文初稿  只做引用，不做视觉模型；只读已确认数据 

### 16 周详细计划

 周次  Phase  新增强化 
---------
 W1  Phase 0  PRD v1.2 + ChangeLog；Benchmark v0；Hello Agent；DeepSeek V4 接入；Trace as State 原型 
 W2  Phase 1  模板 Schema 解析；AssistantSession  FormDraft  TraceState 数据模型 
 W3  Phase 1  PortalJarvis 对话 MVP：单 Agent + 抽取 + 追问 
 W4  Phase 1  Excel 上传反向解析 + 对话确认；Raw 保存；工程阻碍捕获启动 
 W5  Phase 2  Schema Mapping + 人工确认 + Few-shot + Trace as State 两轮推理 
 W6  Phase 2  单位校验 + 缺失项追问 + 字段溯源 
 W7  Phase 2  Batch 计算 + Prediction Object 
 W8  Phase 2  作图 + Validation Schema；论文方向 A 总结 
 W9  Phase 3  逻辑多 Agent：Orchestrator  Extractor  Validator  Missing-Info  Research Opportunity 
 W10  Phase 3  图片绑定 + 对话上传图片 
 W11  Phase 3  权限 + 审计 + Embodied AI 日志接口 
 W12  Phase 3  ExpResin API + Validation Engine MVP；论文方向 C 总结 
 W13  Phase 4  Jarvis-Core 调用已确认数据 
 W14  Phase 4  图片与多模态检索 
 W15  Phase 4  跨实验比较 + 三组对比实验 
 W16  Phase 4  真实用户测试 + 完整闭环 Demo + 至少 1 篇论文初稿框架 

### 学习路线映射
L1 W1–2 编程基础；L2 W3–4 大模型应用；L3 W5–6 后端开发；L4 W7–8 Agent 开发；L5 W9–10 系统整合；L6 W11+ 进阶优化。原则：边做边学、不跳级、每级亲手写代码并达标。

### 人工确认节奏
W1–4：Few-shot 示例库，10–50 条。
W5–8：继续 Prompt 优化，记录 AI 常犯错误为黄金数据。
W9 后：若人工确认 200 条且 Prompt 见顶，再评估云端微调。
本地 LoRAQLoRA 不作为一期必选。

---

## 15. 验收标准

### 每阶段通用
- 代码可运行；测试通过；ChangeLog 更新；Benchmark 指标记录；Raw 未被覆盖；LLM 未直接计算数值。

### PortalJarvis 专项验收
- 必填项缺失提醒 100%；字段来源可追溯 100%；人工确认后才能写入 100%；5 分钟内完成 `01_Metadata` 关键字段；单位错误检测通过测试集；对话轮次 ≤ 10 完成关键元数据；低置信度字段全部高亮；PortalJarvis 不越权做科学推理。

### Trace as State 专项验收
- 两轮推理工作流实现；TraceState 保存完整；精确匹配率提升可量化；若质量无提升，回退单轮有记录。

### DeepSeek V4 专项验收
- V4-Pro 和 V4-Flash 路由可用；自动前缀缓存生效；Function Calling 成功；Token 成本可追踪。

### 科研产出专项验收
- 工程阻碍总结覆盖率 100%；ResearchOpportunity 对象完整；至少 1 个论文方向可操作；三组对比实验数据完整。

### 16 周末最终验收
必须能演示：

 研究生上传真实 CaNa batch test Excel + 图片 → PortalJarvis 对话补全 → 系统映射字段、单位归一化 → 计算 q、removal、mean、SD → 生成图 → Jarvis-Core 通过 API 查询数据和图片 → ExpResin 读取 VirtualResin prediction → 输出 MAERMSEvalidation report → 至少 1 篇论文初稿框架。

---

## 16. 风险与避坑

1. 范围蔓延：禁止一期做本地微调、全具身、全自动无人审核。
2. 数据异质：Benchmark 必须真实。
3. 幻觉：低置信度人工确认 + 生成-验证 + RAG。
4. 单位错误：规则兜底 + LLM 校验 + 回归测试。
5. 成本：API Key 环境变量；Token 上限；DeepSeek V4 自动前缀缓存。
6. 工程一致性：依赖版本锁定。
7. 科研可复现：公式、Prompt、模型版本全部记录。
8. 微调误用：微调是锦上添花，不是雪中送炭。
9. Multi-Agent 过度设计：必须证明质量增益，否则回退单 Agent。
10. PortalJarvis 越权：不得做科学推理，不得发布 evidence。
11. Trace as State 无效：若质量无提升，回退单轮推理。
12. DeepSeek V4 不稳定：保留 Qwen 作为备选后端。
13. 科研产出空泛：ResearchOpportunity 必须可操作、可验证、有目标会议。

---

## 17. 给 AI Agent 的直接指令

你现在是本项目的 AI Agent。每轮开始时，先读：

```text
第一轮基准：ExpResin 项目宪法
ExpResin_PRD_v1.2.md
CHANGELOG.md
RESEARCH_OPPORTUNITIES.md
```

每轮只完成一个任务卡。  
每轮输出必须包含：

```text
1. 本轮 Phase  周次
2. 对应科学不变量
3. 前置验收检查
4. 任务卡
5. 代码改动
6. 测试命令与结果
7. ChangeLog 更新
8. ResearchOpportunity 更新（若触发）
9. 下一轮建议
```

若发现需求冲突，先停止实现，写 ChangeLog 提案，说明科学理由和替代方案。  
不得跳过 Benchmark，不得覆盖 Raw，不得让 LLM 直接算数值，不得无置信度映射。

若涉及 Multi-Agent，必须说明：逻辑角色、是否物理单模型、预期质量增益、回退方案。

若涉及 PortalJarvis，必须遵守：只做表单采集、追问、校验、确认；不调用 VirtualResin；不生成科学假设；不发布 evidence；对话日志不等于科学证据；人工确认后才写入数据库。

若涉及 Trace as State，必须说明：第一轮 Trace 内容、第二轮 Context、预期精确匹配提升、回退方案。

若涉及科研产出，必须输出 ResearchOpportunity 对象。

---

## 18. 结论

本 PRD 是 ExpResin 初期开发的执行文件。  
它把第一轮基准转化为 AI Agent 可执行的任务、验收、协议和单位算力高质量路线，并新增科研论文产出机制、Trace as State 两轮推理、DeepSeek V4 后端。  
后续每一轮思考，都必须围绕第一轮基准展开；若偏离，必须写入 ChangeLog。