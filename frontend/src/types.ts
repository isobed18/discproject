export interface AuditEvent {
  event_id: string
  ingested_at?: string
  source?: string
  signature_valid?: boolean | null
  parse_error?: string | null
  raw?: string | null

  timestamp?: string | null
  event_type?: string | null
  actor?: string | null
  action?: string | null
  resource?: string | null
  correlation_id?: string | null
  service?: string | null

  gateway?: {
    gateway_id?: string | null
    forwarded_for?: string | null
    via?: string | null
    user_agent?: string | null
  } | null

  request?: {
    method?: string | null
    path?: string | null
    query?: string | null
    client_ip?: string | null
    host?: string | null
    user_agent?: string | null
  } | null

  details?: any
}

export interface AuditListResponse {
  items: AuditEvent[]
  total: number
  offset: number
  limit: number
}

export interface AuditSummary {
  buffer: { max: number; current: number }
  counts_by_event_type: Record<string, number>
  counts_by_source: Record<string, number>
  counts_by_action: Record<string, number>
  recent_correlations: Array<{
    correlation_id: string
    first_seen: string
    last_seen: string
    events: number
    last_event_type?: string
    last_action?: string
  }>
  kafka: {
    connected: boolean
    last_ingest_at?: string | null
    last_error?: string | null
    consumed_total: number
    decode_errors_total: number
  }
}
