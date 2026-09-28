import React, { useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import './style.css'
import './enhancements.css'

type Event = { time: string; kind: string; title: string; detail: string }
type Evidence = { citation: string; quote: string; explanation: string }
type Report = { hypothesis: string; evidence: Evidence[]; alternatives: string[]; confidence: '低' | '中' | '高'; next_steps: string[]; limitations: string[] }
type Run = { id: string; status: string; repository: string; issue: string; demo: boolean; scenario: string | null; events: Event[]; answer: string | null; report: Report | null; created_at: string }
type RunSummary = Pick<Run, 'id' | 'status' | 'issue' | 'demo' | 'created_at' | 'scenario'>
type Health = { status: string; api_key_configured: boolean; demo_repository: string }
type Scenario = { id: string; title: string; issue: string }
const statusText: Record<string, string> = { running: '进行中', completed: '已完成', failed: '失败' }

function App() {
  const [health, setHealth] = useState<Health | null>(null)
  const [scenarios, setScenarios] = useState<Scenario[]>([])
  const [history, setHistory] = useState<RunSummary[]>([])
  const [repository, setRepository] = useState('')
  const [issue, setIssue] = useState('divide(5, 2) 返回 2，但预期是 2.5。请定位原因。')
  const [scenario, setScenario] = useState('division')
  const [demo, setDemo] = useState(true)
  const [run, setRun] = useState<Run | null>(null)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function refreshHistory() {
    const response = await fetch('/api/runs')
    if (response.ok) setHistory(await response.json())
  }

  useEffect(() => {
    Promise.all([fetch('/api/health').then(r => r.json()), fetch('/api/scenarios').then(r => r.json())])
      .then(([healthData, scenarioData]: [Health, Scenario[]]) => {
        setHealth(healthData)
        setRepository(healthData.demo_repository)
        setScenarios(scenarioData)
        refreshHistory().catch(() => undefined)
      }).catch(() => setError('无法连接后端，请先启动 API 服务。'))
  }, [])

  useEffect(() => {
    if (!run || run.status !== 'running') return
    const timer = window.setInterval(async () => {
      try {
        const response = await fetch(`/api/runs/${run.id}`)
        if (!response.ok) throw new Error('读取任务失败')
        const updated: Run = await response.json()
        setRun(updated)
        if (updated.status !== 'running') refreshHistory().catch(() => undefined)
      } catch { setError('任务状态更新失败，请检查后端服务。') }
    }, 900)
    return () => window.clearInterval(timer)
  }, [run?.id, run?.status])

  async function start() {
    setError('')
    setRun(null)
    setSubmitting(true)
    try {
      const response = await fetch('/api/runs', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ issue, repository, demo, scenario }) })
      const data = await response.json()
      if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : '无法创建任务')
      const result = await fetch(`/api/runs/${data.id}`)
      if (!result.ok) throw new Error('无法读取新任务')
      setRun(await result.json())
      refreshHistory().catch(() => undefined)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : '发生未知错误')
    } finally { setSubmitting(false) }
  }

  async function openRun(id: string) {
    setError('')
    try {
      const response = await fetch(`/api/runs/${id}`)
      if (!response.ok) throw new Error('历史任务读取失败')
      setRun(await response.json())
    } catch (cause) { setError(cause instanceof Error ? cause.message : '发生未知错误') }
  }

  function selectScenario(id: string) {
    setScenario(id)
    const selected = scenarios.find(item => item.id === id)
    if (selected) setIssue(selected.issue)
  }

  const toolCount = run?.events.filter(item => item.kind === 'tool').length ?? 0
  const verified = run?.events.some(item => item.kind === 'verification' && item.title.includes('已核验')) ?? false
  const timeline = run?.events.filter(item => item.kind !== 'report') ?? []

  return <div className="app">
    <header><div className="brand"><span className="brand-icon">⌁</span><span>REPO SLEUTH</span></div><span className="badge">EVIDENCE-FIRST · AGENT WORKBENCH</span></header>
    <main>
      <section className="hero"><div className="eyebrow">CODE INVESTIGATION AGENT / V0.3 · LANGGRAPH</div><h1>从 Bug 描述到可核验的代码证据。</h1><p>状态图驱动调查、校验与补查；持久化检查点支持中断恢复。每条证据都关联实际观察过的代码原文。</p></section>
      <div className="layout">
        <div className="left-column">
          <section className="card form-card"><div className="section-label">01 / 发起调查</div><h2>调查任务</h2>
            <label className="toggle"><input type="checkbox" checked={demo} onChange={e => setDemo(e.target.checked)} /><span>确定性演示 · 无需 API Key</span></label>
            {demo && <><label htmlFor="scenario">演示场景</label><select id="scenario" value={scenario} onChange={e => selectScenario(e.target.value)}>{scenarios.map(item => <option key={item.id} value={item.id}>{item.title}</option>)}</select></>}
            {!demo && <><label htmlFor="repo">本地仓库路径</label><input id="repo" value={repository} onChange={e => setRepository(e.target.value)} placeholder="/absolute/path/to/repo" /></>}
            <label htmlFor="issue">问题描述</label><textarea id="issue" value={issue} onChange={e => setIssue(e.target.value)} rows={5} disabled={demo} />
            <button className="primary-button" onClick={start} disabled={submitting || !!(run && run.status === 'running') || issue.trim().length < 8}>{submitting ? '正在创建…' : run?.status === 'running' ? '正在调查…' : '开始调查'} <span>↗</span></button>
            <p className="hint">{demo ? '演示会运行真实读取工具，并校验证据引用；模型调用仅在真实模式发生。' : health?.api_key_configured ? '真实模式已就绪：只读仓库，不执行代码或修改文件。' : '真实模式需在后端配置 OPENAI_API_KEY。'}</p>
            {error && <div className="error">{error}</div>}
          </section>
          <section className="card history-card"><div className="section-label">02 / 调查档案</div><h2>最近任务</h2>
            {history.length === 0 ? <p className="muted">还没有调查记录。</p> : <div className="history-list">{history.map(item => <button type="button" className={`history-item ${run?.id === item.id ? 'selected' : ''}`} key={item.id} onClick={() => openRun(item.id)}><span className="history-title">{item.issue}</span><span className="history-meta">{item.demo ? '演示' : '真实'} · {statusText[item.status] || item.status} · {new Date(item.created_at).toLocaleString('zh-CN')}</span></button>)}</div>}
          </section>
        </div>
        <div className="right-column">
          <section className="card timeline-card"><div className="section-label">03 / 行动轨迹</div><div className="timeline-head"><h2>调查过程</h2><span className={`status ${run?.status || 'idle'}`}>{run ? statusText[run.status] || run.status : '待开始'}</span></div>
            {!run && <div className="empty"><div className="empty-icon">⌕</div><p>发起调查或打开历史任务，这里会显示工具调用、返回内容和引用校验。</p></div>}
            {run && <><div className="metrics"><span><strong>{toolCount}</strong> 次工具调用</span><span><strong>{verified ? '✓' : '—'}</strong> 引用校验</span><span><strong>{run.demo ? 'DEMO' : 'LIVE'}</strong> 运行模式</span></div><div className="events">{timeline.map((event, i) => <article className={`event ${event.kind}`} key={i}><div className="event-marker">{event.kind === 'error' ? '!' : event.kind === 'verification' ? '✓' : event.kind === 'tool' ? '→' : '·'}</div><div><div className="event-title">{event.title}<time>{new Date(event.time).toLocaleTimeString('zh-CN')}</time></div><pre>{event.detail}</pre></div></article>)}{run.status === 'running' && <div className="working"><span className="spinner" />Agent 正在分析…</div>}</div></>}
          </section>
          {run?.answer && <section className="card report-card"><div className="section-label">04 / 证据报告</div><div className="report-head"><h2>调查结论</h2><span className="verified-badge">✓ 原文已核验</span></div>
            {run.report ? <div className="structured-report">
              <div className="report-section"><span className="report-label">根因假设 · 置信度 {run.report.confidence}</span><p>{run.report.hypothesis}</p></div>
              <div className="report-section"><span className="report-label">支持证据</span>{run.report.evidence.map((item, index) => <div className="evidence-item" key={`${item.citation}-${index}`}><code>{item.citation}</code><p>{item.explanation}</p><blockquote>{item.quote}</blockquote></div>)}</div>
              <div className="report-section"><span className="report-label">其他可能</span><p>{run.report.alternatives.length ? run.report.alternatives.join('；') : '暂无'}</p></div>
              <div className="report-section"><span className="report-label">下一步验证</span><p>{run.report.next_steps.join('；')}</p></div>
              {run.report.limitations.length > 0 && <div className="report-section"><span className="report-label">局限</span><p>{run.report.limitations.join('；')}</p></div>}
            </div> : <p className="report-text">{run.answer}</p>}
            <p className="report-note">引用与摘录校验只证明来源一致，不证明根因推理必然正确；仍需人工审查。</p></section>}
        </div>
      </div>
      <footer><span>READ · SEARCH · VERIFY · REASON</span><span>所有仓库操作均为只读</span></footer>
    </main>
  </div>
}

createRoot(document.getElementById('root')!).render(<React.StrictMode><App /></React.StrictMode>)
