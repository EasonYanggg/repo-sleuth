import React, { useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import './style.css'

type Event = { time: string; kind: string; title: string; detail: string }
type Evidence = { citation: string; quote: string; explanation: string }
type Report = { hypothesis: string; evidence: Evidence[]; alternatives: string[]; confidence: '低' | '中' | '高'; next_steps: string[]; limitations: string[] }
type Run = { id: string; status: string; repository: string; issue: string; demo: boolean; scenario: string | null; events: Event[]; answer: string | null; report: Report | null; created_at: string }
type RunSummary = Pick<Run, 'id' | 'status' | 'issue' | 'demo' | 'created_at' | 'scenario'>
type Health = { status: string; api_key_configured: boolean; demo_repository: string }
type Scenario = { id: string; title: string; issue: string }

const statusText: Record<string, string> = { running: '调查中', completed: '已完成', failed: '失败' }
const flow = [
  { number: '01', title: '检索仓库', detail: '定位相关代码与调用路径' },
  { number: '02', title: '形成假设', detail: '把观察连接成因果解释' },
  { number: '03', title: '核验证据', detail: '引用与原文逐项对照' },
]

function BrandMark() {
  return <svg viewBox="0 0 40 40" fill="none" aria-hidden="true">
    <path d="M6 20h8l4-9 5 18 4-9h7" stroke="currentColor" strokeWidth="2.3" strokeLinecap="round" strokeLinejoin="round" />
    <path d="M8 8h5M8 8v5M32 8h-5M32 8v5M8 32h5M8 32v-5M32 32h-5M32 32v-5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
  </svg>
}

function ArrowIcon() {
  return <svg viewBox="0 0 20 20" fill="none" aria-hidden="true"><path d="M4 15 15 4M6 4h9v9" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" /></svg>
}

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

  function changeMode(nextDemo: boolean) {
    setDemo(nextDemo)
    setError('')
    if (nextDemo) selectScenario(scenario)
  }

  const toolCount = run?.events.filter(item => item.kind === 'tool').length ?? 0
  const verified = run?.events.some(item => item.kind === 'verification' && item.title.includes('已核验')) ?? false
  const timeline = run?.events.filter(item => item.kind !== 'report') ?? []
  const runActive = run?.status === 'running'

  return <div className="app-shell">
    <header className="topbar">
      <div className="topbar-inner">
        <div className="brand"><span className="brand-mark"><BrandMark /></span><span className="brand-copy"><strong>REPO SLEUTH</strong><small>CODE FORENSICS LAB</small></span></div>
        <div className="header-right"><span className="header-version">WORKBENCH / 0.3</span><span className={`connection-pill ${health ? 'online' : 'offline'}`}><i />{health ? '本地服务已连接' : '等待后端连接'}</span></div>
      </div>
    </header>

    <main className="page-content">
      <section className="hero" aria-labelledby="hero-title">
        <div className="hero-copy">
          <div className="eyebrow"><span className="eyebrow-line" />EVIDENCE-DRIVEN CODE INVESTIGATION</div>
          <h1 id="hero-title">让每一个判断，<br /><span>都有代码作证。</span></h1>
          <p>输入 Bug 现象，Agent 沿着代码寻找线索。调查步骤可回看，结论附带可核验的文件、行号与原文。</p>
          <div className="hero-tags"><span>LANGGRAPH WORKFLOW</span><span>READ-ONLY TOOLS</span><span>VERIFIED CITATIONS</span></div>
        </div>
        <div className="flow-card" aria-label="调查流程">
          <div className="flow-card-head"><span>INVESTIGATION FLOW</span><span className={`flow-live ${health ? '' : 'offline'}`}><i /> {health ? 'SYSTEM READY' : 'API OFFLINE'}</span></div>
          <div className="flow-list">{flow.map((step, index) => <div className="flow-step" key={step.number}>
            <span className={`flow-index ${index === 0 ? 'current' : ''}`}>{step.number}</span>
            <div><strong>{step.title}</strong><small>{step.detail}</small></div>
            <span className="flow-arrow">↗</span>
          </div>)}</div>
          <div className="flow-card-foot"><span>OBSERVE</span><span>REASON</span><span>VERIFY</span></div>
        </div>
      </section>

      <div className="workspace-grid">
        <div className="left-column">
          <section className="panel form-panel" aria-labelledby="new-run-title">
            <div className="panel-heading"><div><span className="section-kicker">01 / NEW INVESTIGATION</span><h2 id="new-run-title">发起调查</h2></div><span className="panel-symbol">⌕</span></div>
            <p className="panel-intro">选择调查模式，给 Agent 一个明确的问题。</p>

            <div className="field-group"><span className="field-label">运行模式</span>
              <div className="mode-switch" role="group" aria-label="运行模式">
                <button type="button" className={demo ? 'active' : ''} aria-pressed={demo} onClick={() => changeMode(true)}><strong>演示模式</strong><small>无需 API Key</small></button>
                <button type="button" className={!demo ? 'active' : ''} aria-pressed={!demo} onClick={() => changeMode(false)}><strong>真实调查</strong><small>调用模型</small></button>
              </div>
            </div>

            {demo ? <div className="field-group"><label className="field-label" htmlFor="scenario">预设故障场景</label><div className="select-wrap"><select id="scenario" value={scenario} onChange={e => selectScenario(e.target.value)}>{scenarios.map(item => <option key={item.id} value={item.id}>{item.title}</option>)}</select><span aria-hidden="true">⌄</span></div></div>
              : <div className="field-group"><label className="field-label" htmlFor="repo">本地仓库路径</label><input id="repo" value={repository} onChange={e => setRepository(e.target.value)} placeholder="/absolute/path/to/repo" spellCheck={false} /></div>}

            <div className="field-group"><label className="field-label" htmlFor="issue">问题描述</label><textarea id="issue" value={issue} onChange={e => setIssue(e.target.value)} rows={5} readOnly={demo} aria-describedby="issue-help" /></div>
            <p className="field-help" id="issue-help">{demo ? '演示场景会使用真实只读工具，结论由预设脚本生成。' : health?.api_key_configured ? '模型已就绪；只读取仓库，不运行或修改代码。' : '真实调查需要在后端配置 OPENAI_API_KEY。'}</p>
            {error && <div className="error-banner" role="alert"><span>!</span>{error}</div>}
            <button className="start-button" type="button" onClick={start} disabled={submitting || runActive || issue.trim().length < 8}><span>{submitting ? '正在创建任务…' : runActive ? '调查进行中…' : '开始调查'}</span><ArrowIcon /></button>
            <div className="form-footnote"><span className="small-lock">◇</span> 工具仅可读取仓库，不会执行代码或修改文件</div>
          </section>

          <section className="panel history-panel" aria-labelledby="history-title">
            <div className="panel-heading compact"><div><span className="section-kicker">02 / CASE ARCHIVE</span><h2 id="history-title">调查档案</h2></div><span className="count-badge">{history.length.toString().padStart(2, '0')}</span></div>
            {history.length === 0 ? <div className="history-empty">还没有调查记录。完成首次调查后会显示在这里。</div> : <div className="history-list">{history.map(item => <button type="button" className={`history-item ${run?.id === item.id ? 'selected' : ''}`} key={item.id} onClick={() => openRun(item.id)}>
              <span className="history-top"><span className={`history-status ${item.status}`}><i />{statusText[item.status] || item.status}</span><span className="history-date">{new Date(item.created_at).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })}</span></span>
              <span className="history-title">{item.issue}</span><span className="history-mode">{item.demo ? 'DEMO / 预设演示' : 'LIVE / 模型调查'} <span aria-hidden="true">↗</span></span>
            </button>)}</div>}
          </section>
        </div>

        <div className="right-column">
          <section className="panel timeline-panel" aria-labelledby="timeline-title">
            <div className="panel-heading timeline-heading"><div><span className="section-kicker">03 / TRACE LOG</span><h2 id="timeline-title">调查轨迹</h2></div><span className={`run-status ${run?.status || 'idle'}`}><i />{run ? statusText[run.status] || run.status : '等待任务'}</span></div>
            {!run ? <div className="trace-empty"><div className="trace-graphic"><span className="trace-ring one" /><span className="trace-ring two" /><span className="trace-core">⌕</span></div><h3>线索会在这里出现</h3><p>开始一次调查，或从左侧打开历史任务。工具调用、观察结果和验证过程都会按时间排列。</p><span className="empty-prompt">AWAITING INVESTIGATION</span></div>
              : <><div className="trace-metrics"><div><small>TOOL CALLS</small><strong>{toolCount.toString().padStart(2, '0')}</strong></div><div><small>EVIDENCE CHECK</small><strong className={verified ? 'positive' : ''}>{verified ? 'PASSED' : 'PENDING'}</strong></div><div><small>RUN MODE</small><strong>{run.demo ? 'DEMO' : 'LIVE'}</strong></div></div>
                <div className="events">{timeline.map((item, index) => <article className={`event event-${item.kind}`} key={`${item.time}-${index}`}>
                  <span className="event-marker">{item.kind === 'error' ? '!' : item.kind === 'verification' ? '✓' : item.kind === 'tool' ? '↗' : item.kind === 'stage' ? '◇' : '·'}</span>
                  <div className="event-body"><div className="event-top"><span className="event-kind">{item.kind === 'tool' ? 'TOOL CALL' : item.kind === 'result' ? 'OBSERVATION' : item.kind === 'verification' ? 'EVIDENCE CHECK' : item.kind === 'stage' ? 'WORKFLOW' : 'ERROR'}</span><time>{new Date(item.time).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</time></div>
                    <details open={item.kind === 'verification' || item.kind === 'error'}><summary>{item.title}<span className="disclosure">⌄</span></summary><pre>{item.detail}</pre></details>
                  </div>
                </article>)}{runActive && <div className="working"><span className="spinner" />Agent 正在分析代码…</div>}</div>
              </>}
          </section>

          {run?.answer && <section className="panel report-panel" aria-labelledby="report-title">
            <div className="panel-heading report-heading"><div><span className="section-kicker">04 / EVIDENCE REPORT</span><h2 id="report-title">调查结论</h2></div><span className="verified-badge">✓ 来源已核验</span></div>
            {run.report ? <div className="structured-report">
              <div className="hypothesis-card"><div className="report-label-row"><span>ROOT CAUSE HYPOTHESIS</span><span className={`confidence confidence-${run.report.confidence}`}>置信度 · {run.report.confidence}</span></div><p>{run.report.hypothesis}</p></div>
              <div className="report-section"><div className="report-section-title"><span className="report-number">01</span><h3>支持证据</h3><span className="report-count">{run.report.evidence.length} SOURCES</span></div><div className="evidence-list">{run.report.evidence.map((item, index) => <div className="evidence-item" key={`${item.citation}-${index}`}><div className="evidence-top"><code>{item.citation}</code><span>VERIFIED SOURCE</span></div><p>{item.explanation}</p><blockquote>{item.quote}</blockquote></div>)}</div></div>
              <div className="report-bottom-grid"><div className="report-section"><div className="report-section-title"><span className="report-number">02</span><h3>其他可能</h3></div><p>{run.report.alternatives.length ? run.report.alternatives.join('；') : '暂无其他已识别的假设。'}</p></div><div className="report-section"><div className="report-section-title"><span className="report-number">03</span><h3>下一步验证</h3></div><p>{run.report.next_steps.join('；')}</p></div></div>
              {run.report.limitations.length > 0 && <div className="limitations"><strong>调查局限</strong><p>{run.report.limitations.join('；')}</p></div>}
            </div> : <p className="legacy-report">{run.answer}</p>}
            <p className="report-note">引用与摘录校验只证明来源一致，不证明根因推理必然正确；最终判断仍需人工审查。</p>
          </section>}
        </div>
      </div>
      <footer className="footer"><span>REPO SLEUTH <i>©</i> 2026</span><span>OBSERVE <b>→</b> REASON <b>→</b> VERIFY</span><span>BUILT FOR EVIDENCE, NOT GUESSWORK.</span></footer>
    </main>
  </div>
}

createRoot(document.getElementById('root')!).render(<React.StrictMode><App /></React.StrictMode>)
