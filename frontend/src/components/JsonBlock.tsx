import { useMemo, useState } from 'react'

export function JsonBlock({ value, maxHeight = 240 }: { value: any; maxHeight?: number }) {
  const [expanded, setExpanded] = useState(false)

  const text = useMemo(() => {
    try {
      return JSON.stringify(value, null, 2)
    } catch {
      return String(value)
    }
  }, [value])

  const shown = expanded ? text : text.length > 400 ? `${text.slice(0, 400)}\n...` : text

  return (
    <div className="jsonBlock">
      <pre style={{ maxHeight, overflow: 'auto' }}>{shown}</pre>
      {text.length > 400 && (
        <button className="linkBtn" onClick={() => setExpanded((v) => !v)}>
          {expanded ? 'Show less' : 'Show more'}
        </button>
      )}
    </div>
  )
}
