import { useState } from 'react'
import { api } from '../store/authStore'
import { Shield, ChevronRight, ChevronLeft, Check } from 'lucide-react'
import clsx from 'clsx'

const QUESTIONS = [
  {
    id: 'horizon',
    label: 'Investment Horizon',
    question: 'How long do you plan to keep your investments before needing the money?',
    options: [
      { label: 'Less than 1 year',  value: 6,   score: 1 },
      { label: '1 – 3 years',       value: 24,  score: 3 },
      { label: '3 – 7 years',       value: 60,  score: 6 },
      { label: '7 – 15 years',      value: 120, score: 8 },
      { label: 'More than 15 years', value: 240, score: 10 },
    ],
  },
  {
    id: 'reaction',
    label: 'Market Downturn',
    question: 'Your portfolio drops 20% in one month. What do you do?',
    options: [
      { label: 'Sell everything immediately',        score: 1 },
      { label: 'Sell some to reduce risk',           score: 3 },
      { label: 'Hold and wait for recovery',         score: 6 },
      { label: 'Buy more at the lower price',        score: 9 },
      { label: 'Double down — this is opportunity',  score: 10 },
    ],
  },
  {
    id: 'income',
    label: 'Monthly Income',
    question: 'What is your approximate monthly income?',
    options: [
      { label: 'Under $2,000',        value: 1500,  score: 3 },
      { label: '$2,000 – $5,000',     value: 3500,  score: 5 },
      { label: '$5,000 – $10,000',    value: 7500,  score: 7 },
      { label: '$10,000 – $25,000',   value: 17500, score: 9 },
      { label: 'Over $25,000',        value: 30000, score: 10 },
    ],
  },
  {
    id: 'assets',
    label: 'Investable Assets',
    question: 'How much can you invest without affecting your lifestyle?',
    options: [
      { label: 'Under $10,000',       value: 5000,   score: 2 },
      { label: '$10,000 – $50,000',   value: 30000,  score: 5 },
      { label: '$50,000 – $200,000',  value: 125000, score: 7 },
      { label: '$200,000 – $1M',      value: 600000, score: 9 },
      { label: 'Over $1 million',     value: 1500000, score: 10 },
    ],
  },
  {
    id: 'goal',
    label: 'Primary Goal',
    question: 'What is your primary investment objective?',
    options: [
      { label: 'Capital preservation — protect what I have', score: 1 },
      { label: 'Income — steady dividends and interest',      score: 4 },
      { label: 'Balanced — mix of growth and income',        score: 6 },
      { label: 'Growth — maximize long-term returns',        score: 8 },
      { label: 'Aggressive growth — high risk, high reward', score: 10 },
    ],
  },
]

const RISK_LABELS = {
  conservative: { label: 'Conservative', color: 'text-blue-400', bg: 'bg-blue-400/10 border-blue-400/30', desc: 'Capital preservation with modest growth. Primarily bonds and stable assets.' },
  moderate:     { label: 'Moderate',     color: 'text-gold-400', bg: 'bg-gold-500/10 border-gold-500/30', desc: 'Balanced approach with diversified mix of stocks and bonds.' },
  aggressive:   { label: 'Aggressive',   color: 'text-red-400',  bg: 'bg-red-500/10 border-red-500/30',   desc: 'Maximum growth potential. Heavy equity exposure with higher volatility.' },
}

