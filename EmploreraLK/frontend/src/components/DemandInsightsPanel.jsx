import { ArrowDownRight, ArrowUpRight, Lightbulb, TrendingDown, TrendingUp } from 'lucide-react'

const formatPeriod = (start, end) => {
  if (!start || !end) return ''
  const format = (value) => new Date(`${value}T00:00:00`).toLocaleDateString(undefined, {
    month: 'short',
    year: 'numeric',
  })
  return `${format(start)} – ${format(end)}`
}

function SkillSignalList({ title, subtitle, items, direction, emptyMessage }) {
  const isEmerging = direction === 'up'
  const Icon = isEmerging ? TrendingUp : TrendingDown
  const accent = isEmerging
    ? { heading: 'text-emerald-800', icon: 'bg-emerald-100 text-emerald-700', badge: 'bg-emerald-50 text-emerald-800', border: 'border-emerald-100' }
    : { heading: 'text-rose-800', icon: 'bg-rose-100 text-rose-700', badge: 'bg-rose-50 text-rose-800', border: 'border-rose-100' }

  return (
    <section className={`rounded-2xl border ${accent.border} bg-white p-5 shadow-sm`}>
      <div className="mb-4 flex items-start gap-3">
        <span className={`rounded-xl p-2 ${accent.icon}`}><Icon className="h-5 w-5" /></span>
        <div>
          <h3 className={`text-sm font-bold ${accent.heading}`}>{title}</h3>
          <p className="mt-1 text-xs leading-relaxed text-gray-500">{subtitle}</p>
        </div>
      </div>

      {items.length > 0 ? (
        <ul className="space-y-3">
          {items.map((item) => (
            <li key={item.skill} className="rounded-xl border border-gray-100 bg-gray-50/70 p-3.5">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-gray-900">{item.skill}</p>
                  <p className="mt-1 text-[11px] text-gray-500">
                    {item.current_postings} recent postings · {item.current_share_percent}% of sample
                    {item.previous_postings > 0
                      ? ` · ${item.previous_postings} prior (${item.previous_share_percent}%)`
                      : ' · new signal'}
                  </p>
                </div>
                <span className={`shrink-0 rounded-full px-2.5 py-1 text-[11px] font-bold ${accent.badge}`}>
                  {item.change_percent === null
                    ? 'New signal'
                    : `${item.change_percent > 0 ? '+' : ''}${item.change_percent}% YoY`}
                </span>
              </div>
              <p className="mt-2 text-xs leading-relaxed text-gray-600">{item.explanation}</p>
              <div className="mt-3 flex items-start gap-2 border-t border-gray-200/70 pt-2.5 text-xs text-gray-700">
                <Lightbulb className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-500" />
                <span>{item.recommendation}</span>
              </div>
              {item.forecast_index !== null && (
                <div className="mt-3 flex items-center gap-1.5 text-[11px] font-semibold text-gray-500">
                  {isEmerging ? <ArrowUpRight className="h-3.5 w-3.5 text-emerald-600" /> : <ArrowDownRight className="h-3.5 w-3.5 text-rose-600" />}
                  Modelled demand index by forecast horizon: {item.forecast_index} (current baseline 100)
                </div>
              )}
            </li>
          ))}
        </ul>
      ) : (
        <div className="rounded-xl bg-gray-50 px-4 py-5 text-center text-xs leading-relaxed text-gray-500">
          {emptyMessage}
        </div>
      )}
    </section>
  )
}

