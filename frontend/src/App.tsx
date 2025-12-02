import { useState, useEffect } from 'react'
import './App.css'

interface AuditLog {
  timestamp: string;
  event_type: string;
  actor: string;
  action: string;
  resource: string;
  details: any;
}

function App() {
  const [logs, setLogs] = useState<AuditLog[]>([])
  const [loading, setLoading] = useState(false)
  const [revokeJti, setRevokeJti] = useState("")
  const [revokeStatus, setRevokeStatus] = useState("")

  const fetchLogs = async () => {
    setLoading(true)
    try {
      const res = await fetch('http://localhost:8000/v1/audit-logs')
      const data = await res.json()
      // Sort by timestamp desc
      data.sort((a: AuditLog, b: AuditLog) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
      setLogs(data)
    } catch (err) {
      console.error("Failed to fetch logs", err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchLogs()
    const interval = setInterval(fetchLogs, 5000)
    return () => clearInterval(interval)
  }, [])

  const handleRevoke = async () => {
    if (!revokeJti) return;
    try {
      const res = await fetch('http://localhost:8000/v1/revoke', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ jti: revokeJti, reason: "admin_ui_action" })
      })
      const data = await res.json()
      setRevokeStatus(`Revoked: ${data.status} at ${data.revoked_at}`)
      setRevokeJti("")
      fetchLogs() // Refresh logs if we logged the revocation (we didn't yet in backend, but good practice)
    } catch (err) {
      setRevokeStatus("Failed to revoke")
      console.error(err)
    }
  }

  return (
    <div className="container">
      <h1>DISC Admin Console</h1>

      <div className="card">
        <h2>Revoke Coupon</h2>
        <div className="form-group">
          <input
            type="text"
            placeholder="Enter JTI to revoke"
            value={revokeJti}
            onChange={(e) => setRevokeJti(e.target.value)}
          />
          <button onClick={handleRevoke}>Revoke</button>
        </div>
        {revokeStatus && <p>{revokeStatus}</p>}
      </div>

      <div className="card">
        <div className="header-row">
          <h2>Audit Logs</h2>
          <button onClick={fetchLogs} disabled={loading}>Refresh</button>
        </div>
        <table>
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Event</th>
              <th>Actor</th>
              <th>Action</th>
              <th>Resource (JTI)</th>
              <th>Details</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((log, i) => (
              <tr key={i}>
                <td>{new Date(log.timestamp).toLocaleString()}</td>
                <td>{log.event_type}</td>
                <td>{log.actor}</td>
                <td>{log.action}</td>
                <td>{log.resource}</td>
                <td><pre>{JSON.stringify(log.details, null, 2)}</pre></td>
              </tr>
            ))}
            {logs.length === 0 && <tr><td colSpan={6}>No logs found</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default App
