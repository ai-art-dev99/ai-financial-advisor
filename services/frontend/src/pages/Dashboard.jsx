import { useState, useEffect } from 'react'
import { api } from '../store/authStore'
import {
  AreaChart, Area, PieChart, Pie, Cell,
  ResponsiveContainer, Tooltip, XAxis, YAxis
} from 'recharts'
import {
  TrendingUp, TrendingDown, DollarSign,
  BarChart2, AlertTriangle, RefreshCw, ArrowUpRight
} from 'lucide-react'
import clsx from 'clsx'

// Mock data for Phase 1 (replaced by API in Phase 2)
const MOCK_PERFORMANCE = Array.from({ length: 30 }, (_, i) => ({
  date: new Date(Date.now() - (29 - i) * 86400000).toLocaleDateString('en', { month: 'short', day: 'numeric' }),
  value: 100000 + Math.sin(i * 0.4) * 8000 + i * 400 + Math.random() * 2000,
}))

const MOCK_ALLOCATION = [
  { name: 'US Stocks', value: 45, color: '#c9a84c' },
  { name: 'Intl Stocks', value: 20, color: '#dfc06e' },
  { name: 'Bonds', value: 25, color: '#252535' },
  { name: 'Alternatives', value: 10, color: '#3a3a50' },
]

const MOCK_HOLDINGS = [
  { symbol: 'AAPL', name: 'Apple Inc.', shares: 12, price: 189.30, change: 1.2, value: 2271.60 },
  { symbol: 'MSFT', name: 'Microsoft', shares: 8, price: 415.50, change: 0.8, value: 3324.00 },
  { symbol: 'NVDA', name: 'NVIDIA', shares: 5, price: 875.40, change: 3.1, value: 4377.00 },
  { symbol: 'SPY', name: 'S&P 500 ETF', shares: 20, price: 530.10, change: -0.3, value: 10602.00 },
  { symbol: 'TLT', name: '20Y Treasury', shares: 30, price: 92.80, change: -0.6, value: 2784.00 },
]

function StatCard({ label, value, sub, icon: Icon, positive }) {
  return (
    <div className="card p-5">
      <div className="flex items-start justify-between mb-3">
        <span className="stat-label">{label}</span>
        <div className="w-8 h-8 rounded-lg bg-obsidian-700 flex items-center justify-center">
          <Icon size={14} className="text-gold-400" />
        </div>
      </div>
      <p className="font-display text-2xl text-white">{value}</p>
      {sub && (
        <p className={clsx('text-xs mt-1.5', positive === true && 'positive', positive === false && 'negative', positive === null && 'text-obsidian-400')}>
          {sub}
        </p>
      )}
    </div>
  )
}

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-obsidian-800 border border-obsidian-600 rounded-lg px-3 py-2">
      <p className="text-xs text-obsidian-400">{label}</p>
      <p className="text-sm font-medium text-gold-400">
        ${payload[0].value.toLocaleString('en', { maximumFractionDigits: 0 })}
      </p>
    </div>
  )
}

