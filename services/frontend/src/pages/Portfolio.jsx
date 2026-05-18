import { useState } from 'react'
import { PlusCircle, BarChart2, TrendingUp, AlertTriangle } from 'lucide-react'

export default function Portfolio() {
  const [showNew, setShowNew] = useState(false)
  const [name, setName] = useState('')

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="font-display text-3xl text-white">My Portfolios</h1>
          <p className="text-obsidian-400 text-sm mt-1">Manage your investment accounts</p>
        </div>
        <button className="btn-primary flex items-center gap-2" onClick={() => setShowNew(!showNew)}>
          <PlusCircle size={14} />
          New Portfolio
        </button>
      </div>

      {showNew && (
        <div className="card p-5 mb-6">
          <h3 className="text-white font-medium mb-4">Create Portfolio</h3>
          <div className="flex gap-3">
            <input className="input flex-1" placeholder="Portfolio name" value={name} onChange={e => setName(e.target.value)} />
            <button className="btn-primary">Create</button>
            <button className="btn-ghost" onClick={() => setShowNew(false)}>Cancel</button>
          </div>
        </div>
      )}

      {/* Empty state */}
      <div className="card p-16 flex flex-col items-center justify-center text-center">
        <div className="w-16 h-16 rounded-2xl bg-obsidian-800 border border-obsidian-700 flex items-center justify-center mb-4">
          <BarChart2 size={24} className="text-gold-400" />
        </div>
        <h3 className="font-display text-xl text-white mb-2">No portfolios yet</h3>
        <p className="text-obsidian-400 text-sm mb-6 max-w-xs">Create your first portfolio to start tracking your investments and getting AI-powered advice.</p>
        <button className="btn-primary" onClick={() => setShowNew(true)}>Create Portfolio</button>
      </div>
    </div>
  )
}
