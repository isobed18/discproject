import { useEffect, useMemo, useState } from 'react'
import { buildQuery, fetchJson } from '../api'
import type { AuditEvent, AuditListResponse } from '../types'
import { useDebouncedValue } from '../useDebouncedValue'
import { JsonBlock } from '../components/JsonBlock'

type SigFilter = 'any' | 'valid' | 'invalid'

export function AuditLogPage({ onOpenCorrelation }: { onOpenCorrelation: (cid: string) => void }) {
  const [resp, setResp] = useState<AuditListResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const [limit] = useState(200)
  const [offset, setOffset] = useState(0)

  const [eventType, setEventType] = useState('')
  const [actor, setActor] = useState('')
  const [action, setAction] = useState('')
  const [resource, setResource] = useState('')
  const [correlationId, setCorrelationId] = useState('')
  const [source, setSource] = useState('')
  const [sig, setSig] = useState<SigFilter>('any')
  const [text, setText] = useState('')
  const [timeFrom, setTimeFrom] = useState('')
  const [timeTo, setTimeTo] = useState('')

  const debouncedText = useDebouncedValue(text, 300)

  const signature_valid = useMemo(() => {
    if (sig === 'valid') return true
    if (sig === 'invalid') return false
    return undefined
  }, [sig])

  const query = useMemo(() => {
    return buildQuery({
      limit,
      offset,
      event_type: eventType || undefined,
      actor: actor || undefined,
      action: action || undefined,
      resource: resource || undefined,
      correlation_id: correlationId || undefined,
      source: source || undefined,
      signature_valid,
      text: debouncedText || undefined,
      time_from: timeFrom || undefined,
      time_to: timeTo || undefined,
    })
  }, [limit, offset, eventType, actor, action, resource, correlationId, source, signature_valid, debouncedText, timeFrom, timeTo])

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      const { data } = await fetchJson<AuditListResponse>(`/audit-events${query}`)
      setResp(data)
    } catch (e: any) {
      setError(e?.message ?? 'Failed to load audit events')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [query])

  const total = resp?.total ?? 0
  const items: AuditEvent[] = resp?.items ?? []

  const canPrev = offset > 0
  const canNext = offset + limit < total

  return (
    <div className="page">
      <div className="pageHeader">
        <div>
          <h2>Audit log</h2>
          <p className="muted">Filter/search across enriched audit events (actor, action, correlation-id, gateway info).</p>
        </div>
        <div className="headerActions">
          <button className="btn" onClick={load} disabled={loading}>
            Refresh
          </button>
        </div>
      </div>

      {error && <div className="alert">{error}</div>}

      <div className="card">
        <div className="filters">
          <div className="field">
            <label>Search</label>
            <input value={text} onChange={(e) => setText(e.target.value)} placeholder="actor, resource, correlation-id, details..." />
          </div>
          <div className="field">
            <label>Event type</label>
            <input value={eventType} onChange={(e) => setEventType(e.target.value)} placeholder="coupon_issued" />
          </div>
          <div className="field">
            <label>Action</label>
            <input value={action} onChange={(e) => setAction(e.target.value)} placeholder="issue / verify / revoke" />
          </div>
          <div className="field">
            <label>Actor</label>
            <input value={actor} onChange={(e) => setActor(e.target.value)} placeholder="admin / gateway" />
          </div>
          <div className="field">
            <label>Resource (JTI)</label>
            <input value={resource} onChange={(e) => setResource(e.target.value)} placeholder="uuid..." />
          </div>
          <div className="field">
            <label>Correlation ID</label>
            <input value={correlationId} onChange={(e) => setCorrelationId(e.target.value)} placeholder="uuid..." />
          </div>
          <div className="field">
            <label>Source</label>
            <select value={source} onChange={(e) => setSource(e.target.value)}>
              <option value="">Any</option>
              <option value="local">Local</option>
              <option value="kafka">Kafka</option>
            </select>
          </div>
          <div className="field">
            <label>Signature</label>
            <select value={sig} onChange={(e) => setSig(e.target.value as SigFilter)}>
              <option value="any">Any</option>
              <option value="valid">Valid</option>
              <option value="invalid">Invalid</option>
            </select>
          </div>
          <div className="field">
            <label>From (ISO)</label>
            <input value={timeFrom} onChange={(e) => setTimeFrom(e.target.value)} placeholder="2025-12-18T09:00:00Z" />
          </div>
          <div className="field">
            <label>To (ISO)</label>
            <input value={timeTo} onChange={(e) => setTimeTo(e.target.value)} placeholder="2025-12-18T18:00:00Z" />
          </div>
        </div>

        <div className="tableMeta">
          <div className="muted">
            Showing <span className="mono">{items.length}</span> of <span className="mono">{total}</span>
          </div>
          <div className="pager">
            <button className="btn secondary" onClick={() => setOffset((o) => Math.max(0, o - limit))} disabled={!canPrev}>
              Prev
            </button>
            <button className="btn secondary" onClick={() => setOffset((o) => (canNext ? o + limit : o))} disabled={!canNext}>
              Next
            </button>
          </div>
        </div>

        <div className="tableWrap">
          <table className="table">
            <thead>
              <tr>
                <th>Time</th>
                <th>Event</th>
                <th>Actor</th>
                <th>Action</th>
                <th>Resource</th>
                <th>Correlation</th>
                <th>Gateway</th>
                <th>Source</th>
                <th>Details</th>
              </tr>
            </thead>
            <tbody>
              {items.map((e) => (
                <tr key={e.event_id}>
                  <td className="mono">{e.timestamp ? new Date(e.timestamp).toLocaleString() : '—'}</td>
                  <td>{e.event_type ?? '—'}</td>
                  <td>{e.actor ?? '—'}</td>
                  <td>{e.action ?? '—'}</td>
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
                  <td className="mono small">{e.gateway?.gateway_id ?? '—'}</td>
                  <td>
                    <span className="pill">{e.source ?? '—'}</span>
                    {e.signature_valid === true && <span className="pill ok">sig</span>}
                    {e.signature_valid === false && <span className="pill warn">bad-sig</span>}
                    {e.parse_error && <span className="pill warn">parse</span>}
                  </td>
                  <td style={{ minWidth: 320 }}>
                    <JsonBlock value={e.details} />
                  </td>
                </tr>
              ))}
              {items.length === 0 && (
                <tr>
                  <td colSpan={9} className="muted">
                    No audit events found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
