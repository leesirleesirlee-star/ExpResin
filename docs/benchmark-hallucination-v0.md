# Benchmark 幻觉任务 v0（模板映射幻觉探针）

- 任务卡：W9 Benchmark 方向「幻觉任务」（roadmap v2.0 §六）
- 基线：`materials/record-templates/*_example_filled.xlsx`；gold：同模板 record_templates 声明
- 模型链路：L1 parse_workbook → L3/L4 map_block（单轮，flash tier 默认）
- 总 token 消耗：50625

## 变体设计

| 变体 | 扰动 | 期望行为 | 幻觉判据 |
|---|---|---|---|
| V0 baseline | 无 | gold 全中 | 基线准确率 |
| V1 nonsense | 表头→无语义符号 | 全部不映射 | 映射即幻觉；conf≥0.8 为高置信幻觉 |
| V2 swapped | 表头循环移位、数据不动 | 跟随表头语义 | 语义服从率 vs 位置惯性 |
| V3a headerless | 清空表头行 | L1 整块拦截、不进入 LLM | region 是否消失 |
| V3b ghostnum | 表头→纯数字（幽灵列） | 拒绝映射 | 幽灵列被映射数 |

## 总览

| 模板 | V0 基线 | V1 幻觉率 | V1 高置信幻觉 | V2 语义服从率 | V3a L1 拦截 | V3b 幽灵防护 |
|---|---|---|---|---|---|---|
| batch | 100%（6/6） | 100%（6/6） | 3 | 100% | ✅ 整块拦截 | ✅ L1 拦截（未进 LLM） |
| column | 100%（3/3） | 100%（3/3） | 1 | 100% | ✅ 整块拦截 | ✅ L1 拦截（未进 LLM） |
| electrochemical | 100%（5/5） | 100%（5/5） | 1 | 100% | ✅ 整块拦截 | ✅ L1 拦截（未进 LLM） |

## 明细

### batch

**V1 高置信幻觉（conf≥0.8）**：

- 列C → `ph` conf=0.96 evidence：数值范围6.85-7.21，典型pH值
- 列A → `contact_time` conf=0.80 evidence：数值范围0~240，样本0,5,15,30，呈时间序列特征
- 列C → `ph` conf=0.97 evidence：数值范围6.85~7.2，接近中性且变化幅度小，典型pH值

**V2 逐列判定**：

| 列 | 新表头 | 语义期望 | 实际映射 | conf | 判定 |
|---|---|---|---|---|---|
| A | `Concentration (mg/L)` | `concentration_mg_l` | `concentration_mg_l` | 0.97 | semantic-obey |
| B | `pH` | `ph` | `ph` | 0.40 | semantic-obey |
| C | `Time (min)` | `contact_time` | `contact_time` | 0.90 | semantic-obey |
| A | `Concentration (mg/L)` | `concentration_mg_l` | `concentration_mg_l` | 0.97 | semantic-obey |
| B | `pH` | `ph` | `ph` | 0.30 | semantic-obey |
| C | `Time (min)` | `contact_time` | `contact_time` | 0.92 | semantic-obey |

**V3a**：L1 拦截=是。
**V3b**：数字表头行被 L1 拒绝（无 region 产出，未消耗 LLM 调用），防护发生在结构层。

### column

**V1 高置信幻觉（conf≥0.8）**：

- 列C → `ph` conf=0.97 evidence：数值范围 6.78-7.1，接近中性，典型 pH 范围，且随时间递减，符合 pH 变化规律。

**V2 逐列判定**：

| 列 | 新表头 | 语义期望 | 实际映射 | conf | 判定 |
|---|---|---|---|---|---|
| A | `Effluent Concentration (mg/L)` | `concentration_mg_l` | `concentration_mg_l` | 0.97 | semantic-obey |
| B | `Effluent pH` | `ph` | `ph` | 0.98 | semantic-obey |
| C | `Time (min)` | `contact_time` | `contact_time` | 0.90 | semantic-obey |

**V3a**：L1 拦截=是。
**V3b**：数字表头行被 L1 拒绝（无 region 产出，未消耗 LLM 调用），防护发生在结构层。

### electrochemical

**V1 高置信幻觉（conf≥0.8）**：

- 列E → `ph` conf=0.90 evidence：数值范围 6.5-9.3，典型 pH 范围，且样本递增符合 pH 变化

**V2 逐列判定**：

| 列 | 新表头 | 语义期望 | 实际映射 | conf | 判定 |
|---|---|---|---|---|---|
| A | `Potential (V)` | `potential_v` | `potential_v` | 0.97 | semantic-obey |
| B | `Current (A)` | `current_a` | `current_a` | 0.97 | semantic-obey |
| C | `Concentration (mg/L)` | `concentration_mg_l` | `concentration_mg_l` | 0.97 | semantic-obey |
| D | `pH` | `ph` | `ph` | 0.95 | semantic-obey |
| E | `Time (s)` | `contact_time` | `contact_time` | 0.80 | semantic-obey |

**V3a**：L1 拦截=是。
**V3b**：数字表头行被 L1 拒绝（无 region 产出，未消耗 LLM 调用），防护发生在结构层。
