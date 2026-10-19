import { useCallback, useEffect, useRef, useState } from 'react'
import { Activity, RefreshCw } from 'lucide-react'
import { API_URL } from '../App'

const HORIZONS = [3, 6, 12, 24, 36]

function DemandLineChart({ title, items, selectedName, onSelect, horizon }) {
  const chartContainer = useRef(null)
  const [chartWidth, setChartWidth] = useState(360)
  const selected = items.find((item) => item.name === selectedName) || items[0]
  const history = selected?.history || []
  const forecast = selected?.forecast || []
  const points = [...history, ...forecast]
  const width = chartWidth
  const height = 280
  const padding = { top: 18, right: 12, bottom: 42, left: width < 400 ? 38 : 48 }
  const plotWidth = width - padding.left - padding.right
  const plotHeight = height - padding.top - padding.bottom
  const highest = Math.max(1, ...points.map((point) => Number(point.demand) || 0))
  const yMaximum = Math.ceil(highest / 4) * 4 || 1
  const x = (index) => padding.left + (points.length > 1 ? index / (points.length - 1) : 0) * plotWidth
  const y = (value) => padding.top + plotHeight - (Number(value) || 0) / yMaximum * plotHeight
  const historyPath = history
    .map((point, index) => `${index === 0 ? 'M' : 'L'} ${x(index)} ${y(point.demand)}`)
    .join(' ')
  const forecastPath = forecast.length
    ? [
        `M ${x(history.length - 1)} ${y(history[history.length - 1]?.demand || 0)}`,
        ...forecast.map((point, index) => `L ${x(history.length + index)} ${y(point.demand)}`),
      ].join(' ')
    : ''
  const dividerX = history.length ? x(history.length - 1) : padding.left
  const labelIndices = [...new Set([
    0,
    Math.floor((points.length - 1) / 3),
    Math.floor((points.length - 1) * 2 / 3),
    points.length - 1,
  ])]
  const formatPeriod = (period) => new Date(`${String(period).slice(0, 7)}-02T00:00:00`).toLocaleDateString(
    undefined,
    { month: 'short', year: '2-digit' },
  )

  useEffect(() => {
    const container = chartContainer.current
    if (!container) return undefined
    const observer = new ResizeObserver(([entry]) => {
      setChartWidth(Math.max(280, Math.round(entry.contentRect.width)))
    })
    observer.observe(container)
    return () => observer.disconnect()
  }, [])

  return (
    <section className="min-w-0 rounded-xl border border-gray-200 bg-white p-3 shadow-sm sm:p-5">
      <div className="flex min-w-0 flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <h3 className="text-sm font-bold text-gray-900">{title}</h3>
          <p className="mt-1 text-[11px] text-gray-500">Monthly job-posting demand, past and projected</p>
        </div>
        {items.length > 0 && (
          <select
            aria-label={`Choose ${title.toLowerCase()}`}
            value={selected?.name || ''}
            onChange={(event) => onSelect(event.target.value)}
            className="w-full min-w-0 rounded-lg border border-gray-200 bg-white px-3 py-2 text-xs text-gray-700 sm:max-w-48"
          >
            {items.map((item) => (
              <option key={item.name} value={item.name}>
                {item.name} · {item.classification}
              </option>
            ))}
          </select>
        )}
      </div>
      {!selected || history.length === 0 || forecast.length === 0 ? (
        <p className="mt-6 rounded-lg bg-gray-50 px-4 py-8 text-center text-xs text-gray-500">
          Monthly trend data is not available yet. Refresh the demand outlook after job-posting data has been collected.
        </p>
      ) : (
        <>
          <div className="mt-4 flex min-w-0 flex-col items-start gap-2 text-xs sm:flex-row sm:items-center sm:justify-between">
            <span className="max-w-full break-words font-semibold text-gray-800">{selected.name}</span>
            <span className={`max-w-full rounded-full px-2.5 py-1 font-bold capitalize ${
              selected.classification === 'emerging'
                ? 'bg-emerald-50 text-emerald-700'
                : selected.classification === 'declining'
                  ? 'bg-rose-50 text-rose-700'
                  : 'bg-slate-100 text-slate-700'
            }`}>
              {selected.classification} · {selected.expected_change_percent > 0 ? '+' : ''}{selected.expected_change_percent}%
            </span>
          </div>
          <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-2 text-[10px] text-gray-500">
            <span className="flex items-center gap-1.5"><span className="h-0.5 w-5 bg-blue-600" />Past demand</span>
            <span className="flex items-center gap-1.5"><span className="w-5 border-t-2 border-dashed border-emerald-600" />Forecast</span>
          </div>
          <div ref={chartContainer} className="mt-2 w-full min-w-0">
            <svg
              viewBox={`0 0 ${width} ${height}`}
              className="block h-auto w-full"
              role="img"
              aria-label={`${title} for ${selected.name}: historical and forecast monthly job postings`}
              preserveAspectRatio="none"
            >
              {[0, 1, 2, 3, 4].map((tick) => {
                const value = yMaximum * tick / 4
                const tickY = y(value)
                return (
                  <g key={tick}>
                    <line x1={padding.left} y1={tickY} x2={width - padding.right} y2={tickY} stroke="#e5e7eb" />
                    <text x={padding.left - 8} y={tickY + 4} textAnchor="end" fill="#6b7280" fontSize="10">
                      {Number.isInteger(value) ? value : value.toFixed(1)}
                    </text>
                  </g>
                )
              })}
              <line
                x1={dividerX}
                y1={padding.top}
                x2={dividerX}
                y2={height - padding.bottom}
                stroke="#9ca3af"
                strokeDasharray="3 4"
              />
              <path d={historyPath} fill="none" stroke="#2563eb" strokeWidth="2.5" strokeLinejoin="round" strokeLinecap="round" />
              <path d={forecastPath} fill="none" stroke="#059669" strokeWidth="2.5" strokeDasharray="6 5" strokeLinejoin="round" strokeLinecap="round" />
              {history.map((point, index) => (
                <circle key={`history-${point.period}`} cx={x(index)} cy={y(point.demand)} r="2" fill="#2563eb">
                  <title>{formatPeriod(point.period)}: {point.demand} postings</title>
                </circle>
              ))}
              {forecast.map((point, index) => (
                <circle key={`forecast-${point.period}`} cx={x(history.length + index)} cy={y(point.demand)} r="2.5" fill="#059669">
                  <title>{formatPeriod(point.period)} forecast: {point.demand} postings</title>
                </circle>
              ))}
              {labelIndices.map((index) => (
                <text
                  key={index}
                  x={x(index)}
                  y={height - 15}
                  textAnchor={index === 0 ? 'start' : index === points.length - 1 ? 'end' : 'middle'}
                  fill="#6b7280"
                  fontSize="10"
                >
                  {formatPeriod(points[index].period)}
                </text>
              ))}
            </svg>
          </div>
          <p className="mt-1 text-center text-[10px] text-gray-400">
            Job postings per month · dashed line shows the next {horizon} months
          </p>
        </>
      )}
    </section>
  )
}

