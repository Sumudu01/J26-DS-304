import React, { useState, useEffect, useRef } from 'react'
import Logo from './Logo.jsx'
import { API_URL } from '../App.jsx'
import { 
  TrendingUp, FileSearch, Milestone, CheckSquare, 
  User, Upload, BookOpen, GraduationCap, Briefcase, 
  MapPin, DollarSign, ExternalLink, RefreshCw, CheckCircle2, ChevronRight,
  LogOut, Bell, X, Search, ArrowUpRight, BarChart3, Layers, Zap, AlertTriangle
} from 'lucide-react'
import ForceGraph2D from 'react-force-graph-2d'

function SeekerDashboard({ user, onUpdateUser, onLogout }) {
  const [activeTab, setActiveTab] = useState('demand') // 'demand', 'gap', 'path', 'matching', 'profile'

  // Notification state
  const [showNotifications, setShowNotifications] = useState(false)
  const notifRef = useRef(null)
  const [notifications, setNotifications] = useState([
    { id: 1, type: 'match',   read: false, title: 'New Job Match!',           body: 'A new AI Engineer role at WSO2 matches your profile (92% score).', time: '2m ago' },
    { id: 2, type: 'gap',     read: false, title: 'Skill Gap Alert',           body: 'You are missing TensorFlow — a top skill for your target role.', time: '1h ago' },
    { id: 3, type: 'market',  read: false, title: 'Market Trend Update',       body: 'Generative AI demand index rose 14% this week on LinkedIn.', time: '3h ago' },
    { id: 4, type: 'career',  read: true,  title: 'Career Path Milestone',     body: 'Complete 2 more Python projects to reach Senior ML Engineer level.', time: 'Yesterday' },
    { id: 5, type: 'match',   read: true,  title: 'Application Viewed',        body: 'Your Easy Apply application to Dialog was viewed by the recruiter.', time: '2d ago' },
  ])

  const unreadCount = notifications.filter(n => !n.read).length

  // Close notification panel when clicking outside
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (notifRef.current && !notifRef.current.contains(e.target)) {
        setShowNotifications(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const markAllRead = () => setNotifications(prev => prev.map(n => ({ ...n, read: true })))
  const dismissNotif = (id) => setNotifications(prev => prev.filter(n => n.id !== id))

  const notifIconColor = {
    match:  'bg-emerald-100 text-emerald-600',
    gap:    'bg-amber-100 text-amber-600',
    market: 'bg-blue-100 text-blue-600',
    career: 'bg-purple-100 text-purple-600',
  }
  const notifIcon = {
    match:  <CheckCircle2 className="h-4 w-4" />,
    gap:    <FileSearch className="h-4 w-4" />,
    market: <TrendingUp className="h-4 w-4" />,
    career: <Milestone className="h-4 w-4" />,
  }

  // Profile update state
  const [editSkills, setEditSkills] = useState(user.skills.join(', '))
  const [editTargetRole, setEditTargetRole] = useState(user.target_role || 'AI Engineer')
  const [isUpdatingProfile, setIsUpdatingProfile] = useState(false)
  const [profileSuccessMsg, setProfileSuccessMsg] = useState('')

  // CV Upload state
  const [cvFile, setCvFile] = useState(null)
  const [cvUploadLoading, setCvUploadLoading] = useState(false)
  const [cvSuccessMsg, setCvSuccessMsg] = useState('')

  // API response states
  const [demandData, setDemandData] = useState([])
  const [forecastHorizon, setForecastHorizon] = useState('2029') // 2027, 2028, 2029

  // Search demand state
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResult, setSearchResult] = useState(null)
  const [searchLoading, setSearchLoading] = useState(false)
  const [searchError, setSearchError] = useState('')
  const [hasSearched, setHasSearched] = useState(false)
  const [gapData, setGapData] = useState(null)
  const [careerData, setCareerData] = useState(null)
  const [matchedJobs, setMatchedJobs] = useState([])
  
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

  const graphContainerRef = useRef(null)
  const [graphWidth, setGraphWidth] = useState(800)

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
    fetchDemandForecast()
    fetchGapAnalysis()
    fetchCareerPath()
    fetchMatchingJobs()
    fetchSalaryInsights()
  }, [user]) // Re-run whenever user profile changes (skills, target_role)

  const fetchDemandForecast = async () => {
    try {
      const res = await fetch(`${API_URL}/demand-forecast`)
      const data = await res.json()
      setDemandData(data)
    } catch (e) {
      console.error("Error loading demand forecasts", e)
    }
  }

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

  const fetchMatchingJobs = async (query = '') => {
    setIsSearchingJobs(true)
    try {
      const res = await fetch(`${API_URL}/matching-jobs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ skills: user.skills, query })
      })
      const data = await res.json()
      setMatchedJobs(data)
    } catch (e) {
      console.error("Error loading matched jobs", e)
    } finally {
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

  // Debounced effect for fetching catalog courses
  useEffect(() => {
    if (courseSearchScope === 'all') {
      const delayDebounceFn = setTimeout(() => {
        fetchCatalogCourses(courseSearchQuery)
      }, 300)
      return () => clearTimeout(delayDebounceFn)
    }
  }, [courseSearchQuery, courseSearchScope])

  // Search for skill/job demand
  const searchSkillDemand = async (e) => {
    e && e.preventDefault()
    if (!searchQuery.trim() || searchQuery.trim().length < 2) {
      setSearchError('Please enter at least 2 characters to search.')
      return
    }
    setSearchLoading(true)
    setSearchError('')
    setSearchResult(null)
    setHasSearched(true)
    try {
      const res = await fetch(`${API_URL}/search-demand`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: searchQuery.trim() })
      })
      const data = await res.json()
      if (res.ok) {
        setSearchResult(data)
      } else {
        setSearchError(data.error || 'Search failed.')
      }
    } catch (err) {
      console.error('Search demand error', err)
      setSearchError('Network error. Please try again.')
    } finally {
      setSearchLoading(false)
    }
  }

  const clearSearch = () => {
    setSearchQuery('')
    setSearchResult(null)
    setSearchError('')
    setHasSearched(false)
  }

  // Save manual profile edits
  const handleSaveProfile = async (e) => {
    e.preventDefault()
    setIsUpdatingProfile(true)
    setProfileSuccessMsg('')
    try {
      const skillList = editSkills.split(',').map(s => s.trim()).filter(Boolean)
      const res = await fetch(`${API_URL}/profile/update`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: user.email,
          skills: skillList,
          target_role: editTargetRole
        })
      })
      const data = await res.json()
      if (res.ok) {
        onUpdateUser(data.user)
        setProfileSuccessMsg('Skills updated. Analytics refreshed!')
        setTimeout(() => setProfileSuccessMsg(''), 4000)
      }
    } catch (e) {
      console.error("Error updating profile", e)
    } finally {
      setIsUpdatingProfile(false)
    }
  }

  // Mock CV Upload
  const handleCvUpload = async (e) => {
    e.preventDefault()
    if (!cvFile) return
    
    setCvUploadLoading(true)
    setCvSuccessMsg('')
    
    const formData = new FormData()
    formData.append('cv', cvFile)
    formData.append('email', user.email)
    
    try {
      const res = await fetch(`${API_URL}/seeker/upload-cv`, {
        method: 'POST',
        body: formData
      })
      const data = await res.json()
      if (res.ok) {
        onUpdateUser(data.user)
        setEditSkills(data.user.skills.join(', '))
        setCvSuccessMsg(`Successfully parsed ${data.filename}! Added advanced skills.`)
        setCvFile(null)
        // Reset file input
        document.getElementById('cv-file-input').value = ''
      }
    } catch (e) {
      console.error("Error uploading CV", e)
    } finally {
      setCvUploadLoading(false)
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
    <div className="flex-1 flex flex-col md:flex-row min-h-screen">

      {/* ── LEFT SIDEBAR – Vertical Navigation ── */}
      <aside className="w-full md:w-64 bg-white border-r border-gray-200 flex flex-col shrink-0">

        {/* Logo */}
        <div className="px-5 py-5 border-b border-gray-100">
          <Logo className="h-8 w-auto" />
        </div>

        {/* Nav links */}
        <nav className="flex-1 px-3 py-4 space-y-1">
          <p className="px-3 mb-2 text-[10px] font-semibold text-gray-400 uppercase tracking-widest">Dashboard</p>

          <button
            onClick={() => setActiveTab('demand')}
            className={`w-full flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
              activeTab === 'demand'
                ? 'bg-brand text-white shadow-sm'
                : 'text-gray-600 hover:bg-gray-100'
            }`}
          >
            <TrendingUp className="h-4 w-4 shrink-0" />
            <span>Market Forecasts</span>
          </button>

          <button
            onClick={() => setActiveTab('gap')}
            className={`w-full flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
              activeTab === 'gap'
                ? 'bg-brand text-white shadow-sm'
                : 'text-gray-600 hover:bg-gray-100'
            }`}
          >
            <FileSearch className="h-4 w-4 shrink-0" />
            <span>Skill Gap Discovery</span>
          </button>

          <button
            onClick={() => setActiveTab('path')}
            className={`w-full flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
              activeTab === 'path'
                ? 'bg-brand text-white shadow-sm'
                : 'text-gray-600 hover:bg-gray-100'
            }`}
          >
            <Milestone className="h-4 w-4 shrink-0" />
            <span>Career Path Planning</span>
          </button>

          <button
            onClick={() => setActiveTab('matching')}
            className={`w-full flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
              activeTab === 'matching'
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
            className={`w-full flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
              activeTab === 'profile'
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
      <main className="flex-1 flex flex-col bg-gray-50">
        {/* Top header bar */}
        <header className="bg-white border-b border-gray-200 px-6 py-4 shrink-0 flex items-center justify-between relative">
          {/* Left – page title */}
          <div>
            <h1 className="text-xl font-bold text-gray-900">
              {activeTab === 'demand'   && 'Market Forecasts'}
              {activeTab === 'gap'      && 'Skill Gap Discovery'}
              {activeTab === 'path'     && 'Career Path Planning'}
              {activeTab === 'matching' && 'Skill Matching & Jobs'}
              {activeTab === 'profile'  && 'My Profile'}
            </h1>
            <p className="text-xs text-gray-500 mt-0.5">
              {activeTab === 'profile'
                ? 'Manage your skills, target role, and upload your CV'
                : 'Diagnose skills, review roadmaps, and match vacancies'}
            </p>
          </div>

          {/* Right – Notification bell & Logout */}
          <div className="flex items-center space-x-4">
            <div className="relative" ref={notifRef}>
              <button
                onClick={() => setShowNotifications(prev => !prev)}
                className="relative p-2 rounded-lg text-gray-500 hover:bg-gray-100 hover:text-gray-700 transition-colors focus:outline-none"
                aria-label="Notifications"
              >
                <Bell className="h-5 w-5" />
                {unreadCount > 0 && (
                  <span className="absolute top-1 right-1 h-4 w-4 flex items-center justify-center rounded-full bg-red-500 text-white text-[9px] font-bold leading-none">
                    {unreadCount}
                  </span>
                )}
              </button>

              {/* Floating notification panel */}
              {showNotifications && (
                <div className="absolute right-0 mt-2 w-80 bg-white rounded-xl border border-gray-200 shadow-xl z-50 overflow-hidden">
                {/* Panel header */}
                <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
                  <div className="flex items-center space-x-2">
                    <Bell className="h-4 w-4 text-gray-700" />
                    <span className="text-sm font-bold text-gray-900">Notifications</span>
                    {unreadCount > 0 && (
                      <span className="px-1.5 py-0.5 bg-red-100 text-red-600 text-[10px] font-bold rounded-full">
                        {unreadCount} new
                      </span>
                    )}
                  </div>
                  {unreadCount > 0 && (
                    <button
                      onClick={markAllRead}
                      className="text-[11px] text-brand font-semibold hover:underline"
                    >
                      Mark all read
                    </button>
                  )}
                </div>

                {/* Notification list */}
                <ul className="max-h-80 overflow-y-auto divide-y divide-gray-50">
                  {notifications.length === 0 && (
                    <li className="px-4 py-8 text-center text-sm text-gray-400">
                      You're all caught up! 🎉
                    </li>
                  )}
                  {notifications.map(n => (
                    <li
                      key={n.id}
                      className={`flex items-start gap-3 px-4 py-3 group transition-colors ${
                        n.read ? 'bg-white' : 'bg-blue-50/40'
                      }`}
                    >
                      {/* Icon */}
                      <div className={`mt-0.5 p-1.5 rounded-full shrink-0 ${notifIconColor[n.type]}`}>
                        {notifIcon[n.type]}
                      </div>

                      {/* Content */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between gap-1">
                          <p className={`text-xs font-semibold truncate ${n.read ? 'text-gray-700' : 'text-gray-900'}`}>
                            {n.title}
                            {!n.read && <span className="ml-1.5 inline-block h-1.5 w-1.5 rounded-full bg-blue-500 align-middle" />}
                          </p>
                          <span className="text-[10px] text-gray-400 shrink-0">{n.time}</span>
                        </div>
                        <p className="text-[11px] text-gray-500 mt-0.5 leading-relaxed line-clamp-2">
                          {n.body}
                        </p>
                      </div>

                      {/* Dismiss */}
                      <button
                        onClick={() => dismissNotif(n.id)}
                        className="opacity-0 group-hover:opacity-100 mt-0.5 text-gray-300 hover:text-gray-500 transition-opacity shrink-0"
                        aria-label="Dismiss"
                      >
                        <X className="h-3.5 w-3.5" />
                      </button>
                    </li>
                  ))}
                </ul>

                {/* Panel footer */}
                {notifications.length > 0 && (
                  <div className="px-4 py-2.5 border-t border-gray-100 text-center">
                    <button
                      onClick={() => setNotifications([])}
                      className="text-[11px] text-gray-400 hover:text-gray-600 font-medium transition-colors"
                    >
                      Clear all notifications
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>

          <button
            onClick={onLogout}
            className="flex items-center space-x-2 px-3 py-1.5 rounded-lg text-xs font-semibold text-red-500 hover:bg-red-50 border border-red-200 hover:border-red-300 transition-all shadow-sm focus:outline-none"
          >
            <LogOut className="h-4 w-4 shrink-0" />
            <span>Logout Session</span>
          </button>
        </div>
      </header>

        {/* Tab Contents */}
        <section className="flex-1 p-6 overflow-y-auto">
          {/* TAB 1: MARKET DEMAND FORECASTING */}
          {activeTab === 'demand' && (
            <div className="space-y-6">

              {/* ── SEARCH SKILL / JOB DEMAND ── */}
              <div className="bg-gradient-to-br from-brand/[0.03] via-white to-blue-50/50 p-6 rounded-xl border border-brand/10 shadow-sm">
                <div className="flex items-center space-x-2 mb-4">
                  <div className="p-2 bg-brand/10 rounded-lg">
                    <Search className="h-4 w-4 text-brand" />
                  </div>
                  <div>
                    <h2 className="text-base font-bold text-gray-900">Search Skill or Job Demand</h2>
                    <p className="text-xs text-gray-500 mt-0.5">Look up any skill, technology, or job role to see its current market demand</p>
                  </div>
                </div>

                {/* Search Input */}
                <form onSubmit={searchSkillDemand} className="flex items-center gap-3">
                  <div className="relative flex-1">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                    <input
                      type="text"
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      placeholder='Try "Machine Learning", "AWS", "React", "AI Engineer"...'
                      className="w-full pl-10 pr-4 py-2.5 text-sm bg-white border border-gray-200 rounded-lg focus:ring-2 focus:ring-brand/20 focus:border-brand/40 outline-none transition-all placeholder:text-gray-400"
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={searchLoading}
                    className="px-5 py-2.5 bg-brand text-white text-sm font-semibold rounded-lg hover:bg-brand-dark transition-all shadow-sm disabled:opacity-50 flex items-center space-x-1.5"
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
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        <span className="text-sm font-bold text-gray-900">Results for</span>
                        <span className="px-2.5 py-0.5 bg-brand/10 text-brand text-xs font-bold rounded-full">"{searchResult.query}"</span>
                        {searchResult.matched_skill_category && (
                          <span className="text-xs text-gray-400">→ mapped to <span className="font-semibold text-gray-600">{searchResult.matched_skill_category}</span></span>
                        )}
                      </div>
                    </div>

                    {/* Metrics Cards Row */}
                    {searchResult.matched_skill_category ? (
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
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
                          <span className={`text-sm font-bold ${
                            searchResult.demand_status === 'High & Growing' ? 'text-emerald-600' :
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
                          <span className={`text-[10px] ml-1 font-semibold ${
                            searchResult.forecast_growth_percent > 0 ? 'text-emerald-600' : 'text-red-600'
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
                    {searchResult.trend_timeline.length > 0 && (
                      <div className="bg-white rounded-lg border border-gray-100 p-4 shadow-sm">
                        <h4 className="text-xs font-bold text-gray-700 mb-3 flex items-center space-x-1.5">
                          <BarChart3 className="h-3.5 w-3.5 text-brand" />
                          <span>Demand Trend for {searchResult.matched_skill_category} (2022 – 2029)</span>
                        </h4>
                        {(() => {
                          const maxVal = 150
                          const barMaxH = 120 // max bar height in px
                          return (
                            <div className="relative pl-8">
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
                                        className={`w-5 md:w-6 rounded-t transition-all duration-500 hover:scale-105 cursor-default ${
                                          point.is_forecast
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
                          )
                        })()}
                        <div className="flex items-center justify-center gap-4 mt-3 text-[10px] text-gray-400">
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
                        <div className="grid grid-cols-3 gap-3">
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
                    {searchResult.related_jobs.length > 0 && (
                      <div className="bg-white rounded-lg border border-gray-100 p-4 shadow-sm">
                        <h4 className="text-xs font-bold text-gray-700 mb-3 flex items-center space-x-1.5">
                          <Briefcase className="h-3.5 w-3.5 text-brand" />
                          <span>Related Open Positions ({searchResult.related_jobs.length})</span>
                        </h4>
                        <div className="space-y-2">
                          {searchResult.related_jobs.map((job, i) => (
                            <div key={i} className="flex items-center justify-between px-3 py-2.5 bg-gray-50 rounded-lg border border-gray-100 hover:border-brand/20 hover:bg-brand/[0.02] transition-all group">
                              <div className="flex-1 min-w-0">
                                <div className="text-xs font-bold text-gray-800 group-hover:text-brand transition-colors truncate">{job.title}</div>
                                <div className="text-[10px] text-gray-500 flex items-center gap-2 mt-0.5">
                                  <span>{job.company}</span>
                                  <span className="text-gray-300">•</span>
                                  <span className="flex items-center"><MapPin className="h-2.5 w-2.5 mr-0.5" />{job.location}</span>
                                  <span className="text-gray-300">•</span>
                                  <span className="font-medium text-emerald-600">{job.salary}</span>
                                </div>
                              </div>
                              <span className="text-[9px] px-2 py-0.5 bg-blue-50 text-blue-600 rounded-full font-semibold shrink-0 ml-2">{job.platform}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>

              <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
                <div className="flex justify-between items-center mb-6">
                  <div>
                    <h2 className="text-base font-bold text-gray-900">Future Job Market Demand Forecasting</h2>
                    <p className="text-xs text-gray-500 mt-1">Predictions on tech demand index calculated from LinkedIn, Indeed, and TopJobs.lk</p>
                  </div>
                  <div className="flex items-center space-x-2 text-xs">
                    <span className="text-gray-500 font-medium">Forecast Horizon:</span>
                    <select
                      value={forecastHorizon}
                      onChange={(e) => setForecastHorizon(e.target.value)}
                      className="border border-gray-300 rounded p-1 bg-white"
                    >
                      <option value="2027">1-Year Outlook (2027)</option>
                      <option value="2028">2-Year Outlook (2028)</option>
                      <option value="2029">3-Year Outlook (2029)</option>
                    </select>
                  </div>
                </div>

                {/* SVG Forecasting line chart */}
                {demandData.length > 0 ? (
                  <div className="relative">
                    <div className="h-64 w-full flex items-end justify-between border-b border-l border-gray-300 pb-2 pl-4">
                      {/* Vertical axis legend */}
                      <div className="absolute left-0 top-0 h-full flex flex-col justify-between text-[10px] text-gray-400 -ml-1 select-none">
                        <span>150</span>
                        <span>100</span>
                        <span>50</span>
                        <span>0</span>
                      </div>
                      
                      {/* Render line bars based on selected forecast years */}
                      {demandData.filter(d => d.year <= parseInt(forecastHorizon)).map((d, index) => {
                        return (
                          <div key={index} className="flex flex-col items-center flex-1 group">
                            {/* Demand bar graphics */}
                            <div className="flex items-end space-x-1.5 w-full justify-center h-48 mb-2">
                              {/* Generative AI (Blue) */}
                              <div 
                                style={{ height: `${(d["Generative AI"] / 150) * 100}%` }}
                                className="w-3.5 bg-blue-600 rounded-t transition-all duration-500 hover:opacity-80 relative"
                                title={`Generative AI: ${d["Generative AI"]}`}
                              >
                                <span className="absolute -top-6 left-1/2 -translate-x-1/2 text-[9px] font-bold text-blue-700 opacity-0 group-hover:opacity-100">{d["Generative AI"]}</span>
                              </div>
                              {/* Python (Indigo) */}
                              <div 
                                style={{ height: `${(d["Python"] / 150) * 100}%` }}
                                className="w-3.5 bg-indigo-600 rounded-t transition-all duration-500 hover:opacity-80 relative"
                                title={`Python: ${d["Python"]}`}
                              >
                                <span className="absolute -top-6 left-1/2 -translate-x-1/2 text-[9px] font-bold text-indigo-700 opacity-0 group-hover:opacity-100">{d["Python"]}</span>
                              </div>
                              {/* Cloud (Emerald) */}
                              <div 
                                style={{ height: `${(d["Cloud Computing"] / 150) * 100}%` }}
                                className="w-3.5 bg-emerald-600 rounded-t transition-all duration-500 hover:opacity-80 relative"
                                title={`Cloud Computing: ${d["Cloud Computing"]}`}
                              >
                                <span className="absolute -top-6 left-1/2 -translate-x-1/2 text-[9px] font-bold text-emerald-700 opacity-0 group-hover:opacity-100">{d["Cloud Computing"]}</span>
                              </div>
                              {/* Traditional Web (Yellow) */}
                              <div 
                                style={{ height: `${(d["Traditional Web"] / 150) * 100}%` }}
                                className="w-3.5 bg-yellow-500 rounded-t transition-all duration-500 hover:opacity-80 relative"
                                title={`Traditional Web: ${d["Traditional Web"]}`}
                              >
                                <span className="absolute -top-6 left-1/2 -translate-x-1/2 text-[9px] font-bold text-yellow-600 opacity-0 group-hover:opacity-100">{d["Traditional Web"]}</span>
                              </div>
                              {/* Legacy (Red) */}
                              <div 
                                style={{ height: `${(d["COBOL/Legacy"] / 150) * 100}%` }}
                                className="w-3.5 bg-red-400 rounded-t transition-all duration-500 hover:opacity-80 relative"
                                title={`COBOL/Legacy: ${d["COBOL/Legacy"]}`}
                              >
                                <span className="absolute -top-6 left-1/2 -translate-x-1/2 text-[9px] font-bold text-red-600 opacity-0 group-hover:opacity-100">{d["COBOL/Legacy"]}</span>
                              </div>
                            </div>
                            <span className="text-xs font-bold text-gray-700">{d.year}</span>
                            {d.year > 2026 && <span className="text-[9px] text-blue-600 font-semibold uppercase">Forecast</span>}
                          </div>
                        )
                      })}
                    </div>
                  </div>
                ) : (
                  <div className="h-64 flex items-center justify-center text-sm text-gray-500">Querying forecasts...</div>
                )}

                {/* Legend */}
                <div className="flex flex-wrap justify-center items-center gap-6 mt-6 border-t border-gray-100 pt-4 text-xs font-medium text-gray-600">
                  <div className="flex items-center space-x-1.5">
                    <span className="h-3 w-3 rounded bg-blue-600"></span>
                    <span>Generative AI (NLP/LLMs)</span>
                  </div>
                  <div className="flex items-center space-x-1.5">
                    <span className="h-3 w-3 rounded bg-indigo-600"></span>
                    <span>Python Programming</span>
                  </div>
                  <div className="flex items-center space-x-1.5">
                    <span className="h-3 w-3 rounded bg-emerald-600"></span>
                    <span>Cloud Computing (AWS/Docker)</span>
                  </div>
                  <div className="flex items-center space-x-1.5">
                    <span className="h-3 w-3 rounded bg-yellow-500"></span>
                    <span>Traditional Web</span>
                  </div>
                  <div className="flex items-center space-x-1.5">
                    <span className="h-3 w-3 rounded bg-red-400"></span>
                    <span>COBOL / Legacy</span>
                  </div>
                </div>
              </div>

              {/* Emerging trends card list */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
                  <h3 className="text-sm font-bold text-gray-900 mb-3 flex items-center text-emerald-700">
                    📈 Rapidly Emerging Skills
                  </h3>
                  <div className="space-y-3">
                    <div className="flex justify-between items-center text-xs">
                      <span className="font-semibold text-gray-700">Generative AI Models (RAG, Agents)</span>
                      <span className="px-2 py-0.5 bg-emerald-50 text-emerald-700 rounded-full font-bold">+59% forecasted</span>
                    </div>
                    <div className="flex justify-between items-center text-xs">
                      <span className="font-semibold text-gray-700">Prompt Engineering Patterns</span>
                      <span className="px-2 py-0.5 bg-emerald-50 text-emerald-700 rounded-full font-bold">+35% forecasted</span>
                    </div>
                    <div className="flex justify-between items-center text-xs">
                      <span className="font-semibold text-gray-700">AWS Cloud Engineering & Kubernetes</span>
                      <span className="px-2 py-0.5 bg-emerald-50 text-emerald-700 rounded-full font-bold">+20% forecasted</span>
                    </div>
                  </div>
                </div>

                <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
                  <h3 className="text-sm font-bold text-gray-900 mb-3 flex items-center text-red-700">
                    📉 Gradually Declining Skills
                  </h3>
                  <div className="space-y-3">
                    <div className="flex justify-between items-center text-xs">
                      <span className="font-semibold text-gray-700">COBOL / Mainframe Logic</span>
                      <span className="px-2 py-0.5 bg-red-50 text-red-700 rounded-full font-bold">-83% demand drop</span>
                    </div>
                    <div className="flex justify-between items-center text-xs">
                      <span className="font-semibold text-gray-700">On-Prem Server Management</span>
                      <span className="px-2 py-0.5 bg-red-50 text-red-700 rounded-full font-bold">-40% demand drop</span>
                    </div>
                    <div className="flex justify-between items-center text-xs">
                      <span className="font-semibold text-gray-700">Static jQuery Frontend Templates</span>
                      <span className="px-2 py-0.5 bg-red-50 text-red-700 rounded-full font-bold">-25% demand drop</span>
                    </div>
                  </div>
                </div>
              </div>
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
                            const fontSize = 12/globalScale;
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
                            <div className={`absolute -left-[37px] top-0.5 rounded-full border-4 border-white h-6 w-6 flex items-center justify-center text-[10px] font-bold text-white shadow-sm ${
                              step.status === 'completed'
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
                                <span className={`px-1.5 py-0.5 rounded-full text-[8px] font-bold border uppercase ${
                                  step.status === 'completed'
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
                                  'advanced':     'from-indigo-500 to-blue-500',
                                  'cloud':        'from-sky-500 to-cyan-500',
                                  'devops':       'from-teal-500 to-emerald-500',
                                  'foundational': 'from-gray-400 to-gray-500',
                                }[item.category] || 'from-brand to-indigo-500';
                                return (
                                  <div key={idx}>
                                    <div className="flex justify-between items-center mb-0.5">
                                      <div className="flex items-center space-x-1.5">
                                        <span className="text-xs font-semibold text-gray-800">{item.skill}</span>
                                        <span className={`px-1.5 py-0.5 rounded-full text-[8px] font-bold border ${
                                          item.category === 'cutting-edge' ? 'bg-purple-50 text-purple-700 border-purple-200'
                                          : item.category === 'advanced'   ? 'bg-indigo-50 text-indigo-700 border-indigo-200'
                                          : item.category === 'cloud'      ? 'bg-sky-50 text-sky-700 border-sky-200'
                                          : item.category === 'devops'     ? 'bg-teal-50 text-teal-700 border-teal-200'
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
                        className={`px-3 py-1.5 rounded-md transition-all ${
                          courseSearchScope === 'recommended'
                            ? 'bg-white text-gray-900 shadow-sm'
                            : 'text-gray-500 hover:text-gray-900'
                        }`}
                      >
                        Recommended
                      </button>
                      <button
                        type="button"
                        onClick={() => { setCourseSearchScope('all'); setCourseSearchQuery(''); }}
                        className={`px-3 py-1.5 rounded-md transition-all ${
                          courseSearchScope === 'all'
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
            <div className="space-y-6">
              <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm mb-4">
                <h2 className="text-base font-bold text-gray-900">Skill Matching & Vacancy Alignment</h2>
                <p className="text-xs text-gray-500 mt-1 mb-5">
                  Jobs scraped from LinkedIn, TopJobs.lk, and Indeed, matched automatically using your calculated skill matching coefficient.
                </p>

                <form 
                  onSubmit={(e) => { e.preventDefault(); fetchMatchingJobs(jobSearchQuery); }}
                  className="flex items-center gap-3"
                >
                  <div className="relative flex-1">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                    <input
                      type="text"
                      value={jobSearchQuery}
                      onChange={(e) => setJobSearchQuery(e.target.value)}
                      placeholder='Search jobs by title, company, or skills...'
                      className="w-full pl-10 pr-4 py-2.5 text-sm bg-gray-50 border border-gray-200 rounded-lg focus:ring-2 focus:ring-brand/20 focus:border-brand/40 outline-none transition-all placeholder:text-gray-400"
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={isSearchingJobs}
                    className="px-5 py-2.5 bg-brand text-white text-sm font-semibold rounded-lg hover:bg-brand-dark transition-all shadow-sm disabled:opacity-50 flex items-center space-x-1.5"
                  >
                    {isSearchingJobs ? (
                      <RefreshCw className="h-4 w-4 animate-spin" />
                    ) : (
                      <Search className="h-4 w-4" />
                    )}
                    <span>{isSearchingJobs ? 'Searching...' : 'Search'}</span>
                  </button>
                  {jobSearchQuery && (
                    <button
                      type="button"
                      onClick={() => { setJobSearchQuery(''); fetchMatchingJobs(''); }}
                      className="px-3 py-2.5 text-sm font-medium text-gray-500 hover:text-gray-700 border border-gray-200 rounded-lg hover:bg-gray-50 transition-all"
                    >
                      Clear
                    </button>
                  )}
                </form>
              </div>

              <div className="space-y-4">
                {matchedJobs.map((job) => {
                  const hasApplied = appliedJobIds.has(job.id)
                  return (
                    <div key={job.id} className="bg-white border border-gray-200 rounded-xl p-5 hover:border-brand/40 transition-all shadow-sm flex flex-col md:flex-row justify-between gap-6">
                      <div className="flex-1 space-y-3">
                        {/* Job header */}
                        <div className="flex flex-wrap items-start justify-between gap-2">
                          <div>
                            <h3 className="text-sm font-bold text-gray-900">{job.title}</h3>
                            <div className="flex items-center space-x-2 text-xs text-gray-500 mt-0.5">
                              <span className="font-semibold text-gray-700">{job.company}</span>
                              <span>•</span>
                              <span className="flex items-center"><MapPin className="h-3 w-3 mr-0.5" /> {job.location}</span>
                            </div>
                          </div>
                          
                          <div className="flex items-center space-x-2">
                            <span className="px-2 py-0.5 bg-gray-100 text-gray-600 border border-gray-200 rounded-full text-[10px] font-semibold">
                              {job.platform}
                            </span>
                            <span className="text-[10px] text-gray-400 font-medium">{job.posted_date}</span>
                          </div>
                        </div>

                        {/* Description snippet */}
                        <p className="text-xs text-gray-600 leading-relaxed">{job.description}</p>

                        {/* Salary and tags */}
                        <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-gray-500 border-t border-gray-100 pt-3">
                          <span className="flex items-center text-brand font-semibold"><DollarSign className="h-3.5 w-3.5 mr-0.5 text-brand" /> {job.salary}</span>
                          
                          <div className="flex flex-wrap gap-1">
                            {job.required_skills.map((skill, index) => {
                              const matches = job.matching_skills.includes(skill)
                              return (
                                <span 
                                  key={index}
                                  className={`px-1.5 py-0.5 rounded text-[10px] font-medium border ${
                                    matches 
                                      ? 'bg-emerald-50 text-emerald-700 border-emerald-200' 
                                      : 'bg-red-50 text-red-700 border-red-200'
                                  }`}
                                >
                                  {matches ? '✓' : '✗'} {skill}
                                </span>
                              )
                            })}
                          </div>
                        </div>
                      </div>

                      {/* Score gauge & CTA */}
                      <div className="flex md:flex-col items-center justify-between md:justify-center border-t md:border-t-0 md:border-l border-gray-100 pt-4 md:pt-0 md:pl-6 gap-4 shrink-0">
                        <div className="text-center md:mb-3">
                          <span className={`text-2xl font-black block ${
                            job.match_score >= 80 ? 'text-emerald-600' : job.match_score >= 50 ? 'text-yellow-600' : 'text-gray-500'
                          }`}>
                            {job.match_score}%
                          </span>
                          <span className="text-[9px] font-bold text-gray-400 uppercase tracking-wider block">Match Score</span>
                        </div>

                        {hasApplied ? (
                          <div className="px-4 py-2 bg-emerald-50 text-emerald-800 border border-emerald-200 rounded text-xs font-semibold flex items-center space-x-1">
                            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
                            <span>Applied</span>
                          </div>
                        ) : (
                          <button
                            onClick={() => handleApplyJob(job.id)}
                            className="px-5 py-2 bg-brand text-white hover:bg-brand-light rounded text-xs font-semibold shadow-sm transition-all"
                          >
                            Easy Apply
                          </button>
                        )}
                      </div>
                    </div>
                  )
                })}

                {matchedJobs.length === 0 && (
                  <div className="p-8 text-center text-sm text-gray-500 border border-dashed rounded-lg bg-white">
                    No active job listings synced from platform feeds matching your criteria.
                  </div>
                )}
              </div>
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
                      <select
                        value={editTargetRole}
                        onChange={(e) => setEditTargetRole(e.target.value)}
                        className="block w-full p-3 text-sm border border-gray-300 bg-white rounded-lg focus:ring-brand focus:border-brand cursor-pointer"
                      >
                        <option value="AI Engineer">AI Engineer</option>
                        <option value="Machine Learning Engineer">Machine Learning Engineer</option>
                        <option value="Cloud Architect">Cloud Architect</option>
                        <option value="Data Analyst">Data Analyst</option>
                        <option value="Full Stack Developer">Full Stack Developer</option>
                      </select>
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

