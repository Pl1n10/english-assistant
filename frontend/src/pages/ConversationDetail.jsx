import { useState, useEffect, useRef } from 'react'
import { useParams, Link } from 'react-router-dom'
import { conversations } from '../api'
import { format } from 'date-fns'
import { it } from 'date-fns/locale'

function ConversationDetail() {
  const { id } = useParams()
  const [conversation, setConversation] = useState(null)
  const [messages, setMessages] = useState([])
  const [newMessage, setNewMessage] = useState('')
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const messagesEndRef = useRef(null)
  const wsRef = useRef(null)

  // Utility
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  // Caricamento iniziale + WebSocket
  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true)
        await Promise.all([loadConversation(), loadMessages()])
      } finally {
        setLoading(false)
      }
    }
    load()

    // Costruisci URL WS in modo "proxy-friendly"
    // Se stai dietro a Ingress + Nginx nel pod frontend, usa stesso host
    const wsProto = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const wsUrl = `${wsProto}://${window.location.host}/ws/conversations/${id}`

    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => {
      // con FastAPI WS "vanilla" non serve join: l'URL è già room-based
      // console.log('WebSocket connesso')
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        // Atteso qualcosa tipo: { message: { id, role, content, created_at, ... } }
        if (data?.message) {
          setMessages((prev) => [...prev, data.message])
          scrollToBottom()
        }
      } catch {
        // fallback: se il backend inviasse testo semplice
        // setMessages((prev) => [...prev, { id: Date.now(), role: 'system', content: event.data, created_at: new Date().toISOString() }])
      }
    }

    ws.onerror = (e) => {
      // console.warn('WebSocket errore', e)
    }

    ws.onclose = () => {
      // console.log('WebSocket chiuso')
    }

    return () => {
      wsRef.current?.close()
    }
  }, [id])

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // API calls
  const loadConversation = async () => {
    const res = await conversations.getById(id)
    setConversation(res.data)
  }

  const loadMessages = async () => {
    const res = await conversations.getMessages(id)
    setMessages(res.data)
  }

  const handleSendMessage = async (e) => {
    e.preventDefault()
    if (!newMessage.trim() || sending) return
    setSending(true)
    try {
      await conversations.sendMessage(id, newMessage)
      setNewMessage('')
      // Il messaggio del teacher arriverà anche via WS (se il backend fa broadcast)
    } catch (err) {
      // eslint-disable-next-line no-alert
      alert("Errore nell'invio del messaggio")
      // console.error(err)
    } finally {
      setSending(false)
    }
  }

  // Presentazione
  const getRoleColor = (role) => {
    const colors = {
      user: 'bg-gray-100',
      assistant: 'bg-blue-50',
      teacher: 'bg-green-50',
      system: 'bg-yellow-50',
    }
    return colors[role] || 'bg-gray-100'
  }

  const getRoleLabel = (role) => {
    const labels = {
      user: 'Studente',
      assistant: 'Bot',
      teacher: 'Docente',
      system: 'Sistema',
    }
    return labels[role] || role
  }

  const prettyDate = (iso) => {
    try {
      return format(new Date(iso), "dd MMM yyyy HH:mm", { locale: it })
    } catch {
      return iso
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-lg text-gray-600">Caricamento...</div>
      </div>
    )
  }

  return (
    <div>
      {/* Header */}
      <div className="mb-6">
        <Link
          to="/dashboard"
          className="text-blue-600 hover:text-blue-700 text-sm font-medium mb-2 inline-block"
        >
          ← Torna alle conversazioni
        </Link>
        <h2 className="text-2xl font-bold text-gray-900">
          {conversation?.student_name || conversation?.student_phone}
        </h2>
        <p className="text-gray-600 mt-1">{conversation?.student_phone}</p>
      </div>

      <div className="bg-white rounded-lg shadow flex flex-col h-[calc(100vh-300px)]">
        {/* Messaggi */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.role === 'user' ? 'justify-start' : 'justify-end'}`}
            >
              <div className={`max-w-[75%] rounded-lg p-3 shadow ${getRoleColor(message.role)}`}>
                <div className="text-xs text-gray-500 mb-1">
                  {getRoleLabel(message.role)} • {prettyDate(message.created_at)}
                </div>
                <div className="whitespace-pre-wrap text-gray-900">{message.content}</div>
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        {/* Composer */}
        <form onSubmit={handleSendMessage} className="p-4 border-t flex gap-2">
          <input
            type="text"
            className="flex-1 border rounded-lg px-3 py-2 focus:outline-none focus:ring"
            placeholder="Scrivi un messaggio…"
            value={newMessage}
            onChange={(e) => setNewMessage(e.target.value)}
          />
          <button
            type="submit"
            disabled={sending || !newMessage.trim()}
            className="bg-blue-600 text-white px-4 py-2 rounded-lg disabled:opacity-50"
          >
            {sending ? 'Invio…' : 'Invia'}
          </button>
        </form>
      </div>
    </div>
  )
}

export default ConversationDetail
