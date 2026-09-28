# Repo Sleuth

一个面试展示用的代码仓库故障调查 Agent。输入本地仓库与 Bug 描述，它会通过只读工具调查代码、展示 LangGraph 状态图的执行轨迹，并输出带 `[相对路径:行号]` 引用和逐字代码摘录的结构化结论。

项目刻意把“能找到代码”与“能证明结论”分开：模型的引用必须指向本次调查中实际读取或搜索到的行，报告中的代码摘录也必须与该行原文一致；无效报告会触发一次修正，仍不合格则任务失败。**这只校验证据来源和摘录，不保证推理一定正确**，因此报告仍需人工审查。

## 主要能力

- **LangGraph 调查状态图**：`prepare → model ↔ tools → verify ↔ model`；工具调用最多 24 次、模型调用最多 10 次。工具保持只读，不执行仓库代码或 shell 命令。
- **断点恢复**：SQLite checkpointer 持久化图状态；真实调查在服务重启后尝试从已完成节点继续。独立的 SQLite 任务档案仍负责页面历史记录。
- **结构化证据报告**：根因假设、逐条证据与代码摘录、其他可能、置信度、验证步骤、局限分开展示。引用和摘录均由证据账本校验。
- **可运行的无 Key 演示**：十个不同故障模式调用真实只读工具，并完成引用和摘录校验；演示结论是确定性脚本，不伪装成模型生成。
- **离线与真实评测**：十条带预期引用和关键词的样例，记录结构校验、工具调用次数及耗时；可选真实模型评测。
- **读取边界**：拒绝仓库外路径、超大或非 UTF-8 文件，排除常见依赖、构建目录和密钥文件。

## 技术栈

Python 3.10+（推荐 3.12）、FastAPI、LangGraph、OpenAI Python SDK / Responses API、SQLite、React、TypeScript、Vite、pytest、ripgrep (`rg`)。LangGraph 依赖 LangChain Core；模型与工具调用目前仍直接使用 OpenAI SDK，以保留可检查的 Responses API 调用链，而不是额外叠一层 LangChain Agent。

## 本地启动

需要 Python 3.10+、Node.js 20+、npm 和 `rg`。旧的 Python 3.9 虚拟环境不能安装当前 LangGraph；请使用符合版本要求的 Python 新建环境。在仓库根目录分别打开两个终端：

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
cd backend
../.venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

```bash
cd frontend
npm install
npm run dev
```

打开 <http://127.0.0.1:5173>。默认是无需 API Key 的演示模式。

要调查自己的仓库，在后端进程环境中设置 `OPENAI_API_KEY`，取消页面上的演示模式，并输入本地仓库绝对路径。可选用 `OPENAI_MODEL` 指定有权使用的模型；默认 `gpt-5`。API Key 只在后端环境变量中使用，不填进网页或仓库。真实模式会产生模型调用费用。

任务档案默认在 `backend/data/runs.sqlite`，图检查点默认在 `backend/data/checkpoints.sqlite`（均已加入 `.gitignore`）。分别可用 `REPO_SLEUTH_DB` 和 `REPO_SLEUTH_CHECKPOINT_DB` 指定其他路径。升级已有任务数据库时会自动增加结构化报告字段；旧报告仍可查看。

## 测试与评测

```bash
cd backend
../.venv/bin/pytest -q
../.venv/bin/python -m evals.run
../.venv/bin/python -m evals.run --live  # 可选：需要 API Key，会产生费用
cd ../frontend
npm run build
```

离线评测验证的是十个演示案例的工具链路与规则，不等于模型在真实项目上的泛化能力。`--live` 会针对同一案例集调用模型并产生费用；真实评测仍需更多独立仓库、人工标注和复核，尤其不能仅以关键词命中当作根因正确。

## 面试讲解顺序

1. 运行不同演示场景，展示同一套只读工具如何调查不同故障模式。
2. 点开工具返回与校验事件，说明 `EvidenceLedger` 如何阻止“凭空编造的行号或代码摘录”。
3. 打开结构化报告，区分来源可验证与推理仍需人工判断。
4. 解释 LangGraph checkpoint 与产品任务档案各自保存什么，并用恢复测试演示中断续跑。
5. 运行 `python -m evals.run`，解释离线指标的作用与局限。
6. 如果已配置 API Key，切换真实模式调查一个小仓库；讨论真实模型的成本、质量和安全边界。

## 架构

```text
frontend/src/             调查表单、行动轨迹、历史任务、证据报告
backend/app/main.py        HTTP API 与后台任务调度
backend/app/agent.py       LangGraph 状态图、Responses API 节点与断点恢复
backend/app/repository.py  受限的仓库读取工具
backend/app/evidence.py    引用与代码摘录证据账本
backend/app/report.py      结构化报告与校验
backend/app/store.py       SQLite 产品任务/事件持久化
backend/app/demo.py        十个确定性演示场景
backend/evals/             标注样例与评测入口
demo-repo/                 十个可复现的样例 Bug
```

当前仍是本地单用户项目：没有登录鉴权、多人隔离、任务取消或执行测试的沙箱。不要把 API 暴露到公网，也不要让不可信用户提交任意本地路径。真实调查恢复需要后端仍有 API Key，且之前的 Responses API 会话可用；恢复失败会在任务轨迹中记录原因。演示模式是确定性任务，重启后从头重跑只读步骤。下阶段可增加隔离工作树、测试运行与人工批准的修复补丁，以及跨仓库人工标注评测集。

OpenAI 接口设计参考：[Function calling 官方文档](https://developers.openai.com/api/docs/guides/function-calling)。
