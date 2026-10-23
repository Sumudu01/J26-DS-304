import React, { useState, useEffect, useRef } from 'react'
import Logo from './Logo.jsx'
import NotificationCenter from './NotificationCenter.jsx'
import DemandInsightsPanel from './DemandInsightsPanel.jsx'
import TargetRoleInput from './TargetRoleInput.jsx'
import { createNotification } from './notificationsApi.js'
import { API_URL } from '../App'
import {
  TrendingUp, FileSearch, Milestone, CheckSquare,
  User, Upload, BookOpen, GraduationCap, Briefcase,
  MapPin, DollarSign, ExternalLink, RefreshCw, CheckCircle2, ChevronRight,
  LogOut, X, Search, ArrowUpRight, BarChart3, Layers, Zap, AlertTriangle, Menu, ChevronLeft,
  Target, Filter, Clock3, Sparkles
} from 'lucide-react'
import ForceGraph2D from 'react-force-graph-2d'

function SeekerDashboard({ user, onUpdateUser, onLogout }) {
  const [activeTab, setActiveTab] = useState('demand') // 'demand', 'gap', 'path', 'matching', 'profile'
  const [isSidebarOpen, setIsSidebarOpen] = useState(false)

  // Profile update state
  const [editSkills, setEditSkills] = useState(user.skills.join(', '))
  const [editTargetRole, setEditTargetRole] = useState(user.target_role || 'AI Engineer')
  const [isUpdatingProfile, setIsUpdatingProfile] = useState(false)
  const [profileSuccessMsg, setProfileSuccessMsg] = useState('')
  const [profileErrorMsg, setProfileErrorMsg] = useState('')

  // CV Upload state
  const [cvFile, setCvFile] = useState(null)
  const [cvUploadLoading, setCvUploadLoading] = useState(false)
  const [cvSuccessMsg, setCvSuccessMsg] = useState('')
  const [cvErrorMsg, setCvErrorMsg] = useState('')
  const [savedCv, setSavedCv] = useState(null)

  // API response states
  const [demandData] = useState([])
  const [forecastHorizon, setForecastHorizon] = useState('2029') // 2027, 2028, 2029
  const [demandInsights, setDemandInsights] = useState(null)
  const [demandInsightsLoading, setDemandInsightsLoading] = useState(false)
  const [demandInsightsError, setDemandInsightsError] = useState('')

  // Search demand state
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResult, setSearchResult] = useState(null)
  const [searchLoading, setSearchLoading] = useState(false)
  const [searchError, setSearchError] = useState('')
  const [hasSearched, setHasSearched] = useState(false)
  const [gapData, setGapData] = useState(null)
  const [careerData, setCareerData] = useState(null)
  const [matchedJobs, setMatchedJobs] = useState([])
  const [matchingTotal, setMatchingTotal] = useState(0)
  const [matchingPage, setMatchingPage] = useState(1)
  const [matchingTotalPages, setMatchingTotalPages] = useState(1)
  const [matchingSource, setMatchingSource] = useState('')
  const [matchingError, setMatchingError] = useState('')
  // true while the backend 503s with warming=true (model still loading at startup)
  const [matchingWarmingUp, setMatchingWarmingUp] = useState(false)

  // UI states
  const [loading, setLoading] = useState(false)
  const [appliedJobIds, setAppliedJobIds] = useState(new Set())
  const [jobSearchQuery, setJobSearchQuery] = useState('')
  const [isSearchingJobs, setIsSearchingJobs] = useState(false)
  const [gapSearchQuery, setGapSearchQuery] = useState('')
  const [isSearchingGap, setIsSearchingGap] = useState(false)

  // Course Search states
  const [courseSearchQuery, setCourseSearchQuery] = useState('')
  const [courseSearchScope, setCourseSearchScope] = useState('recommended') // 'recommended' or 'all'
  const [allCourses, setAllCourses] = useState([])
  const [isSearchingCourses, setIsSearchingCourses] = useState(false)

  // Salary Insights state
  const [salaryData, setSalaryData] = useState(null)

  // Live Job Listings state (Market Forecasts tab)
  const [liveJobs, setLiveJobs] = useState([])
  const [liveJobsTotal, setLiveJobsTotal] = useState(0)
  const [liveJobsPage, setLiveJobsPage] = useState(1)
  const [liveJobsLoading, setLiveJobsLoading] = useState(false)
  const [liveJobsError, setLiveJobsError] = useState('')
  const [liveJobsSource, setLiveJobsSource] = useState('') // '', 'LinkedIn', 'TopJobs'
  const [pipelineStatus, setPipelineStatus] = useState(null) // null | 'running' | 'done'
  const [pipelineTriggerLoading, setPipelineTriggerLoading] = useState(false)
  const [demandSubView, setDemandSubView] = useState('listings') // 'listings' | 'forecast'

  const graphContainerRef = useRef(null)
  const [graphWidth, setGraphWidth] = useState(800)
  const userSkillsKey = Array.isArray(user.skills) ? user.skills.join(',') : user.skills || ''

  // Centralised 401 handler — called whenever an authenticated fetch returns
  // 401 Unauthorized.  Clears the stale token and redirects to login so the
  // user is never stuck on a broken dashboard full of auth errors.
  const handle401 = () => {
    localStorage.removeItem('emploeralk_token')
    localStorage.removeItem('emploeralk_user')
    onLogout()
  }

  useEffect(() => {
    Promise.resolve().then(() => {
      setEditSkills(Array.isArray(user.skills) ? user.skills.join(', ') : user.skills || '')
      setEditTargetRole(user.target_role || '')
    })
  }, [user.skills, user.target_role])

  useEffect(() => {
    const token = localStorage.getItem('emploeralk_token')
    fetch(`${API_URL}/profile/cv`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {}
    })
      .then(async (res) => {
        if (res.status === 401) { handle401(); return null }
        if (res.status === 404) return null
        if (!res.ok) throw new Error('Could not load saved CV details.')
        return res.json()
      })
      .then(setSavedCv)
      .catch(() => setSavedCv(null))
  }, [user.email])

  useEffect(() => {
    const handleResize = () => {
      if (graphContainerRef.current) {
        setGraphWidth(graphContainerRef.current.clientWidth)
      }
    }
    window.addEventListener('resize', handleResize)
    // Initial check
    setTimeout(handleResize, 100)
    return () => window.removeEventListener('resize', handleResize)
  }, [activeTab, gapData])

  // Load initial data
  useEffect(() => {
    fetchGapAnalysis()
    fetchCareerPath()
    fetchMatchingJobs('', 1, '')
    fetchSalaryInsights()
  }, [user]) // Re-run whenever user profile changes (skills, target_role)

  // Fetch live jobs when demand tab is active
  useEffect(() => {
    if (activeTab === 'demand') {
      fetchLiveJobs(1, '')
    }
  }, [activeTab, user.target_role, userSkillsKey])

  const fetchDemandForecast = async () => {
    setDemandInsightsLoading(true)
    setDemandInsightsError('')
    setDemandInsights(null)
    try {
      const res = await fetch(`${API_URL}/forecast/demand-insights?target_year=${forecastHorizon}`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      setDemandInsights(await res.json())
    } catch (e) {
      console.error('Error loading future demand insights', e)
      setDemandInsightsError(e.message || 'Could not load demand insights.')
    } finally {
      setDemandInsightsLoading(false)
    }
  }

  useEffect(() => {
    if (activeTab === 'demand' && demandSubView === 'forecast') {
      fetchDemandForecast()
    }
  }, [activeTab, demandSubView, forecastHorizon])

  const fetchGapAnalysis = async (targetRole = user.target_role) => {
    setIsSearchingGap(true)
    try {
      const res = await fetch(`${API_URL}/skill-gap`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ skills: user.skills, target_role: targetRole })
      })
      const data = await res.json()
      setGapData(data)
      // Re-fetch salary insights with accurate missing skills
      fetchSalaryInsights(data.missing_skills || [])
    } catch (e) {
      console.error("Error loading gap analysis", e)
    } finally {
      setIsSearchingGap(false)
    }
  }

  const fetchCareerPath = async () => {
    try {
      const res = await fetch(`${API_URL}/career-path`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ current_role: user.current_role, target_role: user.target_role })
      })
      const data = await res.json()
      setCareerData(data)
    } catch (e) {
      console.error("Error loading career path", e)
    }
  }

  const fetchSalaryInsights = async (missingSkills = []) => {
    try {
      const res = await fetch(`${API_URL}/salary-insights`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          current_role: user.current_role,
          target_role: user.target_role,
          missing_skills: missingSkills
        })
      })
      const data = await res.json()
      setSalaryData(data)
    } catch (e) {
      console.error("Error loading salary insights", e)
    }
  }

  const fetchMatchingJobs = async (query = '', page = 1, source = matchingSource) => {
    setIsSearchingJobs(true)
    setMatchingError('')
    setMatchingWarmingUp(false)

    // 180-second abort for the very first cold start when the FAISS index is
    // being built from scratch.  After the index is saved to disk all
    // subsequent requests complete in ~1-2 s so this timer never fires.
    const controller = new AbortController()
    const abortTimer = setTimeout(() => controller.abort(), 180000)

    try {
      const PAGE_SIZE = 12
      const params = new URLSearchParams({
        top_k: '50',
        rerank_top_k: '50',
        reasoning_top_k: '3',
        page: String(page),
        page_size: String(PAGE_SIZE),
      })
      const res = await fetch(`${API_URL}/matching/recommendations?${params.toString()}`, {
        signal: controller.signal,
        headers: {
          Authorization: `Bearer ${localStorage.getItem('emploeralk_token') || ''}`
        }
      })
      const data = await res.json()

      // 503 with warming=true → model still starting up; auto-retry after 15 s
      if (!res.ok && res.status === 503 && data?.detail?.warming) {
        setMatchingWarmingUp(true)
        setIsSearchingJobs(false)
        clearTimeout(abortTimer)
        setTimeout(() => fetchMatchingJobs(query, page, source), 15000)
        return
      }

      if (res.status === 401) { handle401(); return }
      if (!res.ok) throw new Error(data.detail?.message || data.detail || data.error || `HTTP ${res.status}`)
      setMatchingWarmingUp(false)
      setMatchedJobs(data.items || [])
      // total_available = full FAISS index size (used for pagination math)
      setMatchingTotal(data.total_available ?? data.total ?? data.total_matched ?? 0)
      // Use server-computed total_pages when available
      setMatchingTotalPages(data.total_pages ?? Math.ceil((data.total_available ?? 1) / 12) ?? 1)
      setMatchingPage(page)
    } catch (e) {
      if (e.name === 'AbortError') {
        setMatchingError('Building job index for the first time — this takes a few minutes on first run. The page will auto-retry shortly.')
        setTimeout(() => fetchMatchingJobs(query, page, source), 20000)
      } else if (e.message && e.message.toLowerCase().includes('could not validate credentials')) {
        handle401()
      } else {
        console.error('Error loading matched jobs', e)
        setMatchedJobs([])
        setMatchingTotal(0)
        setMatchingError(e.message || 'Could not load matching jobs. Check that the backend is running and try again.')
      }
    } finally {
      clearTimeout(abortTimer)
      setIsSearchingJobs(false)
    }
  }

  const fetchCatalogCourses = async (query = '') => {
    setIsSearchingCourses(true)
    try {
      const res = await fetch(`${API_URL}/courses?query=${encodeURIComponent(query)}`)
      const data = await res.json()
      setAllCourses(data)
    } catch (e) {
      console.error("Error loading catalog courses", e)
    } finally {
      setIsSearchingCourses(false)
    }
  }

  // Fetch live job postings from the agentic pipeline backend
  const fetchLiveJobs = async (page = 1, source = liveJobsSource, keyword = searchQuery) => {
    const q = (keyword || '').trim()
    if (!user.target_role && q.length < 2) return []
    setLiveJobsLoading(true)
    setLiveJobsError('')
    try {
      const skillsParam = Array.isArray(user.skills) ? user.skills.join(',') : (user.skills || '')
      const params = new URLSearchParams({
        skills: skillsParam,
        page: String(page),
        page_size: '15',
      })
      if (user.target_role) params.set('target_role', user.target_role)
      if (q.length >= 2) params.set('keyword', q)
      if (source) params.set('source', source)
      const res = await fetch(`${API_URL}/forecast/jobs/recommended?${params.toString()}`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      const items = data.items || []
      setLiveJobs(items)
      setLiveJobsTotal(data.total_matched || 0)
      setLiveJobsPage(page)
      return items
    } catch (e) {
      console.error('Error loading live jobs', e)
      setLiveJobsError('Could not load live job listings. The pipeline may still be collecting data.')
      return []
    } finally {
      setLiveJobsLoading(false)
    }
  }

  // Trigger the full 4-agent pipeline for the user's target role
  const triggerPipeline = async () => {
    if (!user.target_role || pipelineTriggerLoading) return
    setPipelineTriggerLoading(true)
    setPipelineStatus('running')
    try {
      const params = new URLSearchParams({
        target_role: user.target_role,
        location: 'Sri Lanka',
        max_jobs: '25',  // Fast first batch; user can re-run for more
      })
      const res = await fetch(`${API_URL}/forecast/pipeline/run?${params.toString()}`, { method: 'POST' })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      setPipelineStatus('triggered')
      try {
        await createNotification({
          type: 'pipeline',
          title: 'Job search started',
          body: `The job collection pipeline is searching for ${user.target_role} roles in Sri Lanka.`,
        })
      } catch (notificationError) {
        console.error('Could not save job search notification', notificationError)
      }
      // Poll for new listings every 10s up to 3 times (stops when data arrives)
      let pollCount = 0
      const poll = setInterval(async () => {
        pollCount++
        await fetchLiveJobs(1, liveJobsSource)
        if (pollCount >= 3) clearInterval(poll)
      }, 10000)
    } catch (e) {
      console.error('Pipeline trigger error', e)
      setPipelineStatus('error')
    } finally {
      setPipelineTriggerLoading(false)
    }
  }

  // Debounced effect for fetching catalog courses
  useEffect(() => {
    if (courseSearchScope === 'all') {
      const delayDebounceFn = setTimeout(() => {
        fetchCatalogCourses(courseSearchQuery)
      }, 300)
      return () => clearTimeout(delayDebounceFn)
    }
  }, [courseSearchQuery, courseSearchScope])

  const buildLocalDemandResult = (query, jobs) => {
    const q = query.toLowerCase()
    const aliases = {
      'generative ai': 'Generative AI', genai: 'Generative AI', llm: 'Generative AI', nlp: 'Generative AI',
      python: 'Python', cloud: 'Cloud Computing', aws: 'Cloud Computing', docker: 'Cloud Computing',
      kubernetes: 'Cloud Computing', web: 'Traditional Web', jquery: 'Traditional Web', html: 'Traditional Web',
      cobol: 'COBOL/Legacy', legacy: 'COBOL/Legacy', mainframe: 'COBOL/Legacy',
    }
    const keys = demandData[0]
      ? Object.keys(demandData[0]).filter((k) => k !== 'year')
      : ['Generative AI', 'Python', 'Cloud Computing', 'Traditional Web', 'COBOL/Legacy']
    let matched = keys.find((k) => k.toLowerCase() === q || k.toLowerCase().includes(q) || q.includes(k.toLowerCase()))
    if (!matched) {
      const aliasKey = Object.keys(aliases).find((a) => q.includes(a))
      if (aliasKey) matched = aliases[aliasKey]
    }
    const relatedJobs = (jobs || []).slice(0, 8).map((job) => ({
      title: job.title,
      company: job.company,
      location: job.location,
      salary: job.salary || '—',
      platform: job.source,
    }))
    if (!matched || !demandData.length) {
      return {
        query,
        matched_skill_category: null,
        current_demand_index: 0,
        yoy_growth_percent: 0,
        demand_status: null,
        forecast_2029_index: 0,
        forecast_growth_percent: 0,
        trend_timeline: [],
        supply_demand_gap: null,
        related_jobs: relatedJobs,
        related_jobs_count: jobs?.length || relatedJobs.length,
      }
    }
    const timeline = demandData.map((d) => ({
      year: d.year,
      value: d[matched] ?? 0,
      is_forecast: d.year > 2026,
    }))
    const current = [...demandData].reverse().find((d) => d.year <= 2026) || demandData[0]
    const prev = demandData.find((d) => d.year === (current?.year || 0) - 1)
    const future = demandData.find((d) => d.year === 2029) || demandData[demandData.length - 1]
    const currentVal = current?.[matched] ?? 0
    const prevVal = prev?.[matched] ?? currentVal
    const futureVal = future?.[matched] ?? currentVal
    const yoy = prevVal ? Math.round(((currentVal - prevVal) / prevVal) * 100) : 0
    const growth = currentVal ? Math.round(((futureVal - currentVal) / currentVal) * 100) : 0
    return {
      query,
      matched_skill_category: matched,
      current_demand_index: currentVal,
      yoy_growth_percent: yoy,
      demand_status: yoy > 8 ? 'High & Growing' : yoy < -5 ? 'Declining' : 'Stable',
      forecast_2029_index: futureVal,
      forecast_growth_percent: growth,
      trend_timeline: timeline,
      supply_demand_gap: {
        skill: matched,
        demand: Math.min(100, Math.round((currentVal / 150) * 100)),
        supply: Math.max(10, 100 - Math.round((currentVal / 150) * 70)),
        gap: Math.min(100, Math.max(0, Math.round((currentVal / 150) * 55))),
      },
      related_jobs: relatedJobs,
      related_jobs_count: jobs?.length || relatedJobs.length,
    }
  }

  // Search jobs and skills across live listings and demand forecasting
  const searchSkillDemand = async (e) => {
    e && e.preventDefault()
    const query = searchQuery.trim()
    if (!query || query.length < 2) {
      setSearchError('Please enter at least 2 characters to search jobs or skills.')
      return
    }
    setSearchLoading(true)
    setSearchError('')
    setSearchResult(null)
    setHasSearched(true)
    try {
      const matchedJobs = await fetchLiveJobs(1, liveJobsSource, query)
      let demandPayload = null
      try {
        const res = await fetch(`${API_URL}/search-demand`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query })
        })
        if (res.ok) demandPayload = await res.json()
      } catch (err) {
        console.error('Search demand error', err)
      }
      setSearchResult(demandPayload || buildLocalDemandResult(query, matchedJobs))
    } catch (err) {
      console.error('Unified search error', err)
      setSearchError('Could not complete search. Please try again.')
    } finally {
      setSearchLoading(false)
    }
  }

  const clearSearch = () => {
    setSearchQuery('')
    setSearchResult(null)
    setSearchError('')
    setHasSearched(false)
    fetchLiveJobs(1, liveJobsSource, '')
  }

  // Save manual profile edits
  const handleSaveProfile = async (e) => {
    e.preventDefault()
    setIsUpdatingProfile(true)
    setProfileSuccessMsg('')
    setProfileErrorMsg('')
    try {
      const skillList = editSkills.split(',').map(s => s.trim()).filter(Boolean)
      const targetRole = editTargetRole.trim()
      if (!targetRole) {
        setProfileErrorMsg('Please enter a target role.')
        return
      }
      const res = await fetch(`${API_URL}/profile/update`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: user.email,
          skills: skillList,
          target_role: targetRole
        })
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || data.detail || 'Could not update your profile.')
      onUpdateUser(data.user)
      setProfileSuccessMsg('Profile updated. Analytics refreshed!')
      setTimeout(() => setProfileSuccessMsg(''), 4000)
    } catch (e) {
      console.error("Error updating profile", e)
      setProfileErrorMsg(e.message || 'Could not update your profile.')
    } finally {
      setIsUpdatingProfile(false)
    }
  }

  const handleCvUpload = async (e) => {
    e.preventDefault()
    if (!cvFile) return

    setCvUploadLoading(true)
    setCvSuccessMsg('')
    setCvErrorMsg('')

    const formData = new FormData()
    formData.append('cv', cvFile)
    formData.append('email', user.email)

    try {
      const res = await fetch(`${API_URL}/profile/upload-cv?email=${encodeURIComponent(user.email)}`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${localStorage.getItem('emploeralk_token') || ''}`
        },
        body: formData
      })
      const data = await res.json()
      if (res.status === 401) { handle401(); return }
      if (!res.ok) throw new Error(data.error || data.detail || 'Could not parse the CV.')

      onUpdateUser(data.user)
      setEditSkills(data.user.skills.join(', '))
      const persistedCv = {
        filename: data.filename,
        parsed: data.cv,
        uploadedAt: new Date().toISOString(),
        downloadUrl: data.download_url
      }
      setSavedCv({ ...data, ...persistedCv })
      setCvSuccessMsg(`Successfully parsed ${data.filename}! Added advanced skills.`)
      setCvFile(null)
      document.getElementById('cv-file-input').value = ''
    } catch (e) {
      console.error("Error uploading CV", e)
      setCvErrorMsg(e.message || 'Could not parse the CV.')
    } finally {
      setCvUploadLoading(false)
    }
  }

  const handleRemoveCv = () => {
    fetch(`${API_URL}/profile/cv`, {
      method: 'DELETE',
      headers: {
        Authorization: `Bearer ${localStorage.getItem('emploeralk_token') || ''}`
      }
    })
      .then(async (res) => {
        if (res.status === 401) { handle401(); return }
        if (!res.ok) {
          const data = await res.json().catch(() => ({}))
          throw new Error(data.error || data.detail || 'Could not remove the saved CV.')
        }
        setSavedCv(null)
        setCvSuccessMsg('Saved CV details removed from the server.')
        setCvErrorMsg('')
      })
      .catch((error) => setCvErrorMsg(error.message))
  }

  const handleDownloadCv = async () => {
    try {
      const res = await fetch(`${API_URL}/profile/cv/download`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('emploeralk_token') || ''}`
        }
      })
      if (res.status === 401) { handle401(); return }
      if (!res.ok) throw new Error('Could not download the saved CV.')
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = savedCv.filename || 'cv'
      link.click()
      URL.revokeObjectURL(url)
    } catch (error) {
      setCvErrorMsg(error.message)
    }
  }

  const handleApplyJob = (jobId) => {
    setAppliedJobIds(prev => {
      const updated = new Set(prev)
      updated.add(jobId)
      return updated
    })
  }

  return (
    <div className="flex-1 flex flex-col md:flex-row min-h-screen relative">
      {/* Mobile Sidebar Overlay */}
      {isSidebarOpen && (
        <div
          className="fixed inset-0 bg-gray-900/50 z-40 md:hidden"
          onClick={() => setIsSidebarOpen(false)}
        />
      )}

      {/* ── LEFT SIDEBAR – Vertical Navigation ── */}
      <aside className={`w-64 bg-white border-r border-gray-200 flex flex-col shrink-0 fixed inset-y-0 left-0 z-50 transform transition-transform duration-200 ease-in-out md:relative md:translate-x-0 ${isSidebarOpen ? 'translate-x-0' : '-translate-x-full'}`}>

        {/* Logo */}
        <div className="px-5 py-5 border-b border-gray-100 flex justify-between items-center">
          <Logo className="h-8 w-auto" />
          <button onClick={() => setIsSidebarOpen(false)} className="md:hidden p-1 text-gray-500 hover:bg-gray-100 rounded-lg">
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Nav links */}
        <nav className="flex-1 px-3 py-4 space-y-1">
          <p className="px-3 mb-2 text-[10px] font-semibold text-gray-400 uppercase tracking-widest">Dashboard</p>

          <button
            onClick={() => setActiveTab('demand')}
            className={`w-full flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${activeTab === 'demand'
                ? 'bg-brand text-white shadow-sm'
                : 'text-gray-600 hover:bg-gray-100'
              }`}
          >
            <TrendingUp className="h-4 w-4 shrink-0" />
            <span>Market Forecasts</span>
          </button>

          <button
            onClick={() => setActiveTab('gap')}
            className={`w-full flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${activeTab === 'gap'
                ? 'bg-brand text-white shadow-sm'
                : 'text-gray-600 hover:bg-gray-100'
              }`}
          >
            <FileSearch className="h-4 w-4 shrink-0" />
            <span>Skill Gap Discovery</span>
          </button>

          <button
            onClick={() => setActiveTab('path')}
            className={`w-full flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${activeTab === 'path'
                ? 'bg-brand text-white shadow-sm'
                : 'text-gray-600 hover:bg-gray-100'
              }`}
          >
            <Milestone className="h-4 w-4 shrink-0" />
            <span>Career Path Planning</span>
          </button>

          <button
            onClick={() => setActiveTab('matching')}
            className={`w-full flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${activeTab === 'matching'
                ? 'bg-brand text-white shadow-sm'
                : 'text-gray-600 hover:bg-gray-100'
              }`}
          >
            <CheckSquare className="h-4 w-4 shrink-0" />
            <span>Skill Matching &amp; Jobs</span>
          </button>

          {/* Divider */}
          <div className="pt-4 pb-1">
            <p className="px-3 mb-2 text-[10px] font-semibold text-gray-400 uppercase tracking-widest">Account</p>
          </div>

          {/* Profile nav link */}
          <button
            onClick={() => setActiveTab('profile')}
            className={`w-full flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${activeTab === 'profile'
                ? 'bg-brand text-white shadow-sm'
                : 'text-gray-600 hover:bg-gray-100'
              }`}
          >
            <User className="h-4 w-4 shrink-0" />
            <div className="text-left">
              <p className="leading-tight">{user.name}</p>
              <p className={`text-[10px] leading-tight ${activeTab === 'profile' ? 'text-white/70' : 'text-gray-400'}`}>
                {user.current_role}
              </p>
            </div>
          </button>
        </nav>
      </aside>

      {/* ── MAIN PANEL ── */}
      <main className="flex-1 flex flex-col bg-gray-50 min-w-0">
        {/* Top header bar */}
        <header className="bg-white border-b border-gray-200 px-3 sm:px-6 py-3 sm:py-4 shrink-0 flex items-center justify-between gap-2 relative min-w-0">
          {/* Left – page title */}
          <div className="flex items-center space-x-3 min-w-0">
            <button
              onClick={() => setIsSidebarOpen(true)}
              className="md:hidden p-2 -ml-2 text-gray-500 hover:bg-gray-100 rounded-lg"
            >
              <Menu className="h-5 w-5" />
            </button>
            <div>
              <h1 className="text-lg sm:text-xl font-bold text-gray-900 truncate">
                {activeTab === 'demand' && 'Market Forecasts'}
                {activeTab === 'gap' && 'Skill Gap Discovery'}
                {activeTab === 'path' && 'Career Path Planning'}
                {activeTab === 'matching' && 'Skill Matching & Jobs'}
                {activeTab === 'profile' && 'My Profile'}
              </h1>
              <p className="hidden sm:block text-xs text-gray-500 mt-0.5">
                {activeTab === 'profile'
                  ? 'Manage your skills, target role, and upload your CV'
                  : 'Diagnose skills, review roadmaps, and match vacancies'}
              </p>
            </div>
          </div>

          {/* Right – Notification bell & Logout */}
          <div className="flex items-center space-x-2 sm:space-x-4 shrink-0">
            <NotificationCenter />
            <button
              onClick={onLogout}
              className="flex items-center space-x-2 px-3 py-1.5 rounded-lg text-xs font-semibold text-red-500 hover:bg-red-50 border border-red-200 hover:border-red-300 transition-all shadow-sm focus:outline-none"
            >
              <LogOut className="h-4 w-4 shrink-0" />
              <span className="hidden sm:inline">Logout</span>
            </button>
          </div>
        </header>

        {/* Tab Contents */}
        <section className="flex-1 p-3 sm:p-4 lg:p-6 overflow-y-auto overflow-x-hidden">
          {/* TAB 1: MARKET DEMAND FORECASTING */}
          {activeTab === 'demand' && (
            <div className="space-y-4 sm:space-y-6 max-w-full">

              {/* ── SEARCH SKILL / JOB DEMAND ── */}
              <div className="bg-gradient-to-br from-brand/[0.03] via-white to-blue-50/50 p-4 sm:p-6 rounded-xl border border-brand/10 shadow-sm">
                <div className="flex items-start sm:items-center space-x-2 mb-4">
                  <div className="p-2 bg-brand/10 rounded-lg shrink-0">
                    <Search className="h-4 w-4 text-brand" />
                  </div>
                  <div className="min-w-0">
                    <h2 className="text-base font-bold text-gray-900">Search Jobs or Skills</h2>
                    <p className="text-xs text-gray-500 mt-0.5 leading-relaxed">
                      Use any job title, skill, or keyword — results apply to both Live Job Listings and Future Job Market Demand Forecasting
                    </p>
                  </div>
                </div>

                {/* Search Input */}
                <form onSubmit={searchSkillDemand} className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-3">
                  <div className="relative flex-1 min-w-0">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                    <input
                      type="text"
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      placeholder='Try "AI Engineer", "Python", "AWS"...'
                      className="w-full pl-10 pr-4 py-2.5 text-sm bg-white border border-gray-200 rounded-lg focus:ring-2 focus:ring-brand/20 focus:border-brand/40 outline-none transition-all placeholder:text-gray-400"
                    />
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <button
                      type="submit"
                      disabled={searchLoading}
                      className="flex-1 sm:flex-none justify-center px-5 py-2.5 bg-brand text-white text-sm font-semibold rounded-lg hover:bg-brand-dark transition-all shadow-sm disabled:opacity-50 flex items-center space-x-1.5"
                    >
                      {searchLoading ? (
                        <RefreshCw className="h-4 w-4 animate-spin" />
                      ) : (
                        <Search className="h-4 w-4" />
                      )}
                      <span>{searchLoading ? 'Searching...' : 'Search'}</span>
                    </button>
                    {hasSearched && (
                      <button
                        type="button"
                        onClick={clearSearch}
                        className="px-3 py-2.5 text-sm font-medium text-gray-500 hover:text-gray-700 border border-gray-200 rounded-lg hover:bg-gray-50 transition-all"
                      >
                        Clear
                      </button>
                    )}
                  </div>
                </form>

                {searchError && (
                  <div className="mt-3 flex items-center space-x-2 text-xs text-red-600 bg-red-50 px-3 py-2 rounded-lg border border-red-100">
                    <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
                    <span>{searchError}</span>
                  </div>
                )}

                {/* ── Search Results ── */}
                {searchResult && (
                  <div className="mt-5 space-y-4 animate-in fade-in" style={{ animation: 'fadeSlideIn 0.4s ease-out' }}>
                    {/* Result Header */}
                    <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                      <span className="text-sm font-bold text-gray-900">Results for</span>
                      <span className="px-2.5 py-0.5 bg-brand/10 text-brand text-xs font-bold rounded-full break-all">"{searchResult.query}"</span>
                      {searchResult.matched_skill_category && (
                        <span className="text-xs text-gray-400">→ mapped to <span className="font-semibold text-gray-600">{searchResult.matched_skill_category}</span></span>
                      )}
                    </div>

                    {/* Metrics Cards Row */}
                    {searchResult.matched_skill_category ? (
                      <div className="grid grid-cols-2 lg:grid-cols-4 gap-2.5 sm:gap-3">
                        {/* Current Demand */}
                        <div className="bg-white rounded-lg border border-gray-100 p-3.5 shadow-sm">
                          <div className="flex items-center space-x-1.5 mb-1.5">
                            <BarChart3 className="h-3.5 w-3.5 text-blue-500" />
                            <span className="text-[10px] font-semibold text-gray-400 uppercase">Current Demand</span>
                          </div>
                          <span className="text-xl font-extrabold text-gray-900">{searchResult.current_demand_index}</span>
                          <span className="text-[10px] text-gray-400 ml-1">/ 150 index</span>
                        </div>

                        {/* YoY Growth */}
                        <div className="bg-white rounded-lg border border-gray-100 p-3.5 shadow-sm">
                          <div className="flex items-center space-x-1.5 mb-1.5">
                            <TrendingUp className="h-3.5 w-3.5 text-emerald-500" />
                            <span className="text-[10px] font-semibold text-gray-400 uppercase">YoY Growth</span>
                          </div>
                          <span className={`text-xl font-extrabold ${searchResult.yoy_growth_percent > 0 ? 'text-emerald-600' : searchResult.yoy_growth_percent < 0 ? 'text-red-600' : 'text-gray-600'}`}>
                            {searchResult.yoy_growth_percent > 0 ? '+' : ''}{searchResult.yoy_growth_percent}%
                          </span>
                        </div>

                        {/* Demand Status */}
                        <div className="bg-white rounded-lg border border-gray-100 p-3.5 shadow-sm">
                          <div className="flex items-center space-x-1.5 mb-1.5">
                            <Zap className="h-3.5 w-3.5 text-amber-500" />
                            <span className="text-[10px] font-semibold text-gray-400 uppercase">Status</span>
                          </div>
                          <span className={`text-sm font-bold ${searchResult.demand_status === 'High & Growing' ? 'text-emerald-600' :
                              searchResult.demand_status === 'Declining' ? 'text-red-600' : 'text-amber-600'
                            }`}>
                            {searchResult.demand_status}
                          </span>
                        </div>

                        {/* 2029 Forecast */}
                        <div className="bg-white rounded-lg border border-gray-100 p-3.5 shadow-sm">
                          <div className="flex items-center space-x-1.5 mb-1.5">
                            <ArrowUpRight className="h-3.5 w-3.5 text-indigo-500" />
                            <span className="text-[10px] font-semibold text-gray-400 uppercase">2029 Forecast</span>
                          </div>
                          <span className="text-xl font-extrabold text-gray-900">{searchResult.forecast_2029_index}</span>
                          <span className={`text-[10px] ml-1 font-semibold ${searchResult.forecast_growth_percent > 0 ? 'text-emerald-600' : 'text-red-600'
                            }`}>
                            ({searchResult.forecast_growth_percent > 0 ? '+' : ''}{searchResult.forecast_growth_percent}%)
                          </span>
                        </div>
                      </div>
                    ) : (
                      <div className="bg-amber-50 border border-amber-100 rounded-lg p-4 text-xs text-amber-700 flex items-start space-x-2">
                        <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
                        <div>
                          <span className="font-bold">No trend data found</span> for "{searchResult.query}". This skill is not currently tracked in our demand index.
                          {searchResult.related_jobs_count > 0 && <span> However, we found <span className="font-bold">{searchResult.related_jobs_count} related job(s)</span> below.</span>}
                        </div>
                      </div>
                    )}

                    {/* Trend Mini-Chart */}
                    {(searchResult.trend_timeline || []).length > 0 && (
                      <div className="bg-white rounded-lg border border-gray-100 p-3 sm:p-4 shadow-sm">
                        <h4 className="text-xs font-bold text-gray-700 mb-3 flex items-start sm:items-center space-x-1.5">
                          <BarChart3 className="h-3.5 w-3.5 text-brand shrink-0 mt-0.5 sm:mt-0" />
                          <span>Demand Trend for {searchResult.matched_skill_category} (2022 – 2029)</span>
                        </h4>
                        {(() => {
                          const maxVal = 150
                          const barMaxH = 120 // max bar height in px
                          return (
                            <div className="overflow-x-auto -mx-1 px-1 pb-1">
                              <div className="relative pl-8 min-w-[420px]">
                                {/* Y-axis labels */}
                                <div className="absolute left-0 top-0 flex flex-col justify-between text-[9px] text-gray-400 font-medium select-none" style={{ height: `${barMaxH}px` }}>
                                  <span>150</span>
                                  <span>100</span>
                                  <span>50</span>
                                  <span>0</span>
                                </div>
                                {/* Horizontal grid lines */}
                                <div className="absolute left-8 right-0 top-0" style={{ height: `${barMaxH}px` }}>
                                  {[0, 1, 2, 3].map(i => (
                                    <div key={i} className="absolute w-full border-t border-gray-100" style={{ top: `${(i / 3) * 100}%` }} />
                                  ))}
                                </div>
                                {/* Bars */}
                                <div className="flex items-end justify-around border-b border-gray-200" style={{ height: `${barMaxH}px` }}>
                                  {searchResult.trend_timeline.map((point, i) => {
                                    const barH = Math.max(4, (point.value / maxVal) * barMaxH)
                                    return (
                                      <div key={i} className="flex flex-col items-center group relative" style={{ flex: 1 }}>
                                        {/* Value label */}
                                        <div className="text-[9px] font-bold text-brand mb-1 select-none">{point.value}</div>
                                        {/* Bar */}
                                        <div
                                          style={{ height: `${barH}px` }}
                                          className={`w-4 sm:w-5 md:w-6 rounded-t transition-all duration-500 hover:scale-105 cursor-default ${point.is_forecast
                                              ? 'bg-gradient-to-t from-brand/30 to-brand/50 border border-dashed border-brand/50'
                                              : 'bg-gradient-to-t from-brand to-brand-light'
                                            }`}
                                          title={`${point.year}: ${point.value}`}
                                        />
                                      </div>
                                    )
                                  })}
                                </div>
                                {/* Year labels */}
                                <div className="flex justify-around mt-1.5">
                                  {searchResult.trend_timeline.map((point, i) => (
                                    <div key={i} className="flex flex-col items-center" style={{ flex: 1 }}>
                                      <span className={`text-[10px] font-bold ${point.is_forecast ? 'text-blue-600' : 'text-gray-700'}`}>{point.year}</span>
                                      {point.is_forecast && <span className="text-[8px] text-blue-500 font-semibold uppercase leading-tight">Forecast</span>}
                                    </div>
                                  ))}
                                </div>
                              </div>
                            </div>
                          )
                        })()}
                        <div className="flex items-center justify-center flex-wrap gap-3 sm:gap-4 mt-3 text-[10px] text-gray-400">
                          <div className="flex items-center space-x-1.5"><span className="h-2.5 w-5 rounded bg-gradient-to-t from-brand to-brand-light inline-block"></span><span>Historical</span></div>
                          <div className="flex items-center space-x-1.5"><span className="h-2.5 w-5 rounded bg-brand/40 border border-dashed border-brand/50 inline-block"></span><span>Forecasted</span></div>
                        </div>
                      </div>
                    )}

                    {/* Supply-Demand Gap */}
                    {searchResult.supply_demand_gap && (
                      <div className="bg-white rounded-lg border border-gray-100 p-4 shadow-sm">
                        <h4 className="text-xs font-bold text-gray-700 mb-3 flex items-center space-x-1.5">
                          <Layers className="h-3.5 w-3.5 text-orange-500" />
                          <span>Supply vs Demand Gap — {searchResult.supply_demand_gap.skill}</span>
                        </h4>
                        <div className="grid grid-cols-3 gap-2 sm:gap-3">
                          <div className="text-center">
                            <div className="text-lg font-extrabold text-blue-600">{searchResult.supply_demand_gap.demand}%</div>
                            <div className="text-[10px] text-gray-400 font-semibold uppercase">Market Demand</div>
                          </div>
                          <div className="text-center">
                            <div className="text-lg font-extrabold text-emerald-600">{searchResult.supply_demand_gap.supply}%</div>
                            <div className="text-[10px] text-gray-400 font-semibold uppercase">Talent Supply</div>
                          </div>
                          <div className="text-center">
                            <div className="text-lg font-extrabold text-red-600">{searchResult.supply_demand_gap.gap}%</div>
                            <div className="text-[10px] text-gray-400 font-semibold uppercase">Shortage Gap</div>
                          </div>
                        </div>
                        <div className="mt-3 h-2.5 bg-gray-100 rounded-full overflow-hidden">
                          <div className="h-full rounded-full bg-gradient-to-r from-emerald-400 via-amber-400 to-red-500" style={{ width: `${searchResult.supply_demand_gap.gap}%` }}></div>
                        </div>
                        <p className="text-[10px] text-gray-400 mt-1.5">A higher gap means more opportunity — employers are struggling to find talent.</p>
                      </div>
                    )}

                    {/* Related Jobs */}
                    {demandSubView === 'forecast' && (searchResult.related_jobs || []).length > 0 && (
                      <div className="bg-white rounded-lg border border-gray-100 p-4 shadow-sm">
                        <h4 className="text-xs font-bold text-gray-700 mb-3 flex items-center space-x-1.5">
                          <Briefcase className="h-3.5 w-3.5 text-brand" />
                          <span>Related Open Positions ({searchResult.related_jobs.length})</span>
                        </h4>
                        <div className="space-y-2">
                          {searchResult.related_jobs.map((job, i) => (
                            <div key={i} className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 px-3 py-2.5 bg-gray-50 rounded-lg border border-gray-100 hover:border-brand/20 hover:bg-brand/[0.02] transition-all group">
                              <div className="flex-1 min-w-0">
                                <div className="text-xs font-bold text-gray-800 group-hover:text-brand transition-colors truncate">{job.title}</div>
                                <div className="text-[10px] text-gray-500 flex flex-wrap items-center gap-x-2 gap-y-0.5 mt-0.5">
                                  <span>{job.company}</span>
                                  <span className="text-gray-300 hidden sm:inline">•</span>
                                  <span className="flex items-center"><MapPin className="h-2.5 w-2.5 mr-0.5 shrink-0" />{job.location}</span>
                                  <span className="text-gray-300 hidden sm:inline">•</span>
                                  <span className="font-medium text-emerald-600">{job.salary}</span>
                                </div>
                              </div>
                              <span className="self-start sm:self-center text-[9px] px-2 py-0.5 bg-blue-50 text-blue-600 rounded-full font-semibold shrink-0">{job.platform}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Switch between Live Job Listings and Demand Forecasting */}
              <div className="flex items-center justify-between gap-2 sm:gap-3">
                <div className="flex-1 min-w-0 grid grid-cols-2 p-1 bg-gray-100 rounded-xl border border-gray-200">
                  <button
                    type="button"
                    onClick={() => setDemandSubView('listings')}
                    className={`flex items-center justify-center gap-1.5 sm:gap-2 px-2 sm:px-4 py-2 text-xs sm:text-sm font-semibold rounded-lg transition-all min-w-0 ${demandSubView === 'listings'
                        ? 'bg-white text-brand shadow-sm'
                        : 'text-gray-500 hover:text-gray-800'
                      }`}
                  >
                    <Briefcase className="h-4 w-4 shrink-0" />
                    <span className="sm:hidden">Live Jobs</span>
                    <span className="hidden sm:inline truncate">Live Job Listings</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setDemandSubView('forecast')}
                    className={`flex items-center justify-center gap-1.5 sm:gap-2 px-2 sm:px-4 py-2 text-xs sm:text-sm font-semibold rounded-lg transition-all min-w-0 ${demandSubView === 'forecast'
                        ? 'bg-white text-brand shadow-sm'
                        : 'text-gray-500 hover:text-gray-800'
                      }`}
                  >
                    <TrendingUp className="h-4 w-4 shrink-0" />
                    <span className="sm:hidden">Forecast</span>
                    <span className="hidden sm:inline lg:hidden truncate">Demand Forecast</span>
                    <span className="hidden lg:inline truncate">Future Job Market Demand Forecasting</span>
                  </button>
                </div>
                <div className="hidden sm:flex items-center gap-2 shrink-0">
                  <button
                    type="button"
                    onClick={() => setDemandSubView('listings')}
                    disabled={demandSubView === 'listings'}
                    aria-label="Show live job listings"
                    className="p-2 rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
                  >
                    <ChevronLeft className="h-4 w-4" />
                  </button>
                  <button
                    type="button"
                    onClick={() => setDemandSubView('forecast')}
                    disabled={demandSubView === 'forecast'}
                    aria-label="Show demand forecasting"
                    className="p-2 rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
                  >
                    <ChevronRight className="h-4 w-4" />
                  </button>
                </div>
              </div>

              {demandSubView === 'listings' && (
                <>
                  {/* ── LIVE JOB LISTINGS FROM AGENTIC PIPELINE ── */}
                  <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
                    {/* Section header */}
                    <div className="px-4 sm:px-6 py-4 bg-gradient-to-r from-brand/5 to-indigo-50/60 border-b border-gray-100 flex flex-col lg:flex-row lg:items-center lg:justify-between gap-3">
                      <div className="flex items-start sm:items-center space-x-3 min-w-0">
                        <div className="p-2 bg-brand/10 rounded-lg shrink-0">
                          <Briefcase className="h-4 w-4 text-brand" />
                        </div>
                        <div className="min-w-0">
                          <h2 className="text-base font-bold text-gray-900 flex flex-wrap items-center gap-2">
                            Live Job Listings
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 text-[10px] font-bold bg-emerald-100 text-emerald-700 rounded-full animate-pulse">
                              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 inline-block"></span>
                              Real-Time
                            </span>
                          </h2>
                          <p className="text-xs text-gray-500 mt-0.5 leading-relaxed">
                            Personalized for <span className="font-semibold text-brand">{user.target_role || 'your target role'}</span> — sourced from LinkedIn &amp; TopJobs via AI pipeline
                          </p>
                        </div>
                      </div>

                      {/* Controls row */}
                      <div className="flex items-center gap-2 flex-wrap w-full lg:w-auto">
                        {/* Source filter */}
                        <select
                          value={liveJobsSource}
                          onChange={(e) => { setLiveJobsSource(e.target.value); fetchLiveJobs(1, e.target.value) }}
                          className="flex-1 sm:flex-none min-w-0 text-xs border border-gray-200 rounded-lg px-2.5 py-1.5 bg-white text-gray-600 focus:ring-2 focus:ring-brand/20 outline-none"
                        >
                          <option value="">All Sources</option>
                          <option value="LinkedIn">LinkedIn</option>
                          <option value="TopJobs">TopJobs</option>
                        </select>

                        {/* Refresh button */}
                        <button
                          onClick={() => fetchLiveJobs(1, liveJobsSource)}
                          disabled={liveJobsLoading}
                          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-brand border border-brand/20 bg-brand/5 rounded-lg hover:bg-brand/10 transition-all disabled:opacity-50"
                        >
                          <RefreshCw className={`h-3.5 w-3.5 ${liveJobsLoading ? 'animate-spin' : ''}`} />
                          Refresh
                        </button>

                        {/* Pipeline trigger button */}
                        <button
                          onClick={triggerPipeline}
                          disabled={pipelineTriggerLoading || pipelineStatus === 'triggered'}
                          title="Run full 4-agent pipeline to collect & process fresh job data"
                          className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg transition-all ${pipelineStatus === 'triggered'
                              ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                              : 'bg-brand text-white hover:bg-brand-dark shadow-sm'
                            } disabled:opacity-60`}
                        >
                          <Zap className="h-3.5 w-3.5 shrink-0" />
                          {pipelineStatus === 'triggered' ? 'Running…' : <><span className="sm:hidden">Pipeline</span><span className="hidden sm:inline">Run AI Pipeline</span></>}
                        </button>
                      </div>
                    </div>

                    {/* Pipeline status banner */}
                    {pipelineStatus === 'triggered' && (
                      <div className="mx-4 sm:mx-6 mt-4 px-3 sm:px-4 py-3 bg-blue-50 border border-blue-100 rounded-lg flex items-start gap-3 text-xs text-blue-700">
                        <RefreshCw className="h-4 w-4 shrink-0 mt-0.5 animate-spin" />
                        <div>
                          <p className="font-bold">Autonomous Pipeline Running</p>
                          <p className="text-blue-600 mt-0.5">Data Collection Agent → NLP Extraction Agent → Skill Processing Agent are operating in background. New listings will appear within ~30 seconds.</p>
                        </div>
                      </div>
                    )}
                    {pipelineStatus === 'error' && (
                      <div className="mx-4 sm:mx-6 mt-4 px-3 sm:px-4 py-3 bg-red-50 border border-red-100 rounded-lg flex items-center gap-2 text-xs text-red-600">
                        <AlertTriangle className="h-4 w-4 shrink-0" />
                        Pipeline trigger failed. Please ensure the backend is running and try again.
                      </div>
                    )}

                    {/* Body */}
                    <div className="p-4 sm:p-6">
                      {liveJobsLoading && liveJobs.length === 0 ? (
                        <div className="flex flex-col items-center justify-center py-16 text-gray-400 space-y-3">
                          <RefreshCw className="h-8 w-8 animate-spin text-brand/40" />
                          <p className="text-sm font-medium">Fetching live job listings…</p>
                        </div>
                      ) : liveJobsError ? (
                        <div className="flex flex-col items-center justify-center py-12 text-center space-y-4">
                          <div className="p-3 bg-amber-50 rounded-full">
                            <AlertTriangle className="h-6 w-6 text-amber-500" />
                          </div>
                          <div>
                            <p className="text-sm font-semibold text-gray-700">No live listings yet</p>
                            <p className="text-xs text-gray-400 mt-1">{liveJobsError}</p>
                          </div>
                          <button
                            onClick={triggerPipeline}
                            className="flex items-center gap-2 px-4 py-2 bg-brand text-white text-sm font-semibold rounded-lg hover:bg-brand-dark transition-all shadow-sm"
                          >
                            <Zap className="h-4 w-4" />
                            Start Data Collection Pipeline
                          </button>
                        </div>
                      ) : liveJobs.length === 0 ? (
                        <div className="flex flex-col items-center justify-center py-12 text-center space-y-4">
                          <div className="p-3 bg-gray-50 rounded-full">
                            <Briefcase className="h-6 w-6 text-gray-300" />
                          </div>
                          <div>
                            <p className="text-sm font-semibold text-gray-700">
                              {hasSearched && searchQuery.trim()
                                ? `No listings match “${searchQuery.trim()}”`
                                : 'No job listings collected yet'}
                            </p>
                            <p className="text-xs text-gray-400 mt-1">
                              {hasSearched && searchQuery.trim()
                                ? 'Try another job title or skill keyword, or clear search to return to recommended roles.'
                                : 'Trigger the AI pipeline to collect live job posts from LinkedIn & TopJobs for your target role.'}
                            </p>
                          </div>
                          {!(hasSearched && searchQuery.trim()) && (
                            <button
                              onClick={triggerPipeline}
                              disabled={pipelineTriggerLoading}
                              className="flex items-center gap-2 px-4 py-2 bg-brand text-white text-sm font-semibold rounded-lg hover:bg-brand-dark transition-all shadow-sm disabled:opacity-60"
                            >
                              <Zap className="h-4 w-4" />
                              {pipelineTriggerLoading ? 'Starting…' : 'Run AI Pipeline Now'}
                            </button>
                          )}
                        </div>
                      ) : (
                        <>
                          {/* Stats row */}
                          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1 mb-4">
                            <p className="text-xs text-gray-500 break-words">
                              <span className="font-bold text-gray-800">{liveJobsTotal}</span> matching positions found for{' '}
                              <span className="font-semibold text-brand">
                                {hasSearched && searchQuery.trim() ? `"${searchQuery.trim()}"` : user.target_role}
                              </span>
                              {liveJobsSource && <span className="ml-1 text-gray-400">from {liveJobsSource}</span>}
                            </p>
                            <span className="text-[10px] text-gray-400 shrink-0">Ranked by skill match</span>
                          </div>

                          {/* Job cards */}
                          <div className="space-y-3">
                            {liveJobs.map((job, idx) => (
                              <div
                                key={job.job_id || idx}
                                className="group relative flex flex-col sm:flex-row sm:items-start gap-4 p-4 rounded-xl border border-gray-100 hover:border-brand/25 hover:shadow-md bg-white transition-all duration-200"
                              >
                                {/* Skill match badge */}
                                {job.skill_match_count > 0 && (
                                  <div className="absolute top-3 right-3 flex items-center gap-1 px-2 py-0.5 bg-emerald-50 text-emerald-700 rounded-full text-[10px] font-bold">
                                    <CheckCircle2 className="h-3 w-3" />
                                    <span className="hidden sm:inline">{job.skill_match_count} skills matched</span>
                                    <span className="sm:hidden">{job.skill_match_count}</span>
                                  </div>
                                )}

                                {/* Company initials avatar */}
                                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-brand/20 to-indigo-100 flex items-center justify-center text-sm font-extrabold text-brand shrink-0">
                                  {(job.company || 'Co').charAt(0).toUpperCase()}
                                </div>

                                {/* Content */}
                                <div className="flex-1 min-w-0">
                                  <div className="flex items-start justify-between gap-2 pr-12 sm:pr-28">
                                    <div className="min-w-0">
                                      <h4 className="text-sm font-bold text-gray-900 group-hover:text-brand transition-colors leading-tight break-words">
                                        {job.title}
                                      </h4>
                                      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-1 text-xs text-gray-500">
                                        <span className="font-medium text-gray-700">{job.company}</span>
                                        <span className="flex items-center gap-0.5">
                                          <MapPin className="h-3 w-3 shrink-0" />
                                          {job.location}
                                        </span>
                                        {job.seniority_level && (
                                          <span className="px-1.5 py-0.5 bg-indigo-50 text-indigo-600 rounded-full text-[10px] font-semibold">
                                            {job.seniority_level}
                                          </span>
                                        )}
                                      </div>
                                    </div>
                                  </div>

                                  {/* Description snippet */}
                                  {job.description_snippet && (
                                    <p className="mt-2 text-xs text-gray-500 leading-relaxed line-clamp-2">
                                      {job.description_snippet}
                                    </p>
                                  )}

                                  {/* Skill overlap badges */}
                                  {job.skill_overlap && job.skill_overlap.length > 0 && (
                                    <div className="mt-2.5 flex flex-wrap gap-1.5">
                                      {job.skill_overlap.slice(0, 6).map((sk, si) => (
                                        <span key={si} className="px-2 py-0.5 bg-brand/8 text-brand text-[10px] font-semibold rounded-full border border-brand/15">
                                          ✓ {sk}
                                        </span>
                                      ))}
                                      {job.skill_overlap.length > 6 && (
                                        <span className="text-[10px] text-gray-400">+{job.skill_overlap.length - 6} more</span>
                                      )}
                                    </div>
                                  )}

                                  {/* Footer row */}
                                  <div className="mt-3 flex items-center justify-between flex-wrap gap-2">
                                    <div className="flex items-center gap-2">
                                      {/* Source badge */}
                                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${job.source === 'LinkedIn'
                                          ? 'bg-blue-100 text-blue-700'
                                          : 'bg-orange-100 text-orange-700'
                                        }`}>
                                        {job.source}
                                      </span>
                                      {job.posted_date_text && (
                                        <span className="text-[10px] text-gray-400">{job.posted_date_text}</span>
                                      )}
                                    </div>
                                    <a
                                      href={job.job_link}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className="flex items-center gap-1 text-xs font-semibold text-brand hover:text-brand-dark transition-colors"
                                    >
                                      View Job <ExternalLink className="h-3 w-3" />
                                    </a>
                                  </div>
                                </div>
                              </div>
                            ))}
                          </div>

                          {/* Pagination */}
                          {liveJobsTotal > 15 && (
                            <div className="mt-5 flex items-center justify-center gap-2 sm:gap-3 flex-wrap">
                              <button
                                onClick={() => fetchLiveJobs(liveJobsPage - 1, liveJobsSource)}
                                disabled={liveJobsPage <= 1 || liveJobsLoading}
                                className="px-3 py-1.5 text-xs font-semibold border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-40 transition-all"
                              >
                                ← Previous
                              </button>
                              <span className="text-xs text-gray-500">
                                Page {liveJobsPage} · {Math.ceil(liveJobsTotal / 15)} total
                              </span>
                              <button
                                onClick={() => fetchLiveJobs(liveJobsPage + 1, liveJobsSource)}
                                disabled={liveJobsPage * 15 >= liveJobsTotal || liveJobsLoading}
                                className="px-3 py-1.5 text-xs font-semibold border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-40 transition-all"
                              >
                                Next →
                              </button>
                            </div>
                          )}
                        </>
                      )}
                    </div>
                  </div>
                </>
              )}

              {demandSubView === 'forecast' && (
                <>
                  <div className="bg-white p-4 sm:p-6 rounded-xl border border-gray-200 shadow-sm">
                    <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-3 mb-5 sm:mb-6">
                      <div className="min-w-0">
                        <h2 className="text-base font-bold text-gray-900">Future Job Market Demand Forecasting</h2>
                        <p className="text-xs text-gray-500 mt-1 leading-relaxed">Predictions on tech demand index calculated from LinkedIn, Indeed, and TopJobs.lk</p>
                      </div>
                      <div className="flex flex-col sm:flex-row sm:items-center gap-1.5 sm:gap-2 text-xs w-full sm:w-auto">
                        <span className="text-gray-500 font-medium shrink-0">Forecast Horizon</span>
                        <select
                          value={forecastHorizon}
                          onChange={(e) => setForecastHorizon(e.target.value)}
                          className="w-full sm:w-auto border border-gray-300 rounded-lg px-2.5 py-1.5 bg-white text-gray-700 focus:ring-2 focus:ring-brand/20 outline-none"
                        >
                          <option value="2027">1-Year Outlook (2027)</option>
                          <option value="2028">2-Year Outlook (2028)</option>
                          <option value="2029">3-Year Outlook (2029)</option>
                        </select>
                      </div>
                    </div>

                  </div>
                  <DemandInsightsPanel
                    insights={demandInsights}
                    isLoading={demandInsightsLoading}
                    error={demandInsightsError}
                    onRetry={fetchDemandForecast}
                    onCollect={triggerPipeline}
                    canCollect={Boolean(user.target_role)}
                  />
                </>
              )}

            </div>
          )}

          {/* TAB 2: SKILL GAP DISCOVERY */}
          {activeTab === 'gap' && (
            <div className="space-y-6">
              <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
                <h2 className="text-base font-bold text-gray-900">Skill Gap Discovery & Target Alignment</h2>
                <p className="text-xs text-gray-500 mt-1 mb-5">
                  Search for a specific job title or role to dynamically analyze your current skills against its requirements.
                </p>
                <form
                  onSubmit={(e) => { e.preventDefault(); fetchGapAnalysis(gapSearchQuery || user.target_role); }}
                  className="flex items-center gap-3"
                >
                  <div className="relative flex-1">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                    <input
                      type="text"
                      value={gapSearchQuery}
                      onChange={(e) => setGapSearchQuery(e.target.value)}
                      placeholder={`Try searching for roles like "Data Scientist", "Backend Developer"... (Current Target: ${user.target_role})`}
                      className="w-full pl-10 pr-4 py-2.5 text-sm bg-gray-50 border border-gray-200 rounded-lg focus:ring-2 focus:ring-brand/20 focus:border-brand/40 outline-none transition-all placeholder:text-gray-400"
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={isSearchingGap}
                    className="px-5 py-2.5 bg-brand text-white text-sm font-semibold rounded-lg hover:bg-brand-dark transition-all shadow-sm disabled:opacity-50 flex items-center space-x-1.5"
                  >
                    {isSearchingGap ? (
                      <RefreshCw className="h-4 w-4 animate-spin" />
                    ) : (
                      <Search className="h-4 w-4" />
                    )}
                    <span>{isSearchingGap ? 'Analyzing...' : 'Analyze Role'}</span>
                  </button>
                  {gapSearchQuery && (
                    <button
                      type="button"
                      onClick={() => { setGapSearchQuery(''); fetchGapAnalysis(user.target_role); }}
                      className="px-3 py-2.5 text-sm font-medium text-gray-500 hover:text-gray-700 border border-gray-200 rounded-lg hover:bg-gray-50 transition-all"
                    >
                      Reset
                    </button>
                  )}
                </form>
              </div>

              {gapData ? (
                <>
                  {/* Progress Gauge */}
                  <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm flex flex-col md:flex-row items-center gap-8">
                    <div className="relative flex items-center justify-center shrink-0">
                      {/* Simple SVG circle gauge */}
                      <svg className="w-32 h-32 transform -rotate-90">
                        <circle cx="64" cy="64" r="50" stroke="#f3f4f6" strokeWidth="10" fill="transparent" />
                        <circle cx="64" cy="64" r="50" stroke="#002855" strokeWidth="10" fill="transparent"
                          strokeDasharray={314}
                          strokeDashoffset={314 - (314 * gapData.match_percentage) / 100}
                          className="transition-all duration-1000 ease-out"
                        />
                      </svg>
                      <div className="absolute text-center">
                        <span className="text-2xl font-extrabold text-brand">{gapData.match_percentage}%</span>
                        <span className="block text-[10px] text-gray-400 font-semibold uppercase mt-0.5">Compatible</span>
                      </div>
                    </div>

                    <div className="flex-1">
                      <h2 className="text-base font-bold text-gray-900">
                        Skill Fit Diagnostics for target role: <span className="text-brand">{gapData.target_role}</span>
                      </h2>
                      <p className="text-xs text-gray-500 mt-1">Based on comparison of your CV/profile skills vs aggregate requirements scraped from TopJobs, Indeed, and LinkedIn.</p>

                      <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <div className="bg-emerald-50/50 border border-emerald-100 rounded-lg p-3">
                          <span className="text-[11px] font-bold text-emerald-800 uppercase block mb-2">✔️ Matching Skills ({gapData.matching_skills.length})</span>
                          <div className="flex flex-wrap gap-1">
                            {gapData.matching_skills.map((s, i) => (
                              <span key={i} className="px-2 py-0.5 bg-emerald-100 text-emerald-800 border border-emerald-200 text-xs font-semibold rounded">
                                {s}
                              </span>
                            ))}
                            {gapData.matching_skills.length === 0 && <span className="text-xs text-gray-400 italic">No skills match yet.</span>}
                          </div>
                        </div>
                        <div className="bg-red-50/50 border border-red-100 rounded-lg p-3">
                          <span className="text-[11px] font-bold text-red-800 uppercase block mb-2">❌ Missing Skills ({gapData.missing_skills.length})</span>
                          <div className="flex flex-wrap gap-1">
                            {gapData.missing_skills.map((s, i) => (
                              <span key={i} className="px-2 py-0.5 bg-red-100 text-red-800 border border-red-200 text-xs font-semibold rounded">
                                {s}
                              </span>
                            ))}
                            {gapData.missing_skills.length === 0 && <span className="text-xs text-green-700 italic">You match all requirements!</span>}
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Skill Knowledge Graph */}
                  {gapData.graph_data && (
                    <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm flex flex-col">
                      <h3 className="text-sm font-bold text-gray-900 mb-2 flex items-center space-x-2">
                        <span>Skill Relationship Knowledge Graph</span>
                      </h3>
                      <p className="text-xs text-gray-500 mb-4">Visual mapping of your CV skills and aliases compared to the target role requirements.</p>

                      <div ref={graphContainerRef} className="w-full h-[400px] rounded-lg border border-gray-100 bg-gray-50 overflow-hidden relative flex items-center justify-center">
                        <ForceGraph2D
                          width={graphWidth}
                          height={400}
                          graphData={gapData.graph_data}
                          nodeAutoColorBy="group"
                          nodeLabel="name"
                          nodeCanvasObject={(node, ctx, globalScale) => {
                            const label = node.name;
                            const fontSize = 12 / globalScale;
                            ctx.font = `${fontSize}px Sans-Serif`;
                            const textWidth = ctx.measureText(label).width;
                            const bckgDimensions = [textWidth, fontSize].map(n => n + fontSize * 0.2);

                            ctx.fillStyle = 'rgba(255, 255, 255, 0.9)';
                            ctx.fillRect(node.x - bckgDimensions[0] / 2, node.y - bckgDimensions[1] / 2, ...bckgDimensions);

                            ctx.textAlign = 'center';
                            ctx.textBaseline = 'middle';

                            if (node.group === 'candidate' || node.group === 'target') {
                              ctx.fillStyle = '#002855'; // brand
                            } else if (node.group === 'matched_skill') {
                              ctx.fillStyle = '#059669'; // emerald
                            } else if (node.group === 'missing_skill') {
                              ctx.fillStyle = '#dc2626'; // red
                            } else {
                              ctx.fillStyle = '#2563eb'; // blue
                            }

                            ctx.fillText(label, node.x, node.y);
                            node.__bckgDimensions = bckgDimensions;
                          }}
                          nodePointerAreaPaint={(node, color, ctx) => {
                            ctx.fillStyle = color;
                            const bckgDimensions = node.__bckgDimensions;
                            bckgDimensions && ctx.fillRect(node.x - bckgDimensions[0] / 2, node.y - bckgDimensions[1] / 2, ...bckgDimensions);
                          }}
                          linkColor={() => '#cbd5e1'}
                          linkDirectionalArrowLength={3.5}
                          linkDirectionalArrowRelPos={1}
                        />
                      </div>
                    </div>
                  )}

                  {/* Recommended Skill Roadmap */}
                  {gapData.skill_roadmap && gapData.skill_roadmap.length > 0 && (
                    <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm flex flex-col mt-6">
                      <h3 className="text-sm font-bold text-gray-900 mb-2 flex items-center space-x-2">
                        <Milestone className="h-4 w-4 text-brand" />
                        <span>Recommended Skill Acquisition Roadmap</span>
                      </h3>
                      <p className="text-xs text-gray-500 mb-5">Suggested step-by-step learning path to acquire your missing skills effectively, starting from base foundations.</p>

                      <div className="space-y-6 relative border-l-2 border-brand/20 ml-2 pl-6 pt-2 pb-2">
                        {gapData.skill_roadmap.map((phase, idx) => (
                          <div key={idx} className="relative">
                            <div className="absolute -left-[33px] top-0.5 rounded-full bg-white border-2 border-brand h-4 w-4 shadow-[0_0_0_2px_white] flex items-center justify-center">
                              <div className="bg-brand h-1.5 w-1.5 rounded-full"></div>
                            </div>
                            <h4 className="text-xs font-bold text-gray-900">{phase.title}</h4>
                            <div className="flex flex-wrap gap-2 mt-2">
                              {phase.skills.map((s, i) => (
                                <span key={i} className="px-2.5 py-1 bg-brand/5 text-brand border border-brand/10 text-xs font-semibold rounded-md shadow-sm transition-all hover:bg-brand hover:text-white cursor-default">
                                  {s}
                                </span>
                              ))}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                </>
              ) : (
                <div className="h-64 flex items-center justify-center text-sm text-gray-500">Retrieving diagnostics...</div>
              )}
            </div>
          )}

          {/* TAB 3: CAREER PATH PLANNING */}
          {activeTab === 'path' && (
            <div className="space-y-6">
              {/* ─── TWO-COLUMN: Career Path Planner + Salary Insight side by side ─── */}
              <div className="grid grid-cols-1 lg:grid-cols-5 gap-6 items-start">

                {/* LEFT: AI Career Path Timeline (narrower) */}
                <div className="lg:col-span-2">
                  {careerData ? (
                    <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm h-full">
                      <div className="mb-5 border-b border-gray-100 pb-4">
                        <h2 className="text-sm font-bold text-gray-900">
                          AI Career Path Planner: Transition to <span className="text-brand">{careerData.target_role}</span>
                        </h2>
                        <p className="text-xs text-gray-500 mt-1">Est. Duration: <strong>{careerData.estimated_duration}</strong> from <strong>{careerData.current_role}</strong>.</p>
                      </div>

                      {/* Vertical Timeline Roadmap */}
                      <div className="relative border-l-2 border-gray-200 ml-3 pl-6 space-y-6">
                        {careerData.roadmap.map((step, idx) => (
                          <div key={idx} className="relative">
                            {/* Circle dot */}
                            <div className={`absolute -left-[37px] top-0.5 rounded-full border-4 border-white h-6 w-6 flex items-center justify-center text-[10px] font-bold text-white shadow-sm ${step.status === 'completed'
                                ? 'bg-emerald-500'
                                : step.status === 'in-progress'
                                  ? 'bg-indigo-600'
                                  : 'bg-gray-300'
                              }`}>
                              {step.step}
                            </div>

                            <div>
                              <div className="flex items-center flex-wrap gap-2">
                                <h3 className="text-[11px] font-bold text-gray-900 leading-tight">{step.title}</h3>
                                <span className={`px-1.5 py-0.5 rounded-full text-[8px] font-bold border uppercase ${step.status === 'completed'
                                    ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                                    : step.status === 'in-progress'
                                      ? 'bg-indigo-50 text-indigo-700 border-indigo-200'
                                      : 'bg-gray-100 text-gray-400 border-gray-200'
                                  }`}>
                                  {step.status}
                                </span>
                              </div>
                              <p className="text-[10px] text-gray-500 mt-1 leading-relaxed">{step.description}</p>
                              <div className="text-[9px] text-gray-400 mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1">
                                <span>⏱️ <strong>{step.duration}</strong></span>
                                <div className="flex items-center flex-wrap gap-1">
                                  {step.skills_to_acquire.map((sk, i) => (
                                    <span key={i} className="px-1 py-0.5 bg-gray-100 text-gray-600 rounded text-[8px] font-semibold border border-gray-200/50">
                                      {sk}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            </div>
                          </div>
                        ))}

                        {/* Final Step */}
                        <div className="relative">
                          <div className="absolute -left-[37px] top-0.5 rounded-full border-4 border-white h-6 w-6 flex items-center justify-center text-[10px] font-bold text-white bg-brand shadow-sm">
                            ★
                          </div>
                          <div>
                            <h3 className="text-[11px] font-bold text-brand">Career Target Achieved</h3>
                            <p className="text-[10px] text-gray-500 mt-0.5">Ready for placement as <span className="font-semibold">{careerData.target_role}</span>!</p>
                          </div>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="h-64 flex items-center justify-center text-sm text-gray-500 bg-white rounded-xl border border-gray-200">Synthesizing path timeline...</div>
                  )}
                </div>

                {/* RIGHT: Salary Insight & Forecast (wider) */}
                <div className="lg:col-span-3">
                  {salaryData ? (
                    <div className="rounded-xl border border-gray-200 shadow-sm overflow-hidden">
                      {/* Header banner */}
                      <div className="bg-gradient-to-r from-indigo-900 via-indigo-800 to-purple-900 px-6 py-4 flex items-center justify-between">
                        <div>
                          <div className="flex items-center space-x-2 mb-1">
                            <DollarSign className="h-4 w-4 text-indigo-300" />
                            <h3 className="text-sm font-bold text-white">Salary Insight &amp; Forecast</h3>
                          </div>
                          <p className="text-xs text-indigo-300">Unlock your earning potential by gaining the missing skills for <span className="text-white font-semibold">{salaryData.target_role}</span></p>
                        </div>
                        <div className="text-right shrink-0 ml-4">
                          <div className="text-xs text-indigo-400 mb-0.5">Potential Uplift</div>
                          <div className="text-2xl font-black text-emerald-400 tracking-tight">
                            +{salaryData.uplift_pct}%
                          </div>
                          <div className="text-[10px] text-indigo-400">salary increase</div>
                        </div>
                      </div>

                      <div className="bg-white p-5">
                        {/* Current vs Target salary comparison */}
                        <div className="grid grid-cols-2 gap-3 mb-5">
                          <div className="bg-gray-50 rounded-lg p-3 border border-gray-100">
                            <p className="text-[10px] text-gray-500 font-semibold uppercase tracking-wide mb-1">Current Role</p>
                            <p className="text-[11px] font-bold text-gray-700 mb-1.5">{salaryData.current_role}</p>
                            <p className="text-base font-black text-gray-900">LKR {(salaryData.current_salary.median / 1000).toFixed(0)}K</p>
                            <p className="text-[10px] text-gray-500 mt-0.5">{(salaryData.current_salary.min / 1000).toFixed(0)}K – {(salaryData.current_salary.max / 1000).toFixed(0)}K / month</p>
                          </div>
                          <div className="bg-gradient-to-br from-indigo-50 to-purple-50 rounded-lg p-3 border border-indigo-100 relative overflow-hidden">
                            <div className="absolute top-2 right-2">
                              <span className="px-1.5 py-0.5 bg-emerald-100 text-emerald-700 text-[9px] font-bold rounded-full border border-emerald-200">TARGET</span>
                            </div>
                            <p className="text-[10px] text-indigo-500 font-semibold uppercase tracking-wide mb-1">Target Role</p>
                            <p className="text-[11px] font-bold text-indigo-700 mb-1.5">{salaryData.target_role}</p>
                            <p className="text-base font-black text-indigo-900">LKR {(salaryData.target_salary.median / 1000).toFixed(0)}K</p>
                            <p className="text-[10px] text-indigo-500 mt-0.5">{(salaryData.target_salary.min / 1000).toFixed(0)}K – {(salaryData.target_salary.max / 1000).toFixed(0)}K / month</p>
                          </div>
                        </div>

                        {/* Salary uplift bar */}
                        <div className="mb-5">
                          <div className="flex justify-between text-[10px] text-gray-500 mb-1">
                            <span>Current median</span>
                            <span>Target median</span>
                          </div>
                          <div className="relative h-2.5 bg-gray-100 rounded-full overflow-hidden">
                            <div
                              className="absolute left-0 top-0 h-full bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full"
                              style={{ width: `${Math.min(100, Math.round((salaryData.current_salary.median / salaryData.target_salary.max) * 100))}%` }}
                            />
                            <div
                              className="absolute left-0 top-0 h-full bg-gradient-to-r from-emerald-400 to-teal-400 rounded-full opacity-40"
                              style={{ width: `${Math.min(100, Math.round((salaryData.target_salary.median / salaryData.target_salary.max) * 100))}%` }}
                            />
                          </div>
                          <p className="text-[10px] text-emerald-600 font-bold mt-1 text-right">
                            + LKR {(salaryData.salary_uplift / 1000).toFixed(0)}K more per month
                          </p>
                        </div>

                        {/* Per-skill salary boost bars */}
                        {salaryData.skill_impacts && salaryData.skill_impacts.length > 0 && (
                          <div className="mb-5">
                            <p className="text-[10px] font-bold text-gray-700 uppercase tracking-wide mb-2.5 flex items-center space-x-1">
                              <TrendingUp className="h-3 w-3 text-brand" />
                              <span>Salary Boost per Missing Skill</span>
                            </p>
                            <div className="space-y-2">
                              {salaryData.skill_impacts.map((item, idx) => {
                                const maxBoost = salaryData.skill_impacts[0].avg_boost_lkr;
                                const pct = Math.round((item.avg_boost_lkr / maxBoost) * 100);
                                const categoryColor = {
                                  'cutting-edge': 'from-purple-500 to-indigo-500',
                                  'advanced': 'from-indigo-500 to-blue-500',
                                  'cloud': 'from-sky-500 to-cyan-500',
                                  'devops': 'from-teal-500 to-emerald-500',
                                  'foundational': 'from-gray-400 to-gray-500',
                                }[item.category] || 'from-brand to-indigo-500';
                                return (
                                  <div key={idx}>
                                    <div className="flex justify-between items-center mb-0.5">
                                      <div className="flex items-center space-x-1.5">
                                        <span className="text-xs font-semibold text-gray-800">{item.skill}</span>
                                        <span className={`px-1.5 py-0.5 rounded-full text-[8px] font-bold border ${item.category === 'cutting-edge' ? 'bg-purple-50 text-purple-700 border-purple-200'
                                            : item.category === 'advanced' ? 'bg-indigo-50 text-indigo-700 border-indigo-200'
                                              : item.category === 'cloud' ? 'bg-sky-50 text-sky-700 border-sky-200'
                                                : item.category === 'devops' ? 'bg-teal-50 text-teal-700 border-teal-200'
                                                  : 'bg-gray-100 text-gray-600 border-gray-200'
                                          }`}>{item.category}</span>
                                      </div>
                                      <span className="text-[10px] font-bold text-emerald-600">+LKR {(item.avg_boost_lkr / 1000).toFixed(0)}K/mo</span>
                                    </div>
                                    <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                                      <div
                                        className={`h-full bg-gradient-to-r ${categoryColor} rounded-full transition-all duration-500`}
                                        style={{ width: `${pct}%` }}
                                      />
                                    </div>
                                  </div>
                                );
                              })}
                            </div>
                          </div>
                        )}

                        {/* 5-Year salary growth forecast */}
                        {salaryData.yearly_forecast && (
                          <div>
                            <p className="text-[10px] font-bold text-gray-700 uppercase tracking-wide mb-2.5 flex items-center space-x-1">
                              <BarChart3 className="h-3 w-3 text-brand" />
                              <span>5-Year AI Salary Forecast (Sri Lanka Market)</span>
                            </p>
                            <div className="grid grid-cols-5 gap-2">
                              {salaryData.yearly_forecast.map((yr, idx) => {
                                const maxVal = Math.max(...salaryData.yearly_forecast.map(y => y.senior_ai_median));
                                const isCurrentYear = yr.year === 2026;
                                return (
                                  <div key={idx} className="flex flex-col items-center">
                                    <div className="w-full flex flex-col items-center space-y-0.5">
                                      <div className="w-full bg-gray-100 rounded-sm overflow-hidden" style={{ height: '48px' }}>
                                        <div
                                          className="w-full bg-gradient-to-t from-purple-600 to-purple-400 rounded-sm"
                                          style={{ height: `${(yr.senior_ai_median / maxVal) * 100}%`, marginTop: `${100 - (yr.senior_ai_median / maxVal) * 100}%` }}
                                        />
                                      </div>
                                      <div className="w-full bg-gray-100 rounded-sm overflow-hidden" style={{ height: '32px' }}>
                                        <div
                                          className={`w-full rounded-sm ${isCurrentYear ? 'bg-gradient-to-t from-brand to-indigo-400' : 'bg-gradient-to-t from-indigo-500 to-blue-400'}`}
                                          style={{ height: `${(yr.ai_engineer_median / maxVal) * 100}%`, marginTop: `${100 - (yr.ai_engineer_median / maxVal) * 100}%` }}
                                        />
                                      </div>
                                    </div>
                                    <div className={`text-[9px] font-bold mt-1 ${isCurrentYear ? 'text-brand' : 'text-gray-500'}`}>{yr.year}</div>
                                    {isCurrentYear && <div className="text-[8px] text-brand font-bold">NOW</div>}
                                  </div>
                                );
                              })}
                            </div>
                            <div className="flex items-center space-x-4 mt-2">
                              <div className="flex items-center space-x-1">
                                <div className="h-2 w-2 rounded-full bg-purple-500"></div>
                                <span className="text-[9px] text-gray-500">Senior AI</span>
                              </div>
                              <div className="flex items-center space-x-1">
                                <div className="h-2 w-2 rounded-full bg-indigo-500"></div>
                                <span className="text-[9px] text-gray-500">AI Engineer</span>
                              </div>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  ) : (
                    <div className="h-64 flex items-center justify-center text-sm text-gray-500 bg-white rounded-xl border border-gray-200">Loading salary insights...</div>
                  )}
                </div>
              </div>{/* end two-column grid */}

              {/* Course Recommendations */}
              {gapData && (
                <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm mt-6">
                  {/* Title and Scope Switcher */}
                  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-4 gap-3">
                    <div>
                      <h3 className="text-sm font-bold text-gray-900 flex items-center space-x-2">
                        <GraduationCap className="h-4 w-4 text-brand" />
                        <span>Recommended Curated Courses</span>
                      </h3>
                      <p className="text-xs text-gray-500 mt-1">
                        {courseSearchScope === 'recommended'
                          ? "Courses dynamically matched to address your missing skills."
                          : "Explore and search all available courses in the catalog."}
                      </p>
                    </div>

                    {/* Scope toggle pills */}
                    <div className="flex bg-gray-100 p-0.5 rounded-lg text-xs font-semibold shrink-0 self-start sm:self-center">
                      <button
                        type="button"
                        onClick={() => { setCourseSearchScope('recommended'); setCourseSearchQuery(''); }}
                        className={`px-3 py-1.5 rounded-md transition-all ${courseSearchScope === 'recommended'
                            ? 'bg-white text-gray-900 shadow-sm'
                            : 'text-gray-500 hover:text-gray-900'
                          }`}
                      >
                        Recommended
                      </button>
                      <button
                        type="button"
                        onClick={() => { setCourseSearchScope('all'); setCourseSearchQuery(''); }}
                        className={`px-3 py-1.5 rounded-md transition-all ${courseSearchScope === 'all'
                            ? 'bg-white text-gray-900 shadow-sm'
                            : 'text-gray-500 hover:text-gray-900'
                          }`}
                      >
                        All Catalog
                      </button>
                    </div>
                  </div>

                  {/* Search Input Bar */}
                  <div className="mb-4 relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                    <input
                      type="text"
                      value={courseSearchQuery}
                      onChange={(e) => setCourseSearchQuery(e.target.value)}
                      placeholder={
                        courseSearchScope === 'recommended'
                          ? "Filter recommended courses by title, provider, or skills..."
                          : "Search catalog by keyword (e.g. PyTorch, FastAPI, AWS)..."
                      }
                      className="w-full pl-10 pr-10 py-2.5 text-xs bg-gray-50 border border-gray-200 rounded-lg focus:ring-2 focus:ring-brand/20 focus:border-brand/40 outline-none transition-all placeholder:text-gray-400"
                    />
                    {courseSearchQuery && (
                      <button
                        type="button"
                        onClick={() => setCourseSearchQuery('')}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 transition-colors"
                      >
                        <X className="h-4 w-4" />
                      </button>
                    )}
                  </div>

                  {/* Courses List */}
                  <div className="space-y-4">
                    {courseSearchScope === 'all' && isSearchingCourses ? (
                      <div className="flex flex-col items-center justify-center py-8 text-xs text-gray-500">
                        <RefreshCw className="h-5 w-5 animate-spin text-brand mb-2" />
                        <span>Searching course catalog...</span>
                      </div>
                    ) : (() => {
                      const displayedCourses = courseSearchScope === 'recommended'
                        ? (gapData.recommended_courses || []).filter(course => {
                          if (!courseSearchQuery) return true;
                          const q = courseSearchQuery.toLowerCase();
                          return (
                            course.title.toLowerCase().includes(q) ||
                            course.provider.toLowerCase().includes(q) ||
                            course.skills_taught.some(s => s.toLowerCase().includes(q))
                          );
                        })
                        : allCourses;

                      if (displayedCourses.length === 0) {
                        return (
                          <div className="p-6 text-center text-xs text-gray-500 border border-dashed rounded-lg bg-gray-50">
                            {courseSearchScope === 'recommended'
                              ? "No matching recommended courses found for your missing skills."
                              : "No courses found matching that search query in the catalog."}
                          </div>
                        );
                      }

                      return displayedCourses.map((course, idx) => (
                        <div key={idx} className="flex flex-col sm:flex-row justify-between items-start sm:items-center p-4 border border-gray-100 rounded-lg hover:bg-gray-50 transition-colors gap-4">
                          <div className="flex items-start space-x-3">
                            <div className="p-2 bg-blue-50 text-blue-600 rounded mt-1 shrink-0">
                              <BookOpen className="h-4 w-4" />
                            </div>
                            <div>
                              <h4 className="text-xs font-bold text-gray-900">{course.title}</h4>
                              <p className="text-[10px] text-gray-500 mt-0.5">{course.provider} • Duration: {course.duration}</p>
                              <div className="flex flex-wrap gap-1 mt-1.5">
                                {course.skills_taught.map((st, i) => (
                                  <span key={i} className="px-1.5 py-0.5 bg-gray-100 text-gray-600 rounded text-[9px] font-medium border border-gray-200">
                                    Teaches: {st}
                                  </span>
                                ))}
                              </div>
                            </div>
                          </div>
                          <div className="flex items-center space-x-4 self-end sm:self-center shrink-0">
                            <span className="text-xs font-bold text-yellow-600">★ {course.rating}</span>
                            <a
                              href={course.link}
                              target="_blank"
                              rel="noreferrer"
                              className="inline-flex items-center space-x-1 px-3 py-1.5 bg-brand text-white rounded text-xs font-semibold hover:bg-brand-light transition-all"
                            >
                              <span>Enroll Course</span>
                              <ExternalLink className="h-3 w-3" />
                            </a>
                          </div>
                        </div>
                      ));
                    })()}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* TAB 4: SKILL MATCHING AND JOB ALIGNMENT */}
          {activeTab === 'matching' && (
            <div className="space-y-5">
              <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-brand via-brand-dark to-slate-900 p-5 text-white shadow-lg sm:p-7">
                <div className="absolute -right-10 -top-16 h-48 w-48 rounded-full border-[18px] border-white/10" />
                <div className="relative flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
                  <div className="max-w-2xl">
                    <div className="mb-3 flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.2em] text-cyan-200"><Sparkles className="h-3.5 w-3.5" />Personalised job matching</div>
                    <h2 className="text-2xl font-black tracking-tight sm:text-3xl">Find roles that fit your real skills.</h2>
                    <p className="mt-2 max-w-xl text-sm leading-relaxed text-blue-100">We compare your profile with collected job postings and surface the skills that give you the strongest starting point.</p>
                  </div>
                  <div className="grid grid-cols-2 gap-2 sm:gap-3 lg:min-w-[250px]">
                    <div className="rounded-xl border border-white/15 bg-white/10 p-3 backdrop-blur-sm"><p className="text-[10px] font-semibold uppercase text-blue-200">Indexed jobs</p><p className="mt-1 text-2xl font-black">{matchingTotal}</p></div>
                    <div className="rounded-xl border border-white/15 bg-white/10 p-3 backdrop-blur-sm"><p className="text-[10px] font-semibold uppercase text-blue-200">Your skills</p><p className="mt-1 text-2xl font-black">{Array.isArray(user.skills) ? user.skills.length : 0}</p></div>
                  </div>
                </div>
              </div>

              <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm sm:p-5">
                <form onSubmit={(e) => { e.preventDefault(); fetchMatchingJobs(jobSearchQuery, 1, matchingSource) }} className="flex flex-col gap-3 lg:flex-row lg:items-center">
                  <div className="relative min-w-0 flex-1"><Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" /><input type="text" value={jobSearchQuery} onChange={(e) => setJobSearchQuery(e.target.value)} placeholder="Search by role, company, location, or skill" className="w-full rounded-lg border border-gray-200 bg-gray-50 py-2.5 pl-10 pr-4 text-sm outline-none transition-all placeholder:text-gray-400 focus:border-brand/40 focus:ring-2 focus:ring-brand/20" /></div>
                  <div className="flex flex-col gap-2 sm:flex-row">
                    <div className="relative"><Filter className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-gray-400" /><select value={matchingSource} onChange={(e) => { setMatchingSource(e.target.value); fetchMatchingJobs(jobSearchQuery, 1, e.target.value) }} className="w-full appearance-none rounded-lg border border-gray-200 bg-white py-2.5 pl-9 pr-8 text-xs font-semibold text-gray-600 outline-none focus:border-brand/40 focus:ring-2 focus:ring-brand/20 sm:w-36" aria-label="Filter by job source"><option value="">All sources</option><option value="LinkedIn">LinkedIn</option><option value="TopJobs">TopJobs</option></select></div>
                    <button type="submit" disabled={isSearchingJobs} className="flex items-center justify-center gap-1.5 rounded-lg bg-brand px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition-all hover:bg-brand-dark disabled:cursor-not-allowed disabled:opacity-50">{isSearchingJobs ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}{isSearchingJobs ? 'Searching...' : 'Find matches'}</button>
                    {(jobSearchQuery || matchingSource) && <button type="button" onClick={() => { setJobSearchQuery(''); setMatchingSource(''); fetchMatchingJobs('', 1, '') }} className="rounded-lg border border-gray-200 px-3 py-2.5 text-xs font-semibold text-gray-500 transition-all hover:bg-gray-50 hover:text-gray-700">Reset</button>}
                  </div>
                </form>
                <div className="mt-3 flex flex-wrap items-center gap-2 text-[11px] text-gray-400"><Target className="h-3.5 w-3.5 text-brand" /><span>Matching against</span><span className="rounded-full bg-brand/5 px-2 py-0.5 font-semibold text-brand">{user.target_role || 'your target role'}</span><span className="hidden text-gray-300 sm:inline">|</span><span>Ranked by AI relevance score</span></div>
              </div>

              {matchingError && <div className="flex items-start gap-2 rounded-xl border border-amber-200 bg-amber-50 p-4 text-xs text-amber-800"><AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-500" /><div className="flex-1"><p className="font-bold">Matching service unavailable</p><p className="mt-0.5">{matchingError}</p></div><button type="button" onClick={() => fetchMatchingJobs(jobSearchQuery, matchingPage, matchingSource)} className="font-bold text-amber-900 underline">Retry</button></div>}

              {matchingWarmingUp ? (
                <div className="flex flex-col items-center justify-center rounded-xl border border-blue-100 bg-blue-50 py-16 text-center shadow-sm">
                  <RefreshCw className="h-8 w-8 animate-spin text-brand/60" />
                  <p className="mt-3 text-sm font-semibold text-gray-700">Getting the matching engine ready…</p>
                  <p className="mt-1 text-xs text-gray-400">The semantic model is loading at startup — this takes about 20–30 seconds.</p>
                  <p className="mt-2 text-xs text-blue-500 font-medium">Retrying automatically in 15 seconds…</p>
                </div>
              ) : isSearchingJobs && matchedJobs.length === 0 ? (
                <div className="flex flex-col items-center justify-center rounded-xl border border-gray-200 bg-white py-16 text-center shadow-sm"><RefreshCw className="h-8 w-8 animate-spin text-brand/50" /><p className="mt-3 text-sm font-semibold text-gray-700">Calculating your best matches...</p><p className="mt-1 text-xs text-gray-400">Searching the latest collected job postings.</p></div>
              ) : matchedJobs.length === 0 ? (
                <div className="rounded-xl border border-dashed border-gray-300 bg-white px-6 py-16 text-center shadow-sm"><Briefcase className="mx-auto h-9 w-9 text-gray-300" /><p className="mt-3 text-sm font-bold text-gray-700">No matching roles yet</p><p className="mx-auto mt-1 max-w-md text-xs leading-relaxed text-gray-400">Try a broader search, update your skills in My Profile, or run the job collection pipeline from Market Forecasts.</p></div>
              ) : (
                <div className="space-y-3">
                  <div className="flex items-center justify-between px-1 text-xs text-gray-500"><span><strong className="text-gray-800">{matchingTotal}</strong> jobs ranked by relevance to your profile</span><button type="button" onClick={() => fetchMatchingJobs(jobSearchQuery, matchingPage, matchingSource)} disabled={isSearchingJobs} className="flex items-center gap-1 font-semibold text-brand hover:text-brand-dark disabled:opacity-50"><RefreshCw className={`h-3.5 w-3.5 ${isSearchingJobs ? 'animate-spin' : ''}`} /> Refresh</button></div>
                  {matchedJobs.map((job) => {
                    const skills = Array.isArray(user.skills) ? user.skills : []
                    const matchScore = skills.length ? Math.min(100, Math.round((job.skill_match_count / skills.length) * 100)) : 0
                    const overlap = (job.skill_overlap || []).map(String).map((skill) => skill.toLowerCase())
                    return (
                      <article key={job.id || job.job_id} className="group rounded-xl border border-gray-200 bg-white p-4 shadow-sm transition-all hover:border-brand/30 hover:shadow-md sm:p-5">
                        <div className="flex flex-col gap-4 lg:flex-row lg:items-start">
                          <div className="flex min-w-0 flex-1 gap-3"><div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-brand/15 to-cyan-100 text-base font-black text-brand">{(job.company || 'C').charAt(0).toUpperCase()}</div><div className="min-w-0 flex-1"><div className="flex flex-wrap items-start justify-between gap-2"><div><h3 className="text-sm font-bold leading-tight text-gray-900 group-hover:text-brand">{job.title}</h3><p className="mt-1 text-xs font-semibold text-gray-600">{job.company}</p></div><span className="rounded-full bg-gray-100 px-2 py-1 text-[10px] font-bold text-gray-500">{job.source}</span></div><div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-[11px] text-gray-500"><span className="flex items-center gap-1"><MapPin className="h-3 w-3" />{job.location}</span>{job.seniority_level && <span>{job.seniority_level}</span>}<span className="flex items-center gap-1"><Clock3 className="h-3 w-3" />{job.posted_date_text || 'Recently posted'}</span></div>{job.description_snippet && <p className="mt-3 line-clamp-2 text-xs leading-relaxed text-gray-500">{job.description_snippet}</p>}<div className="mt-3 flex flex-wrap gap-1.5">{(job.skills_extracted || []).slice(0, 8).map((skill, index) => <span key={`${skill}-${index}`} className={`rounded-md border px-2 py-1 text-[10px] font-semibold ${overlap.includes(String(skill).toLowerCase()) ? 'border-emerald-200 bg-emerald-50 text-emerald-700' : 'border-gray-200 bg-gray-50 text-gray-500'}`}>{overlap.includes(String(skill).toLowerCase()) ? '✓ ' : ''}{skill}</span>)}</div>{job.llm_reasoning && <div className="mt-3 rounded-lg border border-cyan-100 bg-cyan-50 p-3 text-[11px] text-cyan-950"><p className="font-bold">AI alignment reasoning: {String(job.llm_reasoning.recommendation || 'review')}</p>{job.llm_reasoning.fit_summary && <p className="mt-1 leading-relaxed">{job.llm_reasoning.fit_summary}</p>}{Array.isArray(job.llm_reasoning.skill_gaps) && job.llm_reasoning.skill_gaps.length > 0 && <p className="mt-1"><span className="font-semibold">Skill gaps:</span> {job.llm_reasoning.skill_gaps.join(', ')}</p>}</div>}</div></div>
                          <div className="flex shrink-0 items-center justify-between gap-4 border-t border-gray-100 pt-3 lg:w-32 lg:flex-col lg:items-center lg:border-l lg:border-t-0 lg:pl-5 lg:pt-0"><div className="text-center"><p className={`text-2xl font-black ${matchScore >= 70 ? 'text-emerald-600' : matchScore >= 40 ? 'text-amber-600' : 'text-gray-500'}`}>{matchScore}%</p><p className="text-[9px] font-bold uppercase tracking-wider text-gray-400">Skill fit</p><p className="mt-1 text-[10px] text-gray-400">{job.skill_match_count} shared skill{job.skill_match_count === 1 ? '' : 's'}</p></div>{job.job_link ? <a href={job.job_link} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 rounded-lg bg-brand px-3 py-2 text-xs font-semibold text-white shadow-sm transition-all hover:bg-brand-dark">View role <ExternalLink className="h-3 w-3" /></a> : <span className="text-[10px] text-gray-400">Link unavailable</span>}</div>
                        </div>
                      </article>
                    )
                  })}
                  {matchingTotalPages > 1 && <div className="flex items-center justify-center gap-3 pt-2"><button type="button" onClick={() => fetchMatchingJobs(jobSearchQuery, matchingPage - 1, matchingSource)} disabled={matchingPage <= 1 || isSearchingJobs} className="rounded-lg border border-gray-200 px-3 py-2 text-xs font-semibold text-gray-600 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-40">Previous</button><span className="text-xs text-gray-500">Page {matchingPage} of {matchingTotalPages}</span><button type="button" onClick={() => fetchMatchingJobs(jobSearchQuery, matchingPage + 1, matchingSource)} disabled={matchingPage >= matchingTotalPages || isSearchingJobs} className="rounded-lg border border-gray-200 px-3 py-2 text-xs font-semibold text-gray-600 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-40">Next</button></div>}
                </div>
              )}
            </div>
          )}

          {/* TAB 5: PROFILE / SETTINGS */}
          {activeTab === 'profile' && (
            <div className="space-y-6 w-full">
              {/* Profile Header Banner */}
              <div className="bg-gradient-to-r from-brand to-brand-light text-white rounded-xl shadow-md p-6 flex flex-col md:flex-row md:items-center justify-between gap-6">
                <div className="flex items-center space-x-4">
                  <div className="p-4 bg-white/10 text-white rounded-full backdrop-blur-sm border border-white/20">
                    <User className="h-8 w-8" />
                  </div>
                  <div>
                    <h2 className="text-xl font-bold text-white">{user.name}</h2>
                    <p className="text-sm text-blue-200 mt-0.5">{user.current_role}</p>
                  </div>
                </div>
                <div className="flex flex-col md:items-end space-y-2">
                  <p className="text-sm">
                    <span className="text-blue-200">Target role:</span> <span className="font-semibold text-white">{user.target_role}</span>
                  </p>
                  <div className="flex flex-wrap gap-1.5 md:justify-end">
                    {user.skills.map((sk, idx) => (
                      <span key={idx} className="px-2.5 py-0.5 bg-white/20 text-white rounded text-xs font-medium border border-white/10 backdrop-blur-sm">
                        {sk}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              {/* Bottom Cards: Forms & Editors */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-stretch">
                {/* Left Card: CV Parser & Upload */}
                <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 flex flex-col justify-between">
                  <div>
                    <div className="flex items-center space-x-2 mb-4">
                      <Upload className="h-5 w-5 text-brand" />
                      <h3 className="text-sm font-bold text-gray-800">Upload &amp; Sync CV</h3>
                    </div>
                    <p className="text-xs text-gray-500 mb-6 leading-relaxed">
                      Upload your latest resume (PDF or DOCX). Our mock parser will automatically scan the document, identify key technical skills, and update your profile diagnostics in real-time.
                    </p>

                    <form onSubmit={handleCvUpload} className="space-y-4">
                      {cvSuccessMsg && (
                        <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs rounded text-center">
                          {cvSuccessMsg}
                        </div>
                      )}
                      {cvErrorMsg && (
                        <div className="p-3 bg-red-50 border border-red-200 text-red-800 text-xs rounded text-center">
                          {cvErrorMsg}
                        </div>
                      )}
                      {savedCv && (
                        <div className="p-3 bg-blue-50 border border-blue-200 text-blue-800 text-xs rounded">
                          <div className="flex items-center justify-between gap-3">
                            <span className="font-semibold truncate">Saved CV: {savedCv.filename}</span>
                            <div className="flex shrink-0 gap-3">
                              <button type="button" onClick={handleDownloadCv} className="font-semibold underline hover:no-underline">
                                Download
                              </button>
                              <button type="button" onClick={handleRemoveCv} className="font-semibold underline hover:no-underline">
                                Remove
                              </button>
                            </div>
                          </div>
                          <p className="mt-1">Your parsed CV details are stored securely and available across devices.</p>
                        </div>
                      )}
                      <div className="border-2 border-dashed border-gray-200 rounded-lg p-4 hover:border-brand/40 transition-colors bg-gray-50/50">
                        <input
                          id="cv-file-input"
                          type="file"
                          accept=".pdf,.doc,.docx"
                          required
                          onChange={(e) => setCvFile(e.target.files[0])}
                          className="block w-full text-xs text-gray-500 file:mr-3 file:py-1.5 file:px-3 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 cursor-pointer"
                        />
                      </div>

                      <button
                        type="submit"
                        disabled={!cvFile || cvUploadLoading}
                        className="w-full flex items-center justify-center py-2.5 px-4 border border-gray-300 rounded-lg text-sm font-semibold text-gray-700 bg-white hover:bg-gray-50 transition-all disabled:opacity-50 shadow-sm"
                      >
                        {cvUploadLoading ? (
                          <>
                            <RefreshCw className="animate-spin h-4 w-4 mr-2 text-gray-600" />
                            <span>Parsing CV...</span>
                          </>
                        ) : (
                          <>
                            <Upload className="h-4 w-4 mr-2 text-gray-600" />
                            <span>Upload &amp; Parse CV</span>
                          </>
                        )}
                      </button>
                    </form>
                  </div>
                </div>

                {/* Right Card: Fast Diagnostics Editor */}
                <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
                  <div className="flex items-center space-x-2 mb-4">
                    <Zap className="h-5 w-5 text-brand" />
                    <h3 className="text-sm font-bold text-gray-800">Fast Diagnostics Editor</h3>
                  </div>
                  <form onSubmit={handleSaveProfile} className="space-y-4">
                    {profileSuccessMsg && (
                      <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs rounded text-center">
                        {profileSuccessMsg}
                      </div>
                    )}
                    {profileErrorMsg && (
                      <div className="p-3 bg-red-50 border border-red-200 text-red-700 text-xs rounded text-center" role="alert">
                        {profileErrorMsg}
                      </div>
                    )}
                    <div>
                      <label className="block text-xs font-semibold text-gray-600 mb-1.5">Edit Skills (comma separated)</label>
                      <textarea
                        value={editSkills}
                        onChange={(e) => setEditSkills(e.target.value)}
                        className="block w-full p-3 text-sm border border-gray-300 rounded-lg focus:ring-brand focus:border-brand bg-white"
                        rows="4"
                        placeholder="Python, SQL, Git..."
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-gray-600 mb-1.5">Change Target Role</label>
                      <TargetRoleInput
                        value={editTargetRole}
                        onChange={setEditTargetRole}
                        required
                        className="block w-full p-3 text-sm border border-gray-300 bg-white rounded-lg focus:ring-brand focus:border-brand"
                      />
                      <p className="mt-1.5 text-[11px] text-gray-500">Choose a suggestion or type any target role.</p>
                    </div>
                    <button
                      type="submit"
                      disabled={isUpdatingProfile}
                      className="w-full flex justify-center py-2.5 px-4 rounded-lg text-sm font-semibold text-white bg-brand hover:bg-brand-light transition-all disabled:opacity-50 shadow-sm"
                    >
                      {isUpdatingProfile ? 'Recalculating...' : 'Update & Run Diagnostic'}
                    </button>
                  </form>
                </div>
              </div>
            </div>
          )}
        </section>
      </main>
    </div>
  )
}

export default SeekerDashboard
