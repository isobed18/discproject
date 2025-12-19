import { useEffect, useMemo, useState } from 'react'
import { buildQuery, fetchJson } from '../api'
import type { AuditEvent, AuditListResponse } from '../types'
import { JsonBlock } from '../components/JsonBlock'

export function RevokeOpsPage({ onOpenCorrelation }: { onOpenCorrelation: (cid: string) => void }) {
  const [jti, setJti] = useState('')
  const [reason, setReason] = useState('unspecified')
  const [customReason, setCustomReason] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState<any | null>(null)
  const [lastCorrelation, setLastCorrelation] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const effectiveReason = reason === 'custom' ? (customReason.trim() || 'unspecified') : reason

  const submit = async () => {
    setSubmitting(true)
    setError(null)
    setResult(null)
    setLastCorrelation(null)
    try {
      const { data, headers } = await fetchJson<any>('/revoke', {
        method: 'POST',
        headers: {
          'x-actor': 'admin-ui',
        },
        body: JSON.stringify({ jti: jti.trim(), reason: effectiveReason }),
      })
      setResult(data)
      const cid = headers.get('x-correlation-id')
      if (cid) setLastCorrelation(cid)
    } catch (e: any) {
      setError(e?.message ?? 'Revoke failed')
    } finally {
      setSubmitting(false)
    }
  }

  // Show recent revoke audit events
  const [recent, setRecent] = useState<AuditEvent[]>([])
  const loadRecent = async () => {
    try {
      const q = buildQuery({ limit: 10, offset: 0, event_type: 'coupon_revoked' })
      const { data } = await fetchJson<AuditListResponse>(`/audit-events${q}`)
      setRecent(data.items ?? [])
    } catch {
      setRecent([])
    }
  }

  useEffect(() => {
    loadRecent()
    const t = window.setInterval(loadRecent, 5000)
    return () => window.clearInterval(t)
  }, [])

  const canSubmit = useMemo(() => jti.trim().length > 10 && !submitting, [jti, submitting])

  return (
    <div className="page">
      <div className="pageHeader">
        <div>
          <h2>Revoke flow</h2>
          <p className="muted">Revoke a coupon by JTI, capture reason, and confirm the audit trail end-to-end.</p>
        </div>
      </div>

      {error && <div className="alert">{error}</div>}

      <div className="grid grid2">
        <div className="card">
          <h3>Operation panel</h3>
          <div className="rowWrap">
            <div className="field" style={{ flex: 1 }}>
              <label>JTI</label>
              <input value={jti} onChange={(e) => setJti(e.target.value)} placeholder="uuid..." />
            </div>
          </div>

          <div className="rowWrap" style={{ marginTop: 8 }}>
            <div className="field" style={{ minWidth: 220 }}>
              <label>Reason</label>
              <select value={reason} onChange={(e) => setReason(e.target.value)}>
                <option value="unspecified">Unspecified</option>
                <option value="compromised">Compromised credential</option>
                <option value="user_request">User request</option>
                <option value="policy_change">Policy change</option>
                <option value="abuse">Suspected abuse</option>
                <option value="custom">Custom…</option>
              </select>
            </div>
            {reason === 'custom' && (
              <div className="field" style={{ flex: 1 }}>
                <label>Custom reason</label>
                <input value={customReason} onChange={(e) => setCustomReason(e.target.value)} placeholder="free text" />
              </div>
            )}
          </div>

          <div className="rowWrap" style={{ marginTop: 12 }}>
            <button className="btn" onClick={submit} disabled={!canSubmit}>
              {submitting ? 'Revoking…' : 'Revoke'}
            </button>
            <button className="btn secondary" onClick={() => { setJti(''); setReason('unspecified'); setCustomReason(''); setResult(null); setLastCorrelation(null); setError(null) }}>
              Clear
            </button>
          </div>

          {result && (
            <div style={{ marginTop: 16 }}>
              <div className="alert ok">Revocation executed.</div>
              <JsonBlock value={result} />
              {lastCorrelation && (
                <div style={{ marginTop: 8 }}>
                  <div className="muted">Correlation ID</div>
                  <button className="linkBtn" onClick={() => onOpenCorrelation(lastCorrelation)}>
                    {lastCorrelation}
                  </button>
                </div>
              )}
            </div>
          )}
        </div>

        <div className="card">
          <h3>Confirmation</h3>
          <p className="muted">
            After you revoke, you should see a <span className="mono">coupon_revoked</span> audit event showing up below (and in the Audit Log).
          </p>

          <div className="tableWrap" style={{ marginTop: 12 }}>
            <table className="table">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Actor</th>
                  <th>Resource</th>
                  <th>Correlation</th>
                  <th>Reason</th>
                </tr>
              </thead>
              <tbody>
                {recent.map((e) => (
                  <tr key={e.event_id}>
                    <td className="mono">{e.timestamp ? new Date(e.timestamp).toLocaleString() : '—'}</td>
                    <td>{e.actor ?? '—'}</td>
                    <td className="mono small">{e.resource ?? '—'}</td>
                    <td>
                      {e.correlation_id ? (
                        <button className="linkBtn" onClick={() => onOpenCorrelation(e.correlation_id!)}>
                          {e.correlation_id}
                        </button>
                      ) : (
                        '—'
                      )}
                    </td>
                    <td className="mono small">{e.details?.reason ?? '—'}</td>
                  </tr>
                ))}
                {recent.length === 0 && (
                  <tr>
                    <td colSpan={5} className="muted">
                      No revoke events yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}