function FutureDemandForecastPanel({ onCollect, canCollect }) {
  const [horizon, setHorizon] = useState(36)
  const [report, setReport] = useState(null)
  const [selectedSkill, setSelectedSkill] = useState('')
  const [selectedRole, setSelectedRole] = useState('')
  const [loading, setLoading] = useState(true)
  const [training, setTraining] = useState(false)
  const [error, setError] = useState('')

  const loadForecast = useCallback(async (signal) => {
    let response = await fetch(
      `${API_URL}/forecast/demand-forecast?horizon_months=${horizon}`,
      { signal },
    )
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}))
      throw new Error(payload.detail || `Forecast request failed (${response.status})`)
    }
    let payload = await response.json()
    const hasHistoricalPoints = payload.series?.length
      && payload.series.every((item) => Array.isArray(item.history) && item.history.length > 0)
    if (!hasHistoricalPoints) {
      response = await fetch(
        `${API_URL}/forecast/demand-forecast/train?horizon_months=${horizon}`,
        { method: 'POST', signal },
      )
      payload = await response.json()
      if (!response.ok) {
        throw new Error(payload.detail || `Initial training failed (${response.status})`)
      }
    }
    setReport(payload)
    setError('')
  }, [horizon])

  useEffect(() => {
    let active = true
    let pending = false
    const controller = new AbortController()
    const refresh = async () => {
      if (pending) return
      pending = true
      try {
        await loadForecast(controller.signal)
      } catch (loadError) {
        if (active && loadError.name !== 'AbortError') setError(loadError.message)
      } finally {
        pending = false
        if (active) setLoading(false)
      }
    }
    refresh()
    const interval = window.setInterval(refresh, 60_000)
    return () => {
      active = false
      controller.abort()
      window.clearInterval(interval)
    }
  }, [loadForecast])

  const trainForecast = async () => {
    setTraining(true)
    setError('')
    try {
      const response = await fetch(
        `${API_URL}/forecast/demand-forecast/train?horizon_months=${horizon}`,
        { method: 'POST' },
      )
      const payload = await response.json()
      if (!response.ok) throw new Error(payload.detail || `Training failed (${response.status})`)
      setReport(payload)
    } catch (trainError) {
      setError(trainError.message || 'Could not update the demand outlook.')
    } finally {
      setTraining(false)
    }
  }

  if (loading && !report) {
    return (
      <div className="rounded-xl border border-gray-200 bg-white p-5 text-center text-sm text-gray-600 sm:p-8">
        <span className="mx-auto block h-6 w-6 animate-spin rounded-full border-2 border-brand/20 border-t-brand" />
        <p className="mt-3 font-semibold">{training || loading ? 'Preparing the first forecast report…' : 'Loading the latest forecast report…'}</p>
        <p className="mt-1 text-xs text-gray-500">Preparing practical skill and job-role demand insights.</p>
      </div>
    )
  }

  if (!report?.available && !report?.series) {
    return (
      <section className="rounded-xl border border-gray-200 bg-white p-4 text-center shadow-sm sm:p-6">
        <Activity className="mx-auto h-8 w-8 text-brand" />
        <h3 className="mt-3 text-sm font-bold text-gray-900">The forecast report could not be prepared</h3>
        <p className="mx-auto mt-2 max-w-xl text-xs leading-relaxed text-gray-500">
          {error
            ? 'The demand outlook could not be prepared. Please try again later.'
            : 'A demand outlook will be available when there is enough dated job-posting history.'}
        </p>
        {error && <p role="alert" className="mt-3 text-xs text-rose-700">{error}</p>}
        <div className="mt-4 flex flex-wrap justify-center gap-2">
          <button onClick={trainForecast} disabled={training} className="rounded-lg bg-brand px-4 py-2 text-xs font-semibold text-white disabled:opacity-60">
            {training ? 'Preparing outlook…' : 'Retry outlook'}
          </button>
          {canCollect && <button onClick={onCollect} className="rounded-lg border border-gray-300 px-4 py-2 text-xs font-semibold text-gray-700">Collect job data</button>}
        </div>
      </section>
    )
  }

  const skillSeries = (report.series || []).filter((item) => item.series_type === 'skills')
  const roleSeries = (report.series || []).filter((item) => item.series_type === 'roles')
  return (
    <div className="w-full min-w-0 space-y-3 sm:space-y-4">
      <section className="flex min-w-0 flex-col gap-3 rounded-xl bg-gradient-to-br from-slate-900 via-blue-950 to-indigo-900 p-4 text-white shadow-sm sm:flex-row sm:items-center sm:justify-between sm:p-5">
        <div className="min-w-0">
          <h3 className="text-base font-bold">Future job-market demand</h3>
          <p className="mt-1 text-xs leading-relaxed text-blue-100/80">
            Explore how skill and job-role demand may change, based on {report.source_postings} job postings.
          </p>
        </div>
        <label className="w-full text-xs font-semibold text-blue-100 sm:w-auto sm:shrink-0">
          Forecast period
          <select
            value={horizon}
            onChange={(event) => {
              setLoading(true)
              setHorizon(Number(event.target.value))
            }}
            className="mt-1 block w-full rounded-lg border border-white/20 bg-slate-800 px-3 py-2 text-white sm:w-auto"
          >
            {HORIZONS.map((months) => <option key={months} value={months}>{months} months</option>)}
          </select>
        </label>
      </section>

      {error && <div role="alert" className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-xs text-rose-800">{error}</div>}

      <div className="grid min-w-0 grid-cols-1 gap-3 xl:grid-cols-2 sm:gap-4">
        <DemandLineChart
          title="Skill demand forecast"
          items={skillSeries}
          selectedName={selectedSkill}
          onSelect={setSelectedSkill}
          horizon={report.requested_horizon_months || horizon}
        />
        <DemandLineChart
          title="Job-role demand forecast"
          items={roleSeries}
          selectedName={selectedRole}
          onSelect={setSelectedRole}
          horizon={report.requested_horizon_months || horizon}
        />
      </div>
      <p className="px-1 text-[11px] leading-relaxed text-gray-500">
        Solid lines show postings already collected. Dashed lines show forecast demand; projections are estimates, not guaranteed vacancies.
      </p>

      <div className="flex justify-stretch sm:justify-end">
        <button onClick={trainForecast} disabled={training} className="flex w-full items-center justify-center gap-2 rounded-lg border border-gray-200 bg-white px-3 py-2.5 text-xs font-semibold text-gray-700 disabled:opacity-60 sm:w-auto sm:py-2">
          <RefreshCw className={`h-3.5 w-3.5 ${training ? 'animate-spin' : ''}`} />
          {training ? 'Updating outlook…' : 'Refresh demand outlook'}
        </button>
      </div>
    </div>
  )
}

export default FutureDemandForecastPanel
