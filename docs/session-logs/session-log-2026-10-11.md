# ExpResin 会话日志 · 2026-10-11

> 用途：记录当日工作状态、启动/停止方法与遗留事项，供下次接手时快速恢复上下文。
> 本日主题：**仓库可发布化 —— 停止分发实验数据、脱敏实验标识、重写公开历史，并清理本日缓存与临时物**。

---

## 0. 本日结论（一句话）

公开仓库 `leesirleesirlee-star/ExpResin` 现在只含源码与文档（107 个文件、约 0.83 MB）；
真实实验数据既不在 HEAD、也不在任何历史提交中；全部真实实验标识已替换为示例值。

---

## 1. 做了什么

### 1.1 不再入库的本地数据（磁盘保留；仅 `uploads/` 真删）

| 路径 | 内容 | 处理 |
|---|---|---|
| `uploads/` | 会话上传（截图、粘贴文本） | 磁盘删除 + 索引移除 + 加忽略 |
| `expresin-pipeline/data/raw/` | 每次会话上传的原始工作簿 | 仅索引移除 |
| `expresin-pipeline/data/cache/` | 识别结果缓存 | 仅索引移除 |
| `expresin-pipeline/data/nas_mirror/` | 每实验镜像（manifest / processed / canonical） | 仅索引移除 |
| `expresin-pipeline/data/expresin.db` | 本地 SQLite 档案库 | 仅索引移除 |
| `materials/data/` | 真实实验工作簿 | 仅索引移除 |
| `materials/guides/` | 研究方案与实现指南 docx | 仅索引移除 |
| `expresin-portal/public/data/analysis.json` | 真实识别结果（前端演示/兜底数据） | 仅索引移除 |

保留公开：`expresin-portal/`、`expresin-pipeline/`、`docs/`、`outputs/`、
`materials/record-templates/`（空白记录模板 + `example_filled` 基准样本）、`materials/template-drafts/`。

### 1.2 标识脱敏（真实实验标识 → 示例值）

脚本（一次性工具，完成使命后已按会话末清理要求删除，见 1.4）：
`.deepworks/tmp/sanitize_identifiers.py` —— 用法 `python sanitize_identifiers.py <root> [--apply]`；
逐文件探测编码（utf-8 / gbk）并原样写回，幂等，历史重写时复用。
如需再次执行同类脱敏，按下方替换表重建一份即可；⚠️ 重建的脚本内含真实原值，**不得入库或外发**。

| 类别 | 替换为 | 出现处 |
|---|---|---|
| 真实工作簿文件名（2 个） | `example_ion_exchange.xlsx` / `example_figures.xlsx` | docs、scripts、demo.js、ApiDocsView |
| 真实项目名 | `示例离子交换` | demo.js、research-opportunities |
| 真实实验 ID | `EXP-01` | demo.js |
| 真实 sheet 代号（7 个） | `sheet-01` … `sheet-07` | demo.js、export_web.py、docs |
| 真实 `project_id` | `"DEMO"` | server/app.py、server/store.py、session.js、ApiDocsView |

> 原值不在本文档中复现（避免二次泄露）；脱敏脚本已验证并删除，不再留存替换表。

未替换（领域词汇，非真实实验标识）：树脂型号 A600 / A520 / C104 / WAC / SBA / SAC 等 ——
它们是 `standard_schema.json` 与 `experiment_template_v1.json` 的枚举别名。

验证：用真实工作簿名、项目代号与旧 sheet 代号做全文检索均无命中；`npm run build` 通过；
6 个 `.py` 通过 `py_compile`；3 个 `.json` 可解析。

### 1.3 公开历史重写（已强推）

- 手段：`git filter-branch` 两遍 —— `--tree-filter`（脱敏，含根目录历史遗留文件）+ `--index-filter`
  （删除数据路径），均带 `--prune-empty`。
  - 第一遍只处理了 `materials/data` 等目录，**漏了初始提交放在仓库根目录的原始工作簿**，
    第二遍用 `:(top,glob)*.xlsx|*.docx|*.db|*.csv|*.png|*.txt` 补掉。教训：重写后必须
    `git rev-list --all --objects` 全量核对，而不是只看 `git grep`。
- 结果：23 → **19** 个提交；`.git` 3.69 MB → 0.41 MB；公开历史可达对象 331 个。
- 重写前备份：`C:\Users\Lenovo\AppData\Local\Temp\opencode\ExpResin-git-backup-20261011\.git`
  （HEAD `c26a241`，含重写前的完整历史；**仅本机，勿入库**）。
- 强推后远端 `main` = `13a6cd5`。
- 端到端验证：全新 clone 公开仓库 → 19 提交 / 107 文件 / 0.39 MB，
  `git rev-list --all --objects` 中不含 `nas_mirror`、`expresin.db`、`uploads/`、
  `analysis.json`、`materials/data|guides`、以及真实工作簿名与项目代号。

### 1.4 本日缓存与临时物清理（会话末）

| 类别 | 内容 | 结果 |
|---|---|---|
| 识别缓存 | `expresin-pipeline/data/cache/*.json` × 6（37 KB，本日生成） | 已删，空目录保留 |
| Python 字节码缓存 | `expresin-pipeline/scripts/__pycache__`（6）+ `server/__pycache__`（3），本日语法检查产生 | 已删 |
| 会话临时物 | `.deepworks/tmp/` 本日文件 45 个（306.73 KB）：CDP 验证脚本、截图、提交信息 txt、脱敏脚本 | 已删 |
| 外部临时副本 | `%LOCALAPPDATA%\Temp\opencode\expr-clean\`（脱敏脚本 + filter `.sh`） | 已删 |
| 历史遗留临时物 | `.deepworks/tmp/` 中 9/19–9/24 的 29 个文件（1033 KB），含真实实验数据与真实标识（L1/mapping 输出、w7 报告、探测脚本等） | 已删 |

保留未动：`expresin-portal/dist/`（本日构建产物，可 `npm run build` 重建）、
`expresin-portal/node_modules/.vite`（9/19）、`expresin-pipeline/src/__pycache__`（10/10）、
以及 1.3 的 Git 历史备份。

删除后复查：`.deepworks/` 全域剩余 154 个文件，用真实工作簿名、项目代号、旧 sheet 代号检索均为 0 命中。
副作用：识别缓存清空后，下次对同一工作簿识别会重新走 L1/L2 + LLM 映射，不再秒回缓存结果。

## 2. 遗留与注意

1. **GitHub 侧延迟 GC**：旧 commit 已从分支历史不可达，但按旧 SHA 直接访问可能在短时间内仍可命中；
   如确需彻底清除，可向 GitHub 支持提交 prune 请求。
2. 任何在强推前 **clone / fork 过的副本** 仍持有旧数据，无法远程回收。
3. **历史哈希已全部变化**：协作者需重新 clone，或 `git fetch --all && git reset --hard origin/main`。
4. 本地真实数据仍在磁盘（见 1.1 表），日常运行不受影响；`uploads/` 已删除，需要时由上传流程自动重建。
5. 后续若重新生成 `analysis.json` 等导出物，**不要** `git add -f`，它们默认被忽略。
6. 服务状态：本日会话末已按要求关闭前后端 —— 前端 Vite 进程已停止、5173 空闲；后端本来就未启动、8000 空闲。
   重启方法见 `session-log-2026-09-24.md` 第 0 节。
7. 本日清理不可逆：`.deepworks/tmp/` 中 9 月的调试/探测脚本与数据 dump 已删除，如需同类排查请重新编写。