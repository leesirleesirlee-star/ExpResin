# 后端三个实验模板 · 列映射准确度测试

- 测试入口：`POST /portal/assistant/sessions/{sid}/upload`（后端 L1 切块 + LLM 映射）
- 输入：`materials/record-templates/*_example_filled.xlsx`
- gold：`expresin-pipeline/config/record_templates/*_record_v1.json` 的 `data_columns`
- 后端：`http://127.0.0.1:8000`（健康：`/api/health`）

## 总览

| 模板 | 示例文件 | 预期块/列 | 识别块/列 | 正确 | 误映射 | 漏识别 | 噪声列 | 列映射准确率 |
|---|---|---|---|---|---|---|---|---|
| batch | Batch_Record_Template_v1_example_filled.xlsx | 2/6 | 2/6 | 6 | 0 | 0 | 0 | **100.0%** |
| column | Column_Record_Template_v1_example_filled.xlsx | 1/3 | 1/3 | 3 | 0 | 0 | 0 | **100.0%** |
| electrochemical | Electrochemical_Record_Template_v1_example_filled.xlsx | 1/5 | 1/5 | 5 | 0 | 0 | 0 | **100.0%** |
| **合计** | — | — | — | **14** | 0 | 0 | — | **100.0%**（14/14） |

## Batch（批次吸附）

- 文件：`Batch_Record_Template_v1_example_filled.xlsx` · 会话：`ses_7b6270fb573b` · 命中缓存：`False`
- 识别数据块：2（预期 2）
  - 块 `Record#R21-21/B1` kind=`sample_measurement` analyte=`SO4` 列数=3
  - 块 `Record#R34-34/B1` kind=`sample_measurement` analyte=`Cl` 列数=3

| 块 | 列 | 原始表头 raw | 识别 target | 置信度 | gold target | 判定 |
|---|---|---|---|---|---|---|
| Record#R21-21/B1 | A | `Time (min)` | `contact_time` | 0.92 | `contact_time` | ✅ |
| Record#R21-21/B1 | B | `Concentration (mg/L)` | `concentration_mg_l` | 0.98 | `concentration_mg_l` | ✅ |
| Record#R21-21/B1 | C | `pH` | `ph` | 0.99 | `ph` | ✅ |
| Record#R34-34/B1 | A | `Time (min)` | `contact_time` | 0.95 | `contact_time` | ✅ |
| Record#R34-34/B1 | B | `Concentration (mg/L)` | `concentration_mg_l` | 0.97 | `concentration_mg_l` | ✅ |
| Record#R34-34/B1 | C | `pH` | `ph` | 0.97 | `ph` | ✅ |

## Column（柱穿透）

- 文件：`Column_Record_Template_v1_example_filled.xlsx` · 会话：`ses_f31bd1637b04` · 命中缓存：`False`
- 识别数据块：1（预期 1）
  - 块 `Record#R22-22/B1` kind=`sample_measurement` analyte=`SO4` 列数=3

| 块 | 列 | 原始表头 raw | 识别 target | 置信度 | gold target | 判定 |
|---|---|---|---|---|---|---|
| Record#R22-22/B1 | A | `Time (min)` | `contact_time` | 0.94 | `contact_time` | ✅ |
| Record#R22-22/B1 | B | `Effluent Concentration (mg/L)` | `concentration_mg_l` | 0.97 | `concentration_mg_l` | ✅ |
| Record#R22-22/B1 | C | `Effluent pH` | `ph` | 0.98 | `ph` | ✅ |

## Electrochemical（电化学）

- 文件：`Electrochemical_Record_Template_v1_example_filled.xlsx` · 会话：`ses_40228d67855a` · 命中缓存：`False`
- 识别数据块：1（预期 1）
  - 块 `Record#R23-23/B1` kind=`sample_measurement` analyte=`Cl` 列数=5

| 块 | 列 | 原始表头 raw | 识别 target | 置信度 | gold target | 判定 |
|---|---|---|---|---|---|---|
| Record#R23-23/B1 | A | `Time (s)` | `contact_time` | 0.96 | `contact_time` | ✅ |
| Record#R23-23/B1 | B | `Potential (V)` | `potential_v` | 0.99 | `potential_v` | ✅ |
| Record#R23-23/B1 | C | `Current (A)` | `current_a` | 0.99 | `current_a` | ✅ |
| Record#R23-23/B1 | D | `Concentration (mg/L)` | `concentration_mg_l` | 0.98 | `concentration_mg_l` | ✅ |
| Record#R23-23/B1 | E | `pH` | `ph` | 0.99 | `ph` | ✅ |

## 结论

三个模板在示例填写文件上的列级映射全部命中所声明字段，总体准确率 **100.0%**（14/14）。