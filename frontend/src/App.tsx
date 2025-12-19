import { useEffect, useMemo, useState } from 'react'
import './App.css'

import { DashboardPage } from './pages/DashboardPage'
import { AuditLogPage } from './pages/AuditLogPage'
import { KafkaConsumerPage } from './pages/KafkaConsumerPage'
import { CorrelationDebugPage } from './pages/CorrelationDebugPage'
import { RevokeOpsPage } from './pages/RevokeOpsPage'

type Page = 'dashboard' | 'audit' | 'kafka' | 'debug' | 'revoke'

function pageFromHash(): Page {
  const h = window.location.hash || '#/dashboard'
  if (h.startsWith('#/audit')) return 'audit'
  if (h.startsWith('#/kafka')) return 'kafka'
  if (h.startsWith('#/debug')) return 'debug'
  if (h.startsWith('#/revoke')) return 'revoke'
  return 'dashboard'
}

function navigate(page: Page, query?: Record<string, string>) {
  const base = `#/${page}`
  if (!query || Object.keys(query).length === 0) {
    window.location.hash = base
    return
  }
  const usp = new URLSearchParams(query)
  window.location.hash = `${base}?${usp.toString()}`
}

export default function App() {
  const [page, setPage] = useState<Page>(pageFromHash())

  useEffect(() => {
    const onHash = () => setPage(pageFromHash())
    window.addEventListener('hashchange', onHash)
    return () => window.removeEventListener('hashchange', onHash)
  }, [])

  useEffect(() => {
    if (!window.location.hash) navigate('dashboard')
  }, [])

  const navItems = useMemo(
    () =>
      [
        { key: 'dashboard', label: 'Dashboard', icon: '⎈' },
        { key: 'audit', label: 'Audit log', icon: '🧾' },
        { key: 'kafka', label: 'Kafka consumer', icon: '🧵' },
        { key: 'debug', label: 'Correlation debug', icon: '🕵️' },
        { key: 'revoke', label: 'Revoke ops', icon: '⛔' },
      ] as Array<{ key: Page; label: string; icon: string }>,
    [],
  )

  const openCorrelation = (cid: string) => {
    navigate('debug', { cid })
  }

  return (
    <div className="appShell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brandMark">DISC</div>
          <div className="brandText">
            <div className="brandTitle">Admin Console</div>
            <div className="brandSub">Auditing & Traceability</div>
          </div>
        </div>

        <nav className="nav">
          {navItems.map((i) => (
            <button
              key={i.key}
              className={page === i.key ? 'navItem active' : 'navItem'}
              onClick={() => navigate(i.key)}
            >
              <span className="navIcon">{i.icon}</span>
              <span>{i.label}</span>
            </button>
          ))}
        </nav>

        <div className="sidebarFooter">
          <div className="muted small">RBAC UI hookup postponed to next sprint.</div>
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <div className="topTitle">{navItems.find((n) => n.key === page)?.label}</div>
        </header>

        <div className="content">
          {page === 'dashboard' && <DashboardPage onOpenCorrelation={openCorrelation} />}
          {page === 'audit' && <AuditLogPage onOpenCorrelation={openCorrelation} />}
          {page === 'kafka' && <KafkaConsumerPage onOpenCorrelation={openCorrelation} />}
          {page === 'debug' && <CorrelationDebugPage />}
          {page === 'revoke' && <RevokeOpsPage onOpenCorrelation={openCorrelation} />}
        </div>
      </main>
    </div>
  )
}
