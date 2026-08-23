import React, { useState, useEffect } from 'react'
import Logo  from './Logo.jsx'
import { API_URL } from '../App.jsx'
import { 
  Briefcase, Users, BarChart3, Plus, Search, 
  MapPin, DollarSign, Check, X, FileText, UserCheck, AlertTriangle,
  Database, Cpu, Server, RefreshCw, Shield
} from 'lucide-react'

function AdminDashboard({ user, onLogout }) {
  const [metrics, setMetrics] = useState(null)
  const [scrapers, setScrapers] = useState([])
  
  // UI States
  const [scrapeLoadingId, setScrapeLoadingId] = useState('')
  const [scrapeSuccessMsg, setScrapeSuccessMsg] = useState('')
  const [systemLoad, setSystemLoad] = useState(38)

  useEffect(() => {
    fetchMetrics()
    fetchScrapers()
    
    // Simulate slight fluctuations in system load for prototype look-and-feel
    const interval = setInterval(() => {
      setSystemLoad(Math.floor(Math.random() * (45 - 30 + 1) + 30))
    }, 4000)
    
    return () => clearInterval(interval)
  }, [])

  const fetchMetrics = async () => {
    try {
      const res = await fetch(`${API_URL}/admin/metrics`)
      const data = await res.json()
      setMetrics(data)
    } catch (e) {
      console.error("Error fetching metrics", e)
    }
  }

  const fetchScrapers = async () => {
    try {
      const res = await fetch(`${API_URL}/admin/scrapers`)
      const data = await res.json()
      setScrapers(data)
    } catch (e) {
      console.error("Error fetching scrapers", e)
    }
  }

  const handleTriggerScrape = async (scraperId) => {
    setScrapeLoadingId(scraperId)
    setScrapeSuccessMsg('')
    try {
      const res = await fetch(`${API_URL}/admin/scrape`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scraper_id: scraperId })
      })
      const data = await res.json()
      if (res.ok) {
        setScrapeSuccessMsg(`Simulation success: ${scrapers[scraperId].name} compiled! Found new entries.`)
        // Refresh local UI states
        fetchScrapers()
        fetchMetrics()
        setTimeout(() => setScrapeSuccessMsg(''), 4500)
      }
    } catch (e) {
      console.error("Error running scraper simulation", e)
    } finally {
      setScrapeLoadingId('')
    }
  }

  return (
    <div className="flex-1 flex flex-col md:flex-row min-h-screen">
      {/* Sidebar */}
      <aside className="w-full md:w-64 bg-white border-r border-gray-200 p-6 flex flex-col justify-between shrink-0">
        <div>
          <div className="flex items-center space-x-2 mb-8">
            <Logo className="h-8 w-auto" />
          </div>

          <div className="bg-gray-50 border border-gray-100 rounded-xl p-4 mb-6 text-xs flex items-center space-x-2">
            <Shield className="h-5 w-5 text-red-600" />
            <div>
              <span className="font-bold text-gray-900 block">Admin Panel</span>
              <p className="text-gray-500 font-semibold">{user.name}</p>
            </div>
          </div>

          <div className="space-y-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">
            <span>System Control Node</span>
            <div className="space-y-1 mt-2">
              <div className="flex justify-between items-center py-1.5 px-2 bg-red-50 text-red-700 rounded border border-red-100">
                <span>Node Status:</span>
                <span className="font-extrabold uppercase text-[10px] animate-pulse">Live</span>
              </div>
              <div className="flex justify-between items-center py-1.5 px-2 bg-gray-50 text-gray-600 rounded">
                <span>CPU Load:</span>
                <span>{systemLoad}%</span>
              </div>
            </div>
          </div>
        </div>

        <button
          onClick={onLogout}
          className="w-full py-2 border border-gray-300 rounded text-xs font-medium text-gray-700 hover:bg-gray-50 transition-colors"
        >
          Logout Session
        </button>
      </aside>

      {/* Main Panel */}
      <main className="flex-1 flex flex-col bg-gray-50">
        <header className="bg-white border-b border-gray-200 px-6 py-4 flex justify-between items-center shrink-0">
          <div>
            <h1 className="text-xl font-bold text-gray-900">Platform Scraper Operations</h1>
            <p className="text-xs text-gray-500 mt-0.5">Control data sync adapters for LinkedIn, Indeed, TopJobs, Coursera, and Surveys</p>
          </div>
        </header>

        <section className="flex-1 p-6 overflow-y-auto space-y-6">
          {/* Quick Metrics Cards */}
          {metrics && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
              <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm flex items-center space-x-3">
                <div className="p-3 bg-blue-50 text-blue-600 rounded-lg">
                  <Database className="h-5 w-5" />
                </div>
                <div>
                  <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider block">Scraped Jobs</span>
                  <span className="text-lg font-extrabold text-gray-900">{metrics.total_jobs}</span>
                </div>
              </div>
              
              <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm flex items-center space-x-3">
                <div className="p-3 bg-indigo-50 text-indigo-600 rounded-lg">
                  <Cpu className="h-5 w-5" />
                </div>
                <div>
                  <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider block">Indexed Courses</span>
                  <span className="text-lg font-extrabold text-gray-900">{metrics.total_courses}</span>
                </div>
              </div>

              <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm flex items-center space-x-3">
                <div className="p-3 bg-emerald-50 text-emerald-600 rounded-lg">
                  <Users className="h-5 w-5" />
                </div>
                <div>
                  <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider block">Candidates Gained</span>
                  <span className="text-lg font-extrabold text-gray-900">{metrics.total_candidates}</span>
                </div>
              </div>

              <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm flex items-center space-x-3">
                <div className="p-3 bg-red-50 text-red-600 rounded-lg">
                  <Server className="h-5 w-5" />
                </div>
                <div>
                  <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider block">Server Health</span>
                  <span className="text-xs font-extrabold text-emerald-600 flex items-center uppercase mt-1">
                    <span className="h-2.5 w-2.5 bg-emerald-500 rounded-full inline-block mr-1"></span>
                    {metrics.system_status}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Scrapers management card */}
          <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
            <h2 className="text-sm font-bold text-gray-900 mb-2">Integrated Platform Scrapers</h2>
            <p className="text-xs text-gray-500 mb-6">Emploeralk scrapes external platforms to compute skills demand forecasting. Run simulations below to verify ETL logic.</p>
            
            {scrapeSuccessMsg && (
              <div className="mb-6 p-3 bg-blue-50 border border-blue-200 text-blue-800 text-xs rounded text-center font-semibold">
                {scrapeSuccessMsg}
              </div>
            )}

            <div className="space-y-4">
              {Object.keys(scrapers).map((key) => {
                const scr = scrapers[key]
                const isLoading = scrapeLoadingId === key
                return (
                  <div key={key} className="flex flex-col sm:flex-row justify-between items-start sm:items-center p-4 border border-gray-100 rounded-lg hover:bg-gray-50 transition-all gap-4">
                    <div className="flex items-start space-x-3">
                      <div className={`p-2 rounded mt-1 shrink-0 ${
                        scr.status === 'Scraping...' ? 'bg-yellow-100 text-yellow-700' : 'bg-gray-100 text-gray-600'
                      }`}>
                        <RefreshCw className={`h-4 w-4 ${scr.status === 'Scraping...' ? 'animate-spin' : ''}`} />
                      </div>
                      
                      <div>
                        <h4 className="text-xs font-bold text-gray-900">{scr.name}</h4>
                        <p className="text-[10px] text-gray-500 mt-0.5">Last triggered: {scr.last_run} • Collected count: <strong className="text-gray-800">{scr.records_found}</strong></p>
                      </div>
                    </div>

                    <div className="flex items-center space-x-4 self-end sm:self-center shrink-0">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                        scr.status === 'Idle' 
                          ? 'bg-gray-100 text-gray-600 border border-gray-200' 
                          : 'bg-yellow-150 text-yellow-700 border border-yellow-300'
                      }`}>
                        {scr.status}
                      </span>
                      
                      <button
                        onClick={() => handleTriggerScrape(key)}
                        disabled={scrapeLoadingId !== ''}
                        className="px-4 py-1.5 border border-brand text-brand hover:bg-brand hover:text-white rounded text-xs font-bold transition-all disabled:opacity-50"
                      >
                        {isLoading ? 'Crawling...' : 'Trigger Scrape'}
                      </button>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>

          {/* System logs simulation terminal */}
          <div className="bg-gray-950 text-white font-mono p-5 rounded-xl border border-gray-800 shadow-lg">
            <div className="flex space-x-1.5 mb-4">
              <span className="h-3 w-3 rounded-full bg-red-500"></span>
              <span className="h-3 w-3 rounded-full bg-yellow-500"></span>
              <span className="h-3 w-3 rounded-full bg-green-500"></span>
              <span className="text-[10px] text-gray-500 pl-4">emploeralk-admin@pipeline-node</span>
            </div>
            
            <div className="space-y-1.5 text-xs text-gray-300 leading-relaxed">
              <p>&gt; sys_status: querying docker instances ... <span className="text-emerald-500">Healthy</span></p>
              <p>&gt; mem_usage: 242MB / 1024MB allocated</p>
              <p>&gt; flask_api: listening on interface 127.0.0.1:5000</p>
              <p>&gt; model_analyzer: coefficients generated for 18 distinct tech fields</p>
              <p className="text-[10px] text-gray-500 mt-4">// Active socket channels mapping candidate surveys ...</p>
              <p>&gt; socket_conn: CV collector stream opened successfully.</p>
            </div>
          </div>
        </section>
      </main>
    </div>
  )
}

export default AdminDashboard

