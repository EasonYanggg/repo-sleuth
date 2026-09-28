# Repo Sleuth

一个面试展示用的代码仓库故障调查 Agent。输入本地仓库与 Bug 描述，它会通过只读工具调查代码、展示工具调用轨迹，并输出带 `[相对路径:行号]` 引用的结论。

项目刻意把“能找到代码”与“能证明结论”分开：模型的引用必须指向本次调查中实际读取或搜索到的行；无效引用会触发一次修正，仍不合格则任务失败。**这只校验证据来源，不保证推理一定正确**，因此报告仍需人工审查。

## 主要能力

- **受限工具循环**：`list_files`、`search_code`、`read_file`；最多 8 轮、24 次工具调用，不执行仓库代码或 shell 命令。
- **证据账本**：记录工具观察到的代码行，对最终报告的引用进行校验，并在轨迹中显示验证结果。
- **持久化调查档案**：SQLite 保存任务、状态、事件和结论；页面可查看最近任务，服务重启后仍在。
- **可运行的无 Key 演示**：两个预置 Bug 场景调用真实只读工具，并完成引用校验；演示结论是确定性脚本，不伪装成模型生成。
- **离线评测**：两条带预期引用和关键词的样例，检查工具使用、证据校验与结论；可选真实模型评测。
- **读取边界**：拒绝仓库外路径、超大或非 UTF-8 文件，排除常见依赖、构建目录和密钥文件。

## 技术栈

Python 3.9+、FastAPI、OpenAI Python SDK / Responses API、SQLite、React、TypeScript、Vite、pytest、ripgrep (`rg`)。

## 本地启动

需要 Python 3.9+、Node.js 20+、npm 和 `rg`。在仓库根目录分别打开两个终端：

```bash
python3 -m venv .venv
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

任务数据库默认在 `backend/data/runs.sqlite`（已加入 `.gitignore`）。可用 `REPO_SLEUTH_DB` 指定其他路径。

## 测试与评测

```bash
cd backend
../.venv/bin/pytest -q
../.venv/bin/python -m evals.run
../.venv/bin/python -m evals.run --live  # 可选：需要 API Key，会产生费用
cd ../frontend
npm run build
```

离线评测验证的是演示链路与规则，不等于模型在真实项目上的泛化能力。真实评测仍需更多仓库、标注问题和人工复核。

## 面试讲解顺序

1. 运行两个演示场景，展示同一套工具边界如何收集证据。
2. 点开工具返回内容与引用校验事件，说明 `EvidenceLedger` 如何阻止“凭空编造的行号”。
3. 刷新页面或重启后端，打开历史任务，说明 SQLite 持久化设计。
4. 运行 `python -m evals.run`，解释离线指标的作用与局限。
5. 如果已配置 API Key，切换真实模式调查一个小仓库；讨论真实模型的成本、质量和安全边界。

## 架构

```text
frontend/src/             调查表单、行动轨迹、历史任务、证据报告
backend/app/main.py        HTTP API 与后台任务调度
backend/app/agent.py       Responses API 工具循环与结论修正
backend/app/repository.py  受限的仓库读取工具
backend/app/evidence.py    引用证据账本
backend/app/store.py       SQLite 任务/事件持久化
backend/app/demo.py        确定性演示场景
backend/evals/             标注样例与评测入口
demo-repo/                 两个可复现的样例 Bug
```

当前仍是本地单用户项目：没有登录鉴权、多人隔离、任务取消或执行测试的沙箱。不要把 API 暴露到公网，也不要让不可信用户提交任意本地路径。下阶段可增加隔离工作树、测试运行与人工批准的修复补丁，以及更大规模的标注评测集。

OpenAI 接口设计参考：[Function calling 官方文档](https://developers.openai.com/api/docs/guides/function-calling)。
