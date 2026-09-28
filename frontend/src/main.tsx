import React, { useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import './style.css'

type Event = { time: string; kind: string; title: string; detail: string }
type Run = { id: string; status: string; repository: string; issue: string; demo: boolean; events: Event[]; answer: string | null }
type Health = { status: string; api_key_configured: boolean; demo_repository: string }

function App() {
  const [health, setHealth] = useState<Health | null>(null)
  const [repository, setRepository] = useState('')
  const [issue, setIssue] = useState('divide(5, 2) 返回 2，但预期是 2.5。请定位原因。')
  const [demo, setDemo] = useState(true)
  const [run, setRun] = useState<Run | null>(null)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    fetch('/api/health').then(r => r.json()).then((data: Health) => {
      setHealth(data)
      setRepository(data.demo_repository)
    }).catch(() => setError('无法连接后端，请先启动 API 服务。'))
  }, [])

  useEffect(() => {
    if (!run || run.status !== 'running') return
    const timer = window.setInterval(async () => {
      try {
        const response = await fetch(`/api/runs/${run.id}`)
        if (response.ok) setRun(await response.json())
      } catch { setError('任务状态更新失败，请检查后端服务。') }
    }, 900)
    return () => window.clearInterval(timer)
  }, [run?.id, run?.status])

  async function start() {
    setError('')
    setRun(null)
    setSubmitting(true)
    try {
      const response = await fetch('/api/runs', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ issue, repository, demo }) })
      const data = await response.json()
      if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : '无法创建任务')
      const result = await fetch(`/api/runs/${data.id}`)
      setRun(await result.json())
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : '发生未知错误')
    } finally { setSubmitting(false) }
  }

  return <div className="app">
    <header><div className="brand"><span className="brand-icon">⌁</span><span>REPO SLEUTH</span></div><span className="badge">INTERVIEW PROJECT · MVP</span></header>
    <main>
      <section className="hero"><div className="eyebrow">CODE INVESTIGATION AGENT</div><h1>把 bug 描述，变成有证据的调查结论。</h1><p>Agent 自主检索仓库，逐步记录工具调用，并说明根因与下一步验证方式。</p></section>
      <div className="layout">
        <section className="card form-card"><div className="section-label">01 / 发起调查</div><h2>调查任务</h2>
          <label htmlFor="repo">本地仓库路径</label><input id="repo" value={repository} onChange={e => setRepository(e.target.value)} disabled={demo} placeholder="/absolute/path/to/repo" />
          <label htmlFor="issue">问题描述</label><textarea id="issue" value={issue} onChange={e => setIssue(e.target.value)} rows={6} />
          <label className="toggle"><input type="checkbox" checked={demo} onChange={e => setDemo(e.target.checked)} /><span>演示模式（无需 API Key，使用固定样例）</span></label>
          <button onClick={start} disabled={submitting || !!(run && run.status === 'running') || issue.trim().length < 8}>{submitting ? '正在创建…' : run?.status === 'running' ? '正在调查…' : '开始调查'} <span>↗</span></button>
          <p className="hint">{demo ? '演示模式展示固定的调查过程；关闭后由真实模型选择工具。' : health?.api_key_configured ? '真实模式已就绪：只读仓库，不执行代码或修改文件。' : '真实模式需在后端配置 OPENAI_API_KEY。'}</p>
          {error && <div className="error">{error}</div>}
        </section>
        <section className="card timeline-card"><div className="section-label">02 / 行动轨迹</div><div className="timeline-head"><h2>调查过程</h2><span className={`status ${run?.status || 'idle'}`}>{run ? ({running:'进行中',completed:'已完成',failed:'失败'}[run.status] || run.status) : '待开始'}</span></div>
          {!run && <div className="empty"><div className="empty-icon">⌕</div><p>发起调查后，这里会显示每次工具调用与返回证据。</p></div>}
          {run && <div className="events">{run.events.map((event, i) => <article className={`event ${event.kind}`} key={i}><div className="event-marker">{event.kind === 'report' ? '✓' : event.kind === 'error' ? '!' : event.kind === 'tool' ? '→' : '·'}</div><div><div className="event-title">{event.title}<time>{new Date(event.time).toLocaleTimeString('zh-CN')}</time></div><pre>{event.detail}</pre></div></article>)}{run.status === 'running' && <div className="working"><span className="spinner" />Agent 正在分析…</div>}</div>}
        </section>
      </div>
      <footer><span>READ · SEARCH · REASON</span><span>所有仓库操作均为只读</span></footer>
    </main>
  </div>
}

createRoot(document.getElementById('root')!).render(<React.StrictMode><App /></React.StrictMode>)
