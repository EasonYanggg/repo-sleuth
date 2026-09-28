# Repo Sleuth

一个面试展示用的代码仓库故障调查 Agent。输入本地仓库路径和 bug 描述后，Agent 使用 `list_files`、`search_code`、`read_file` 三个只读工具调查代码，并在页面上展示每次调用、证据和最终结论。

## 技术栈

- Python 3.9+、FastAPI、OpenAI Python SDK / Responses API
- React、TypeScript、Vite
- pytest；仓库搜索使用 ripgrep (`rg`)

首版任务记录存于服务进程内存。重启后记录会消失。Agent 只读仓库，不执行测试或修改代码。演示模式无需 API Key，使用内置样例和固定调查结果；真实模式会调用模型。

## 启动

需要 Python 3.9+、Node.js 20+、npm 和 `rg`。在两个终端中运行：

```bash
# 终端 1：仓库根目录
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
cd backend
../.venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

```bash
# 终端 2：仓库根目录
cd frontend
npm install
npm run dev
```

打开 <http://127.0.0.1:5173>。直接点击“开始调查”即可体验内置演示。

运行真实调查前，在启动后端的终端设置 `OPENAI_API_KEY`，再取消页面中的“演示模式”。可选用 `OPENAI_MODEL` 指定有权使用的模型；默认是 `gpt-5`。API Key 仅留在后端环境变量中，不填入网页或仓库。

## 测试

```bash
cd backend
../.venv/bin/pytest -q
cd ../frontend
npm run build
```

## 面试演示路径

1. 演示模式中运行内置 `divide(5, 2)` bug，讲解时间线和证据。
2. 切换真实模式，指定自己的小型代码仓库，输入一个新问题。
3. 展示工具边界：模型只能列文件、搜索文本、读取单个 UTF-8 文件；路径跳出仓库会被拒绝。每轮结果带回模型，最多 8 轮。
4. 解释下一阶段的设计：隔离工作树中生成补丁、测试验证、人工审批、持久化任务、评测集。

## 目录

```text
backend/app/agent.py       模型工具调用循环
backend/app/repository.py  受限仓库读取工具
backend/app/main.py        API 与任务事件流
backend/tests/             工具边界与调用循环测试
frontend/src/              调查表单和行动时间线
demo-repo/                 可复现的样例 bug
```

官方接口参考：[OpenAI Function calling](https://developers.openai.com/api/docs/guides/function-calling)。
