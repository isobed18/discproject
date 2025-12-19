import { useEffect, useMemo, useState } from 'react'
import { buildQuery, fetchJson } from '../api'
import type { AuditEvent, AuditListResponse } from '../types'
import { useDebouncedValue } from '../useDebouncedValue'
import { JsonBlock } from '../components/JsonBlock'

type SigFilter = 'any' | 'valid' | 'invalid'

export function KafkaConsumerPage({ onOpenCorrelation }: { onOpenCorrelation: (cid: string) => void }) {
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
  const [sig, setSig] = useState<SigFilter>('any')
  const [text, setText] = useState('')

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
      signature_valid,
      text: debouncedText || undefined,
    })
  }, [limit, offset, eventType, actor, action, resource, correlationId, signature_valid, debouncedText])

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      const { data } = await fetchJson<AuditListResponse>(`/kafka-events${query}`)
      setResp(data)
    } catch (e: any) {
      setError(e?.message ?? 'Failed to load Kafka events')
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
          <h2>Kafka consumer</h2>
          <p className="muted">Raw consumed audit events (signature verification, parse errors, raw payload).</p>
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
            <input value={text} onChange={(e) => setText(e.target.value)} placeholder="event_type, actor, details..." />
          </div>
          <div className="field">
            <label>Event type</label>
            <input value={eventType} onChange={(e) => setEventType(e.target.value)} placeholder="coupon_verified" />
          </div>
          <div className="field">
            <label>Action</label>
            <input value={action} onChange={(e) => setAction(e.target.value)} placeholder="verify" />
          </div>
          <div className="field">
            <label>Actor</label>
            <input value={actor} onChange={(e) => setActor(e.target.value)} placeholder="gateway" />
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
            <label>Signature</label>
            <select value={sig} onChange={(e) => setSig(e.target.value as SigFilter)}>
              <option value="any">Any</option>
              <option value="valid">Valid</option>
              <option value="invalid">Invalid</option>
            </select>
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
                <th>Ingested</th>
                <th>Sig</th>
                <th>Parse</th>
                <th>Event</th>
                <th>Actor</th>
                <th>Action</th>
                <th>Resource</th>
                <th>Correlation</th>
                <th>Raw</th>
              </tr>
            </thead>
            <tbody>
              {items.map((e) => (
                <tr key={e.event_id}>
                  <td className="mono">{e.ingested_at ? new Date(e.ingested_at).toLocaleString() : '—'}</td>
                  <td>{e.signature_valid === true ? <span className="pill ok">valid</span> : e.signature_valid === false ? <span className="pill warn">invalid</span> : <span className="pill">—</span>}</td>
                  <td>{e.parse_error ? <span className="pill warn">error</span> : <span className="pill ok">ok</span>}</td>
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
                  <td style={{ minWidth: 320 }}>
                    <JsonBlock value={{ raw: e.raw, parse_error: e.parse_error }} />
                  </td>
                </tr>
              ))}
              {items.length === 0 && (
                <tr>
                  <td colSpan={9} className="muted">
                    No Kafka events found.
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