export default function RiskProfile() {
  const [step, setStep] = useState(0)  // 0 = intro, 1-5 = questions, 6 = result
  const [answers, setAnswers] = useState({})
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  const q = QUESTIONS[step - 1]
  const progress = step === 0 ? 0 : (step / QUESTIONS.length) * 100

  const avgScore = Object.values(answers).reduce((a, b) => a + b.score, 0) /
    Math.max(Object.keys(answers).length, 1)

  const riskScore = Math.round(avgScore) || 5
  const riskCategory = riskScore <= 3 ? 'conservative' : riskScore <= 7 ? 'moderate' : 'aggressive'

  const saveProfile = async () => {
    setSaving(true)
    try {
      await api.post('/auth/users/me/risk-profile', {
        risk_score: riskScore,
        investment_horizon: answers.horizon?.value || 60,
        monthly_income: answers.income?.value || 5000,
        investable_assets: answers.assets?.value || 50000,
        questionnaire_data: answers,
      })
      setSaved(true)
    } catch (e) {
      console.error(e)
    } finally {
      setSaving(false)
    }
  }

  // Intro
  if (step === 0) return (
    <div className="p-8 max-w-2xl mx-auto">
      <div className="text-center mb-8 mt-8">
        <div className="w-16 h-16 rounded-2xl bg-gold-500/10 border border-gold-500/30 flex items-center justify-center mx-auto mb-5">
          <Shield size={28} className="text-gold-400" />
        </div>
        <h1 className="font-display text-3xl text-white mb-3">Risk Assessment</h1>
        <p className="text-obsidian-400 leading-relaxed max-w-sm mx-auto">
          Answer 5 questions and we'll build a personalised risk profile to guide your investment strategy.
        </p>
      </div>
      <div className="card p-6 mb-6 space-y-3">
        {QUESTIONS.map((q, i) => (
          <div key={q.id} className="flex items-center gap-3">
            <div className="w-6 h-6 rounded-full bg-obsidian-700 flex items-center justify-center text-xs text-obsidian-400">
              {i + 1}
            </div>
            <span className="text-sm text-obsidian-300">{q.label}</span>
          </div>
        ))}
      </div>
      <button className="btn-primary w-full flex items-center justify-center gap-2 py-3" onClick={() => setStep(1)}>
        Start Assessment <ChevronRight size={16} />
      </button>
    </div>
  )

  // Result
  if (step > QUESTIONS.length) {
    const info = RISK_LABELS[riskCategory]
    return (
      <div className="p-8 max-w-2xl mx-auto">
        <div className="text-center mb-8 mt-8">
          <h1 className="font-display text-3xl text-white mb-2">Your Risk Profile</h1>
          <p className="text-obsidian-400 text-sm">Based on your answers</p>
        </div>

        <div className={clsx('card border p-8 text-center mb-6', info.bg)}>
          <p className={clsx('font-display text-5xl mb-2', info.color)}>{riskScore}<span className="text-2xl text-obsidian-400">/10</span></p>
          <p className={clsx('text-xl font-medium mb-3', info.color)}>{info.label}</p>
          <p className="text-obsidian-300 text-sm max-w-sm mx-auto">{info.desc}</p>
        </div>

        <div className="card p-5 mb-6">
          <p className="stat-label mb-4">Suggested Allocation</p>
          <div className="space-y-3">
            {riskCategory === 'conservative' && [
              ['Bonds / Fixed Income', 60], ['US Equities', 25], ['International', 10], ['Cash', 5]
            ].map(([l, v]) => (
              <div key={l} className="flex items-center gap-3">
                <span className="text-sm text-obsidian-300 w-40">{l}</span>
                <div className="flex-1 bg-obsidian-700 rounded-full h-1.5">
                  <div className="bg-gold-500 h-1.5 rounded-full" style={{ width: `${v}%` }} />
                </div>
                <span className="text-sm text-white w-8 text-right">{v}%</span>
              </div>
            ))}
            {riskCategory === 'moderate' && [
              ['US Equities', 40], ['Bonds', 30], ['International', 20], ['Alternatives', 10]
            ].map(([l, v]) => (
              <div key={l} className="flex items-center gap-3">
                <span className="text-sm text-obsidian-300 w-40">{l}</span>
                <div className="flex-1 bg-obsidian-700 rounded-full h-1.5">
                  <div className="bg-gold-500 h-1.5 rounded-full" style={{ width: `${v}%` }} />
                </div>
                <span className="text-sm text-white w-8 text-right">{v}%</span>
              </div>
            ))}
            {riskCategory === 'aggressive' && [
              ['US Growth Equities', 50], ['International', 25], ['Alternatives', 15], ['Bonds', 10]
            ].map(([l, v]) => (
              <div key={l} className="flex items-center gap-3">
                <span className="text-sm text-obsidian-300 w-40">{l}</span>
                <div className="flex-1 bg-obsidian-700 rounded-full h-1.5">
                  <div className="bg-gold-500 h-1.5 rounded-full" style={{ width: `${v}%` }} />
                </div>
                <span className="text-sm text-white w-8 text-right">{v}%</span>
              </div>
            ))}
          </div>
        </div>

        {saved ? (
          <div className="flex items-center justify-center gap-2 py-3 text-emerald-500">
            <Check size={16} /> Profile saved successfully
          </div>
        ) : (
          <button className="btn-primary w-full flex items-center justify-center gap-2 py-3" onClick={saveProfile} disabled={saving}>
            {saving ? <div className="w-4 h-4 border-2 border-obsidian-950/30 border-t-obsidian-950 rounded-full animate-spin" /> : <><Check size={14} /> Save Profile</>}
          </button>
        )}

        <button className="btn-ghost w-full mt-2 text-center" onClick={() => { setStep(1); setAnswers({}) }}>
          Retake assessment
        </button>
      </div>
    )
  }

  // Question
  return (
    <div className="p-8 max-w-2xl mx-auto">
      {/* Progress */}
      <div className="mb-8 mt-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs text-obsidian-400">Question {step} of {QUESTIONS.length}</span>
          <span className="text-xs text-gold-400">{Math.round(progress)}%</span>
        </div>
        <div className="w-full bg-obsidian-700 rounded-full h-1">
          <div className="bg-gold-500 h-1 rounded-full transition-all duration-500" style={{ width: `${progress}%` }} />
        </div>
      </div>

      <div className="mb-8">
        <p className="stat-label mb-3">{q.label}</p>
        <h2 className="font-display text-2xl text-white">{q.question}</h2>
      </div>

      <div className="space-y-3 mb-8">
        {q.options.map((opt, i) => {
          const selected = answers[q.id]?.score === opt.score
          return (
            <button
              key={i}
              onClick={() => setAnswers(a => ({ ...a, [q.id]: opt }))}
              className={clsx(
                'w-full text-left px-5 py-4 rounded-xl border transition-all duration-200 text-sm',
                selected
                  ? 'bg-gold-500/10 border-gold-500 text-white'
                  : 'bg-obsidian-800 border-obsidian-600 text-obsidian-300 hover:border-obsidian-500 hover:text-white'
              )}
            >
              <div className="flex items-center justify-between">
                <span>{opt.label}</span>
                {selected && <Check size={14} className="text-gold-400 shrink-0" />}
              </div>
            </button>
          )
        })}
      </div>

      <div className="flex gap-3">
        <button className="btn-ghost flex items-center gap-1" onClick={() => setStep(s => Math.max(0, s - 1))}>
          <ChevronLeft size={14} /> Back
        </button>
        <button
          className="btn-primary flex-1 flex items-center justify-center gap-2"
          disabled={!answers[q.id]}
          onClick={() => setStep(s => s + 1)}
        >
          {step === QUESTIONS.length ? 'See Results' : 'Next Question'}
          <ChevronRight size={14} />
        </button>
      </div>
    </div>
  )
}
