import { useState, useEffect } from 'react'
import { api } from '../store/authStore'
import { TrendingUp, TrendingDown, RefreshCw, Search } from 'lucide-react'
import { AreaChart, Area, ResponsiveContainer, Tooltip } from 'recharts'
import clsx from 'clsx'

const WATCHLIST = ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'TSLA', 'META', 'SPY', 'QQQ', 'GLD', 'TLT', 'BTC-USD']

// Spark data generator (replaced by real bars in Phase 2)
const spark = () => Array.from({ length: 20 }, (_, i) => ({
  v: 100 + Math.sin(i * 0.5) * 8 + Math.random() * 5
}))

const MOCK_QUOTES = WATCHLIST.map(sym => ({
  symbol: sym,
  price: 80 + Math.random() * 800,
  change_pct: (Math.random() - 0.45) * 6,
  volume: Math.floor(Math.random() * 50_000_000),
  spark: spark(),
}))

function QuoteRow({ q }) {
  const up = q.change_pct >= 0
  return (
    <div className="flex items-center gap-4 px-5 py-3.5 border-b border-obsidian-700/50 hover:bg-obsidian-800/50 transition-colors">
      <div className="w-20">
        <p className="font-mono text-sm text-gold-400 font-medium">{q.symbol}</p>
      </div>
      <div className="flex-1">
        <ResponsiveContainer width="100%" height={36}>
          <AreaChart data={q.spark}>
            <defs>
              <linearGradient id={`g-${q.symbol}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={up ? '#22c55e' : '#ef4444'} stopOpacity={0.2} />
                <stop offset="95%" stopColor={up ? '#22c55e' : '#ef4444'} stopOpacity={0} />
              </linearGradient>
            </defs>
            <Area type="monotone" dataKey="v" stroke={up ? '#22c55e' : '#ef4444'}
              strokeWidth={1.5} fill={`url(#g-${q.symbol})`} dot={false} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
      <div className="w-28 text-right">
        <p className="font-mono text-sm text-white">${q.price.toFixed(2)}</p>
      </div>
      <div className="w-24 text-right">
        <span className={clsx('text-xs font-medium flex items-center justify-end gap-1', up ? 'positive' : 'negative')}>
          {up ? <TrendingUp size={11} /> : <TrendingDown size={11} />}
          {up ? '+' : ''}{q.change_pct.toFixed(2)}%
        </span>
      </div>
      <div className="w-28 text-right text-xs text-obsidian-400">
        {(q.volume / 1_000_000).toFixed(1)}M vol
      </div>
    </div>
  )
}

export default function Market() {
  const [quotes, setQuotes] = useState(MOCK_QUOTES)
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(false)

  const refresh = async () => {
    setLoading(true)
    try {
      const { data } = await api.get(`/market/quotes?symbols=${WATCHLIST.join(',')}`)
      if (data.length > 0) setQuotes(data)
    } catch { /* use mock */ }
    finally { setLoading(false) }
  }

  const filtered = quotes.filter(q =>
    q.symbol.toLowerCase().includes(search.toLowerCase())
  )

  const gainers = [...quotes].sort((a, b) => b.change_pct - a.change_pct).slice(0, 3)
  const losers  = [...quotes].sort((a, b) => a.change_pct - b.change_pct).slice(0, 3)

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="font-display text-3xl text-white">Market</h1>
          <p className="text-obsidian-400 text-sm mt-1">Real-time quotes &amp; watchlist</p>
        </div>
        <button className="btn-ghost flex items-center gap-2" onClick={refresh}>
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      {/* Movers */}
      <div className="grid grid-cols-2 gap-4 mb-6">
        <div className="card p-5">
          <p className="stat-label mb-3">Top Gainers</p>
          <div className="space-y-2">
            {gainers.map(q => (
              <div key={q.symbol} className="flex items-center justify-between">
                <span className="font-mono text-sm text-white">{q.symbol}</span>
                <span className="text-xs positive font-medium">+{q.change_pct.toFixed(2)}%</span>
              </div>
            ))}
          </div>
        </div>
        <div className="card p-5">
          <p className="stat-label mb-3">Top Losers</p>
          <div className="space-y-2">
            {losers.map(q => (
              <div key={q.symbol} className="flex items-center justify-between">
                <span className="font-mono text-sm text-white">{q.symbol}</span>
                <span className="text-xs negative font-medium">{q.change_pct.toFixed(2)}%</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Quotes table */}
      <div className="card">
        <div className="flex items-center gap-3 px-5 py-4 border-b border-obsidian-700">
          <Search size={14} className="text-obsidian-400" />
          <input
            className="bg-transparent text-sm text-white placeholder-obsidian-500 outline-none flex-1"
            placeholder="Search symbols..."
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
        <div className="flex items-center gap-4 px-5 py-2 border-b border-obsidian-700">
          <p className="w-20 stat-label">Symbol</p>
          <p className="flex-1 stat-label pl-2">7d chart</p>
          <p className="w-28 text-right stat-label">Price</p>
          <p className="w-24 text-right stat-label">Change</p>
          <p className="w-28 text-right stat-label">Volume</p>
        </div>
        {filtered.map(q => <QuoteRow key={q.symbol} q={q} />)}
      </div>
    </div>
  )
}
