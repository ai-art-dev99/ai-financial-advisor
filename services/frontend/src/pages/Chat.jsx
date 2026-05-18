import { useState, useRef, useEffect } from 'react'
import { useAuthStore } from '../store/authStore'
import { Bot, User, Send, Trash2, Loader2, Zap } from 'lucide-react'
import clsx from 'clsx'

const API = import.meta.env.VITE_API_URL || '/api/v1'

function renderMarkdown(text) {
    return text
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/`(.*?)`/g, '<code class="bg-obsidian-700 px-1 rounded text-gold-300 text-xs">$1</code>')
        .replace(/^### (.*$)/gm, '<h3 class="text-white font-medium text-sm mt-3 mb-1">$1</h3>')
        .replace(/^## (.*$)/gm, '<h2 class="text-white font-medium mt-4 mb-1">$1</h2>')
        .replace(/^- (.*$)/gm, '<li class="ml-4 list-disc text-obsidian-300">$1</li>')
        .replace(/\n/g, '<br/>')
}

function Message({ msg }) {
    const isUser = msg.role === 'user'
    return (
        <div className={clsx('flex gap-3 mb-4', isUser && 'flex-row-reverse')}>
            {/* Avatar */}
            <div className={clsx(
                'w-8 h-8 rounded-full flex items-center justify-center shrink-0 mt-0.5',
                isUser ? 'bg-gold-500' : 'bg-obsidian-700 border border-obsidian-600'
            )}>
                {isUser
                    ? <User size={14} className="text-obsidian-950" />
                    : <Bot size={14} className="text-gold-400" />}
            </div>

            {/* Bubble */}
            <div className={clsx(
                'max-w-[80%] px-4 py-3 rounded-2xl text-sm leading-relaxed',
                isUser
                    ? 'bg-gold-500/10 border border-gold-500/20 text-white rounded-tr-sm'
                    : 'bg-obsidian-800 border border-obsidian-700 text-obsidian-200 rounded-tl-sm'
            )}>
                {isUser
                    ? <p>{msg.content}</p>
                    : <div dangerouslySetInnerHTML={{ __html: renderMarkdown(msg.content) }} />
                }
            </div>
        </div>
    )
}

function TypingIndicator() {
    return (
        <div className="flex gap-3 mb-4">
            <div className="w-8 h-8 rounded-full bg-obsidian-700 border border-obsidian-600 flex items-center justify-center shrink-0">
                <Bot size={14} className="text-gold-400" />
            </div>
            <div className="bg-obsidian-800 border border-obsidian-700 px-4 py-3 rounded-2xl rounded-tl-sm">
                <div className="flex gap-1 items-center h-4">
                    {[0, 1, 2].map(i => (
                        <div key={i}
                            className="w-1.5 h-1.5 rounded-full bg-obsidian-400 animate-bounce"
                            style={{ animationDelay: `${i * 0.15}s` }} />
                    ))}
                </div>
            </div>
        </div>
    )
}

const STARTER_QUESTIONS = [
    "What should I know about rebalancing my portfolio?",
    "Explain the risk vs return tradeoff in simple terms.",
    "Should I invest in ETFs or individual stocks?",
    "How does dollar-cost averaging work?",
]

export default function Chat() {
    const [messages, setMessages] = useState([])
    const [input, setInput] = useState('')
    const [streaming, setStreaming] = useState(false)
    const [sessionId, setSessionId] = useState(null)
    const bottomRef = useRef(null)
    const inputRef = useRef(null)
    const token = localStorage.getItem('access_token')

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [messages])

    const sendMessage = async (text) => {
        const userMsg = text || input.trim()
        if (!userMsg || streaming) return
        setInput('')

        // Optimistically add user message
        setMessages(prev => [...prev, { role: 'user', content: userMsg }])
        setStreaming(true)

        // Placeholder for assistant
        let assistantContent = ''
        setMessages(prev => [...prev, { role: 'assistant', content: '', streaming: true }])

        try {
            const resp = await fetch(`${API}/ai/chat/message`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`,
                },
                body: JSON.stringify({
                    message: userMsg,
                    session_id: sessionId,
                    include_portfolio: true,
                }),
            })

            if (!resp.ok) throw new Error(`HTTP ${resp.status}`)

            const reader = resp.body.getReader()
            const decoder = new TextDecoder()

            while (true) {
                const { done, value } = await reader.read()
                if (done) break

                const lines = decoder.decode(value).split('\n')
                for (const line of lines) {
                    if (!line.startsWith('data: ')) continue
                    try {
                        const event = JSON.parse(line.slice(6))
                        if (event.type === 'session') {
                            setSessionId(event.session_id)
                        } else if (event.type === 'token') {
                            assistantContent += event.content
                            setMessages(prev => prev.map((m, i) =>
                                i === prev.length - 1
                                    ? { ...m, content: assistantContent, streaming: true }
                                    : m
                            ))
                        } else if (event.type === 'done') {
                            setMessages(prev => prev.map((m, i) =>
                                i === prev.length - 1
                                    ? { ...m, streaming: false }
                                    : m
                            ))
                        }
                    } catch { /* skip malformed events */ }
                }
            }
        } catch (e) {
            setMessages(prev => prev.map((m, i) =>
                i === prev.length - 1
                    ? { role: 'assistant', content: `Sorry, I encountered an error: ${e.message}`, streaming: false }
                    : m
            ))
        } finally {
            setStreaming(false)
            inputRef.current?.focus()
        }
    }

    const clearChat = async () => {
        if (sessionId) {
            await fetch(`${API}/ai/chat/session/${sessionId}`, {
                method: 'DELETE',
                headers: { 'Authorization': `Bearer ${token}` },
            }).catch(() => { })
        }
        setMessages([])
        setSessionId(null)
    }

    return (
        <div className="flex flex-col h-screen">
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-obsidian-700 shrink-0">
                <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-xl bg-gold-500/10 border border-gold-500/30 flex items-center justify-center">
                        <Bot size={18} className="text-gold-400" />
                    </div>
                    <div>
                        <h1 className="text-white font-medium">Argo AI Advisor</h1>
                        <div className="flex items-center gap-1.5">
                            <div className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                            <span className="text-xs text-obsidian-400">Powered by Claude · RAG enabled</span>
                        </div>
                    </div>
                </div>
                {messages.length > 0 && (
                    <button onClick={clearChat} className="btn-ghost flex items-center gap-1.5 text-xs">
                        <Trash2 size={13} /> Clear
                    </button>
                )}
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto px-6 py-4">
                {messages.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-full text-center">
                        <div className="w-16 h-16 rounded-2xl bg-gold-500/10 border border-gold-500/20 flex items-center justify-center mb-4">
                            <Zap size={28} className="text-gold-400" />
                        </div>
                        <h2 className="font-display text-xl text-white mb-2">Ask me anything</h2>
                        <p className="text-obsidian-400 text-sm mb-8 max-w-xs">
                            I have access to your portfolio, risk profile, and live financial knowledge.
                        </p>
                        <div className="grid grid-cols-1 gap-2 w-full max-w-md">
                            {STARTER_QUESTIONS.map(q => (
                                <button key={q} onClick={() => sendMessage(q)}
                                    className="text-left px-4 py-3 rounded-xl bg-obsidian-800 border border-obsidian-700
                             text-sm text-obsidian-300 hover:text-white hover:border-obsidian-600 transition-all">
                                    {q}
                                </button>
                            ))}
                        </div>
                    </div>
                ) : (
                    <>
                        {messages.map((msg, i) => (
                            <Message key={i} msg={msg} />
                        ))}
                        {streaming && messages.at(-1)?.content === '' && <TypingIndicator />}
                        <div ref={bottomRef} />
                    </>
                )}
            </div>

            {/* Input */}
            <div className="px-6 pb-6 pt-3 border-t border-obsidian-700 shrink-0">
                <div className="flex items-end gap-3 bg-obsidian-800 border border-obsidian-600 rounded-2xl px-4 py-3
                        focus-within:border-gold-500 transition-colors">
                    <textarea
                        ref={inputRef}
                        className="flex-1 bg-transparent text-white text-sm placeholder-obsidian-500 outline-none
                       resize-none max-h-32 leading-relaxed"
                        placeholder="Ask about your portfolio, market trends, or investment strategy..."
                        value={input}
                        onChange={e => setInput(e.target.value)}
                        onKeyDown={e => {
                            if (e.key === 'Enter' && !e.shiftKey) {
                                e.preventDefault()
                                sendMessage()
                            }
                        }}
                        rows={1}
                    />
                    <button
                        onClick={() => sendMessage()}
                        disabled={!input.trim() || streaming}
                        className={clsx(
                            'w-8 h-8 rounded-xl flex items-center justify-center transition-all shrink-0',
                            input.trim() && !streaming
                                ? 'bg-gold-500 text-obsidian-950 hover:bg-gold-400'
                                : 'bg-obsidian-700 text-obsidian-500 cursor-not-allowed'
                        )}
                    >
                        {streaming
                            ? <Loader2 size={14} className="animate-spin" />
                            : <Send size={14} />}
                    </button>
                </div>
                <p className="text-center text-xs text-obsidian-600 mt-2">
                    Argo is not a licensed financial advisor. Always consult a professional for major decisions.
                </p>
            </div>
        </div>
    )
}