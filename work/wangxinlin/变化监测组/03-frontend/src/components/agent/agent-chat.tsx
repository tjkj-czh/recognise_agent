import { useState, useRef, useEffect } from 'react'
import {
  Bot,
  X,
  Send,
  User,
  Sparkles,
  Loader2,
} from 'lucide-react'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
}

interface AgentChatProps {
  open: boolean
  onClose: () => void
}

export default function AgentChat({ open, onClose }: AgentChatProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content: '你好！我是浙江省空间变化智能监测平台的 AI 助手。我可以帮你：\n\n• 查询土地供应信息\n• 分析变化监测结果\n• 生成监测报告\n• 解答政策问题\n\n请问有什么可以帮你的？',
      timestamp: new Date(),
    },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

  const handleSend = async () => {
    if (!input.trim() || loading) return

    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim(),
      timestamp: new Date(),
    }

    setMessages((prev) => [...prev, userMsg])
    setInput('')
    setLoading(true)

    // Simulate AI response (placeholder for real LLM integration)
    setTimeout(() => {
      const responses = [
        '我已收到你的问题。目前正在分析相关数据，请稍候...',
        '根据当前数据库中的土地供应信息，我可以为你筛选出符合条件的地块。',
        '这是一个很好的问题。你可以尝试在左侧卡片列表中查看详细信息，或直接告诉我具体的地块名称。',
        '我已记录下你的需求。后续 Skill 运行时接入后，我将能够直接调用变化检测和报告生成能力。',
      ]
      const assistantMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: responses[Math.floor(Math.random() * responses.length)],
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, assistantMsg])
      setLoading(false)
    }, 1500)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  if (!open) return null

  return (
    <div className="fixed bottom-6 right-6 z-[9999] flex flex-col w-[420px] h-[560px] bg-white rounded-2xl shadow-2xl border border-slate-200 overflow-hidden animate-fade-in"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-gradient-to-r from-blue-600 to-cyan-500 text-white shrink-0"
      >
        <div className="flex items-center gap-2"
        >
          <div className="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center"
          >
            <Sparkles className="w-4 h-4" />
          </div>
          <div>
            <h3 className="font-semibold text-sm"
            >智能监测助手</h3>
            <p className="text-xs text-white/80"
            >AI 驱动 · 实时响应</p>
          </div>
        </div>
        <button
          onClick={onClose}
          className="p-1.5 hover:bg-white/20 rounded-lg transition-colors"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-4 bg-slate-50"
      >
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex gap-2 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}
          >
            <div
              className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 ${
                msg.role === 'assistant'
                  ? 'bg-blue-100 text-blue-600'
                  : 'bg-slate-200 text-slate-600'
              }`}
            >
              {msg.role === 'assistant' ? (
                <Bot className="w-4 h-4" />
              ) : (
                <User className="w-4 h-4" />
              )}
            </div>
            <div
              className={`max-w-[80%] rounded-xl px-3 py-2 text-sm leading-relaxed ${
                msg.role === 'assistant'
                  ? 'bg-white border border-slate-200 text-slate-700 shadow-sm'
                  : 'bg-blue-600 text-white'
              }`}
            >
              {msg.content.split('\n').map((line, i) => (
                <p key={i} className={i > 0 ? 'mt-1' : ''}>
                  {line}
                </p>
              ))}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex gap-2"
          >
            <div className="w-7 h-7 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center shrink-0"
            >
              <Bot className="w-4 h-4" />
            </div>
            <div className="bg-white border border-slate-200 rounded-xl px-3 py-2 shadow-sm"
            >
              <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />
            </div>
          </div>
        )}
      </div>

      {/* Input */}
      <div className="px-3 py-3 bg-white border-t border-slate-200 shrink-0"
      >
        <div className="flex items-end gap-2"
        >
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="输入问题，按 Enter 发送..."
            className="flex-1 resize-none max-h-24 px-3 py-2 bg-slate-100 border-0 rounded-xl text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/50"
            rows={1}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || loading}
            className="p-2.5 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-300 text-white rounded-xl transition-colors"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  )
}
