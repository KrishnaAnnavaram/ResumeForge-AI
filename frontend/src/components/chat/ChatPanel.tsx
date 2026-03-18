import { useState, useRef, useEffect } from 'react'
import { Send, MessageSquare } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { motion, AnimatePresence } from 'framer-motion'
import { chatApi } from '../../api/chat'
import { useSessionStore } from '../../store/sessionStore'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
}

export function ChatPanel() {
  const { sessionId } = useSessionStore()
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [chatSessionId, setChatSessionId] = useState<string | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const initSession = async () => {
    if (chatSessionId) return chatSessionId
    const res = await chatApi.createSession('generation', sessionId || undefined)
    setChatSessionId(res.data.id)
    return res.data.id
  }

  const send = async () => {
    if (!input.trim() || loading) return
    const userContent = input
    setInput('')
    setMessages(prev => [...prev, { id: Date.now().toString(), role: 'user', content: userContent }])
    setLoading(true)

    try {
      const sid = await initSession()
      const res = await chatApi.sendMessage(sid, userContent)
      setMessages(prev => [...prev, {
        id: res.data.id,
        role: 'assistant',
        content: res.data.content,
      }])
    } catch {
      setMessages(prev => [...prev, {
        id: Date.now().toString(),
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
      }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col h-full bg-bg-surface border-t border-bg-border">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.length === 0 && (
          <div className="text-center text-text-tertiary text-sm py-8">
            <MessageSquare size={24} className="mx-auto mb-2 opacity-30" />
            <p>Ask anything about your application</p>
          </div>
        )}
        <AnimatePresence>
          {messages.map((msg) => (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div className={`
                max-w-[85%] rounded-lg px-3 py-2 text-sm
                ${msg.role === 'user'
                  ? 'bg-accent-primary/20 text-text-primary border border-accent-primary/30'
                  : 'bg-bg-elevated text-text-primary border border-bg-border'
                }
              `}>
                {msg.role === 'assistant' ? (
                  <div className="markdown-content text-sm [&_p]:mb-1 [&_p]:leading-relaxed">
                    <ReactMarkdown>{msg.content}</ReactMarkdown>
                  </div>
                ) : (
                  <span>{msg.content}</span>
                )}
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
        {loading && (
          <div className="flex gap-1 pl-2">
            {[0, 1, 2].map(i => (
              <div
                key={i}
                className="w-2 h-2 rounded-full bg-accent-primary"
                style={{ animation: `amberPulse 1.2s ease-in-out ${i * 0.2}s infinite` }}
              />
            ))}
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="p-3 border-t border-bg-border">
        <div className="flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), send())}
            placeholder="Type feedback or ask a question..."
            className="flex-1 bg-bg-elevated border border-bg-border rounded-md px-3 py-2 text-sm text-text-primary placeholder:text-text-tertiary focus:outline-none focus:border-accent-primary"
          />
          <button
            onClick={send}
            disabled={!input.trim() || loading}
            className="px-3 py-2 bg-accent-primary rounded-md text-bg-base disabled:opacity-40 transition-opacity"
          >
            <Send size={14} />
          </button>
        </div>
      </div>
    </div>
  )
}
