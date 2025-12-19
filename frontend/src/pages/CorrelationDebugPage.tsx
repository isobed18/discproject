import { useEffect, useMemo, useState } from 'react'
import { fetchJson } from '../api'
import type { AuditEvent } from '../types'
import { JsonBlock } from '../components/JsonBlock'

type Mode = 'correlation' | 'resource'

function parseHashQuery(): Record<string, string> {
  const h = window.location.hash || ''
  const idx = h.indexOf('?')
  if (idx === -1) return {}
  const qs = h.slice(idx + 1)
  const usp = new URLSearchParams(qs)
  const out: Record<string, string> = {}
  usp.forEach((v, k) => (out[k] = v))
  return out
}

export function CorrelationDebugPage() {
  const [mode, setMode] = useState<Mode>('correlation')
  const [value, setValue] = useState('')
  const [items, setItems] = useState<AuditEvent[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    // Prefill from hash, if present (e.g. #/debug?cid=...)
    const q = parseHashQuery()
    if (q.cid) {
      setMode('correlation')
      setValue(q.cid)
    }
    if (q.jti) {
      setMode('resource')
      setValue(q.jti)
    }
  }, [])

  const endpoint = useMemo(() => {
    if (!value.trim()) return null
    const v = encodeURIComponent(value.trim())
    return mode === 'correlation' ? `/trace/correlation/${v}` : `/trace/resource/${v}`
  }, [mode, value])

  const load = async () => {
    if (!endpoint) return
    setLoading(true)
    setError(null)
    try {
      const { data } = await fetchJson<{ items: AuditEvent[] }>(endpoint)
      setItems(data.items ?? [])
    } catch (e: any) {
      setError(e?.message ?? 'Failed to load trace')
      setItems([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    // Auto load if value was prefilled
    if (endpoint) load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [endpoint])

  return (
    <div className="page">
      <div className="pageHeader">
        <div>
          <h2>Correlation-ID debug</h2>
          <p className="muted">Enter a correlation-id (or JTI) and inspect the full event chain/timeline.</p>
        </div>
      </div>

      {error && <div className="alert">{error}</div>}

      <div className="card">
        <div className="rowWrap">
          <div className="field" style={{ minWidth: 220 }}>
            <label>Mode</label>
            <select value={mode} onChange={(e) => setMode(e.target.value as Mode)}>
              <option value="correlation">Correlation ID</option>
              <option value="resource">Resource / JTI</option>
            </select>
          </div>
          <div className="field" style={{ flex: 1 }}>
            <label>{mode === 'correlation' ? 'Correlation ID' : 'JTI'}</label>
            <input value={value} onChange={(e) => setValue(e.target.value)} placeholder={mode === 'correlation' ? 'e.g. 7a9b...' : 'e.g. jti uuid...'} />
          </div>
          <div className="field" style={{ minWidth: 160, alignSelf: 'end' }}>
            <button className="btn" onClick={load} disabled={!endpoint || loading}>
              {loading ? 'Loading…' : 'Trace'}
            </button>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="cardHeader">
          <h3>Timeline</h3>
          <p className="muted">Events are ordered by timestamp.</p>
        </div>

        {items.length === 0 ? (
          <div className="muted">No events for this {mode === 'correlation' ? 'correlation-id' : 'resource'}.</div>
        ) : (
          <div className="timeline">
            {items.map((e, idx) => (
              <div key={e.event_id} className="timelineItem">
                <div className="timelineDot" />
                <div className="timelineBody">
                  <div className="timelineHeader">
                    <div className="title">
                      <span className="pill">{e.event_type ?? 'event'}</span>
                      <span className="mono small">{e.timestamp ?? e.ingested_at ?? ''}</span>
                    </div>
                    <div className="right muted">
                      #{idx + 1} · {e.source}
                      {e.signature_valid === true && <span className="pill ok">sig</span>}
                      {e.signature_valid === false && <span className="pill warn">bad-sig</span>}
                      {e.parse_error && <span className="pill warn">parse</span>}
                    </div>
                  </div>

                  <div className="grid grid2" style={{ marginTop: 12 }}>
                    <div className="kv">
                      <div className="row">
                        <div className="key">Actor</div>
                        <div className="val">{e.actor ?? '—'}</div>
                      </div>
                      <div className="row">
                        <div className="key">Action</div>
                        <div className="val">{e.action ?? '—'}</div>
                      </div>
                      <div className="row">
                        <div className="key">Resource</div>
                        <div className="val mono small">{e.resource ?? '—'}</div>
                      </div>
                      <div className="row">
                        <div className="key">Correlation</div>
                        <div className="val mono small">{e.correlation_id ?? '—'}</div>
                      </div>
                    </div>

                    <div className="kv">
                      <div className="row">
                        <div className="key">Gateway</div>
                        <div className="val mono small">{e.gateway?.gateway_id ?? '—'}</div>
                      </div>
                      <div className="row">
                        <div className="key">Client IP</div>
                        <div className="val mono small">{e.request?.client_ip ?? e.gateway?.forwarded_for ?? '—'}</div>
                      </div>
                      <div className="row">
                        <div className="key">Route</div>
                        <div className="val mono small">{e.request?.method ?? ''} {e.request?.path ?? ''}</div>
                      </div>
                      <div className="row">
                        <div className="key">User-Agent</div>
                        <div className="val mono small">{e.gateway?.user_agent ?? e.request?.user_agent ?? '—'}</div>
                      </div>
                    </div>
                  </div>

                  <div style={{ marginTop: 12 }}>
                    <h4 className="h4">Details</h4>
                    <JsonBlock value={e.details} maxHeight={220} />
                  </div>

                  {(e.raw || e.parse_error) && (
                    <div style={{ marginTop: 12 }}>
                      <h4 className="h4">Raw</h4>
                      <JsonBlock value={{ raw: e.raw, parse_error: e.parse_error }} maxHeight={220} />
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