export default function Dashboard() {
  const [portfolios, setPortfolios] = useState([])

  useEffect(() => {
    api.get('/portfolio/portfolios/').then(r => setPortfolios(r.data)).catch(() => {})
  }, [])

  const totalValue = MOCK_PERFORMANCE.at(-1).value
  const startValue = MOCK_PERFORMANCE[0].value
  const totalReturn = ((totalValue - startValue) / startValue) * 100

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="font-display text-3xl text-white">Portfolio Overview</h1>
          <p className="text-obsidian-400 text-sm mt-1">Updated just now</p>
        </div>
        <button className="btn-ghost flex items-center gap-2">
          <RefreshCw size={14} />
          Refresh
        </button>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <StatCard
          label="Total Value"
          value={`$${totalValue.toLocaleString('en', { maximumFractionDigits: 0 })}`}
          sub="↑ $1,240 today"
          icon={DollarSign}
          positive={true}
        />
        <StatCard
          label="Total Return"
          value={`+${totalReturn.toFixed(2)}%`}
          sub="Since inception"
          icon={TrendingUp}
          positive={true}
        />
        <StatCard
          label="Daily P&L"
          value="+$1,240"
          sub="+1.18% today"
          icon={BarChart2}
          positive={true}
        />
        <StatCard
          label="Risk Score"
          value="7 / 10"
          sub="Aggressive growth"
          icon={AlertTriangle}
          positive={null}
        />
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        {/* Performance chart - 2/3 width */}
        <div className="card p-5 col-span-2">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-white font-medium">Performance</h2>
            <div className="flex gap-1">
              {['1W', '1M', '3M', '1Y'].map(t => (
                <button key={t}
                  className={clsx('px-2 py-1 text-xs rounded-lg transition-colors',
                    t === '1M' ? 'bg-gold-500 text-obsidian-950' : 'text-obsidian-400 hover:text-white')}
                >
                  {t}
                </button>
              ))}
            </div>
          </div>
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={MOCK_PERFORMANCE}>
              <defs>
                <linearGradient id="goldGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#c9a84c" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#c9a84c" stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="date" tick={{ fill: '#444', fontSize: 11 }} tickLine={false} axisLine={false} interval={6} />
              <YAxis tick={{ fill: '#444', fontSize: 11 }} tickLine={false} axisLine={false}
                     tickFormatter={v => `$${(v / 1000).toFixed(0)}k`} />
              <Tooltip content={<CustomTooltip />} />
              <Area type="monotone" dataKey="value" stroke="#c9a84c" strokeWidth={2}
                    fill="url(#goldGrad)" dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Allocation pie - 1/3 width */}
        <div className="card p-5">
          <h2 className="text-white font-medium mb-4">Allocation</h2>
          <ResponsiveContainer width="100%" height={160}>
            <PieChart>
              <Pie data={MOCK_ALLOCATION} cx="50%" cy="50%" innerRadius={45} outerRadius={70}
                   dataKey="value" stroke="none">
                {MOCK_ALLOCATION.map((entry, i) => (
                  <Cell key={i} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip formatter={(v) => `${v}%`}
                       contentStyle={{ background: '#14141c', border: '1px solid #252535', borderRadius: 8 }}
                       labelStyle={{ color: '#888' }} itemStyle={{ color: '#c9a84c' }} />
            </PieChart>
          </ResponsiveContainer>
          <div className="space-y-1.5 mt-2">
            {MOCK_ALLOCATION.map(a => (
              <div key={a.name} className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full" style={{ background: a.color }} />
                  <span className="text-xs text-obsidian-400">{a.name}</span>
                </div>
                <span className="text-xs text-white font-medium">{a.value}%</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Holdings table */}
      <div className="card">
        <div className="flex items-center justify-between px-5 py-4 border-b border-obsidian-700">
          <h2 className="text-white font-medium">Holdings</h2>
          <button className="btn-primary text-xs flex items-center gap-1.5">
            <ArrowUpRight size={12} />
            Add Position
          </button>
        </div>
        <table className="w-full">
          <thead>
            <tr className="border-b border-obsidian-700">
              {['Symbol', 'Name', 'Shares', 'Price', 'Change', 'Value'].map(h => (
                <th key={h} className="px-5 py-3 text-left stat-label">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {MOCK_HOLDINGS.map((h, i) => (
              <tr key={h.symbol}
                className={clsx('border-b border-obsidian-700/50 hover:bg-obsidian-800/50 transition-colors',
                  i === MOCK_HOLDINGS.length - 1 && 'border-b-0')}
              >
                <td className="px-5 py-3.5">
                  <span className="font-mono text-sm text-gold-400 font-medium">{h.symbol}</span>
                </td>
                <td className="px-5 py-3.5 text-sm text-obsidian-300">{h.name}</td>
                <td className="px-5 py-3.5 text-sm text-white">{h.shares}</td>
                <td className="px-5 py-3.5 font-mono text-sm text-white">${h.price.toFixed(2)}</td>
                <td className="px-5 py-3.5">
                  <span className={clsx('text-xs font-medium flex items-center gap-1 w-fit',
                    h.change >= 0 ? 'positive' : 'negative')}>
                    {h.change >= 0 ? <TrendingUp size={11} /> : <TrendingDown size={11} />}
                    {h.change >= 0 ? '+' : ''}{h.change}%
                  </span>
                </td>
                <td className="px-5 py-3.5 font-mono text-sm text-white font-medium">
                  ${h.value.toLocaleString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
