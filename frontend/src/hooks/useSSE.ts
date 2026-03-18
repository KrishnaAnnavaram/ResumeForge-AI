import { useEffect, useRef } from 'react'

interface SSEOptions {
  onMessage: (data: Record<string, unknown>) => void
  onError?: (error: Event) => void
  onOpen?: () => void
}

export function useSSE(url: string | null, options: SSEOptions) {
  const { onMessage, onError, onOpen } = options
  const esRef = useRef<EventSource | null>(null)

  useEffect(() => {
    if (!url) return

    const token = JSON.parse(localStorage.getItem('careeros-auth') || '{}')?.state?.token
    const urlWithAuth = `${url}?token=${encodeURIComponent(token || '')}`

    const es = new EventSource(urlWithAuth)
    esRef.current = es

    es.onopen = () => onOpen?.()
    es.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        onMessage(data)
      } catch {
        // ignore parse errors
      }
    }
    es.onerror = (e) => {
      onError?.(e)
      es.close()
    }

    return () => {
      es.close()
    }
  }, [url])
}
