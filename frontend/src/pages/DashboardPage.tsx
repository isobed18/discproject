import { useEffect, useMemo, useState } from 'react'
import { fetchJson } from '../api'
import type { AuditSummary } from '../types'

export function DashboardPage({ onOpenCorrelation }: { onOpenCorrelation: (cid: string) => void }) {
  const [summary, setSummary] = useState<AuditSummary | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      const { data } = await fetchJson<AuditSummary>('/audit-summary')
      setSummary(data)
    } catch (e: any) {
      setError(e?.message ?? 'Failed to load summary')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    const t = window.setInterval(load, 5000)
    return () => window.clearInterval(t)
  }, [])

  const kpis = useMemo(() => {
    if (!summary) return []
    const get = (k: string) => summary.counts_by_event_type?.[k] ?? 0
    return [
      { label: 'Issued', value: get('coupon_issued') },
      { label: 'Verified', value: get('coupon_verified') },
      { label: 'Revoked', value: get('coupon_revoked') },
      { label: 'Policy denied', value: get('coupon_issue_denied') },
    ]
  }, [summary])

  return (
    <div className="page">
      <div className="pageHeader">
        <div>
          <h2>Traceability dashboard</h2>
          <p className="muted">Audit events + end-to-end correlation for debugging.</p>
        </div>
        <div className="headerActions">
          <button className="btn" onClick={load} disabled={loading}>
            Refresh
          </button>
        </div>
      </div>

      {error && <div className="alert">{error}</div>}

      <div className="grid grid4">
        {kpis.map((k) => (
          <div key={k.label} className="card kpi">
            <div className="kpiLabel">{k.label}</div>
            <div className="kpiValue">{k.value}</div>
          </div>
        ))}
      </div>

      <div className="grid grid2">
        <div className="card">
          <h3>Kafka consumer</h3>
          {!summary ? (
            <div className="muted">Loading...</div>
          ) : (
            <div className="kv">
              <div className="row">
                <div className="key">Connected</div>
                <div className="val">
                  <span className={summary.kafka.connected ? 'pill ok' : 'pill warn'}>
                    {summary.kafka.connected ? 'Yes' : 'No'}
                  </span>
                </div>
              </div>
              <div className="row">
                <div className="key">Last ingest</div>
                <div className="val">{summary.kafka.last_ingest_at ?? '—'}</div>
              </div>
              <div className="row">
                <div className="key">Consumed total</div>
                <div className="val">{summary.kafka.consumed_total}</div>
              </div>
              <div className="row">
                <div className="key">Decode errors</div>
                <div className="val">{summary.kafka.decode_errors_total}</div>
              </div>
              {summary.kafka.last_error && (
                <div className="row">
                  <div className="key">Last error</div>
                  <div className="val mono">{summary.kafka.last_error}</div>
                </div>
              )}
            </div>
          )}
        </div>

        <div className="card">
          <h3>Audit buffer</h3>
          {!summary ? (
            <div className="muted">Loading...</div>
          ) : (
            <div className="kv">
              <div className="row">
                <div className="key">Size</div>
                <div className="val">
                  {summary.buffer.current} / {summary.buffer.max}
                </div>
              </div>
              <div className="row">
                <div className="key">Sources</div>
                <div className="val">
                  {Object.entries(summary.counts_by_source)
                    .map(([k, v]) => `${k}: ${v}`)
                    .join(' · ')}
                </div>
              </div>
              <div className="row">
                <div className="key">Actions</div>
                <div className="val">
                  {Object.entries(summary.counts_by_action)
                    .slice(0, 6)
                    .map(([k, v]) => `${k}: ${v}`)
                    .join(' · ')}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="card">
        <div className="cardHeader">
          <h3>Recent correlation flows</h3>
          <p className="muted">Click a correlation-id to open the timeline.</p>
        </div>
        {!summary ? (
          <div className="muted">Loading...</div>
        ) : summary.recent_correlations.length === 0 ? (
          <div className="muted">No correlation-ids captured yet.</div>
        ) : (
          <div className="tableWrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Correlation ID</th>
                  <th>Events</th>
                  <th>First</th>
                  <th>Last</th>
                  <th>Last action</th>
                </tr>
              </thead>
              <tbody>
                {summary.recent_correlations.map((c) => (
                  <tr key={c.correlation_id}>
                    <td>
                      <button className="linkBtn" onClick={() => onOpenCorrelation(c.correlation_id)}>
                        {c.correlation_id}
                      </button>
                    </td>
                    <td>{c.events}</td>
                    <td className="mono">{c.first_seen}</td>
                    <td className="mono">{c.last_seen}</td>
                    <td>{c.last_action ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