function DemandInsightsPanel({ insights, isLoading, error, onRetry, onCollect, canCollect }) {
  if (isLoading && !insights) {
    return (
      <div className="flex min-h-60 items-center justify-center gap-3 rounded-2xl border border-gray-200 bg-white text-sm text-gray-500 shadow-sm">
        <span className="h-5 w-5 animate-spin rounded-full border-2 border-brand/20 border-t-brand" />
        Analyzing recent job-market data…
      </div>
    )
  }

  if (error && !insights) {
    return (
      <div className="rounded-2xl border border-rose-200 bg-rose-50 p-5 text-sm text-rose-800" role="alert">
        <p className="font-semibold">Demand insights could not be loaded.</p>
        <p className="mt-1 text-xs">{error}</p>
        <button onClick={onRetry} className="mt-3 rounded-lg bg-white px-3 py-2 text-xs font-semibold text-rose-800 shadow-sm">
          Try again
        </button>
      </div>
    )
  }

  if (!insights) return null

  const { data_window: window, emerging_skills: emerging, declining_skills: declining } = insights
  const hasObservations = window.current_postings > 0 || window.previous_postings > 0

  return (
    <div className="space-y-5">
      <div className="rounded-2xl bg-gradient-to-br from-slate-900 via-blue-950 to-indigo-900 p-5 text-white shadow-sm sm:p-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="max-w-3xl">
            <p className="text-[11px] font-bold uppercase tracking-[0.16em] text-blue-200">Market pulse · {insights.target_year} outlook</p>
            <h3 className="mt-2 text-lg font-bold leading-snug sm:text-xl">{insights.summary}</h3>
            <p className="mt-2 text-xs leading-relaxed text-blue-100/80">
                Signals compare each skill's share of extracted, dated job postings over two 12-month periods. The outlook extends recent movement; it is directional, not a guaranteed hiring forecast.
            </p>
          </div>
          <span className="w-fit shrink-0 rounded-full border border-white/20 bg-white/10 px-3 py-1.5 text-[11px] font-semibold capitalize text-blue-50">
            {insights.confidence} confidence
          </span>
        </div>
        <div className="mt-5 grid grid-cols-1 gap-2 border-t border-white/15 pt-4 text-xs sm:grid-cols-3">
          <div><span className="block text-[10px] uppercase tracking-wide text-blue-200">Recent period</span><span className="mt-1 block font-semibold">{formatPeriod(window.current_start, window.current_end)}</span></div>
          <div><span className="block text-[10px] uppercase tracking-wide text-blue-200">Prior comparison</span><span className="mt-1 block font-semibold">{formatPeriod(window.previous_start, window.previous_end)}</span></div>
          <div className="flex gap-4">
            <span><span className="block text-[10px] uppercase tracking-wide text-blue-200">Recent posts</span><span className="mt-1 block font-semibold">{window.current_postings}</span></span>
            <span><span className="block text-[10px] uppercase tracking-wide text-blue-200">Prior posts</span><span className="mt-1 block font-semibold">{window.previous_postings}</span></span>
          </div>
        </div>
      </div>

      {!hasObservations && (
        <div className="flex flex-col gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-4 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-xs leading-relaxed text-amber-900">
            No dated skill data is available yet. Run the job-market pipeline to collect and analyze current postings before drawing conclusions.
          </p>
          {canCollect ? (
            <button onClick={onCollect} className="shrink-0 rounded-lg bg-amber-700 px-3 py-2 text-xs font-semibold text-white hover:bg-amber-800">
              Collect job data
            </button>
          ) : (
            <span className="shrink-0 text-xs font-semibold text-amber-800">Set a target role to collect relevant jobs.</span>
          )}
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <SkillSignalList
          title="Emerging skills"
          subtitle="Skills appearing more often—or newly appearing—in recent job ads."
          items={emerging}
          direction="up"
          emptyMessage={window.previous_postings === 0
            ? 'A prior-year comparison sample is not available, so emerging skills cannot be confirmed yet.'
            : 'No clear growth signals meet the minimum posting threshold in this period.'}
        />
        <SkillSignalList
          title="Declining skills"
          subtitle="Skills with a meaningful drop in mentions across comparable periods."
          items={declining}
          direction="down"
          emptyMessage={window.previous_postings === 0
            ? 'A prior-year comparison sample is not available, so declining skills cannot be confirmed yet.'
            : 'No clear decline signals meet the minimum posting threshold in this period.'}
        />
      </div>
      <p className="px-1 text-[11px] leading-relaxed text-gray-400">
        Based on {window.current_postings + window.previous_postings} dated job postings with extracted skills. Skills require at least three postings per signal; limited samples are marked as early signals. Last generated {insights.generated_at}.
      </p>
    </div>
  )
}

export default DemandInsightsPanel
