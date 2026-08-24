import React, { useState, useEffect, useRef } from 'react'
import Logo from './Logo.jsx'
import { API_URL } from '../App.jsx'
import { 
  TrendingUp, FileSearch, Milestone, CheckSquare, 
  User, Upload, BookOpen, GraduationCap, Briefcase, 
  MapPin, DollarSign, ExternalLink, RefreshCw, CheckCircle2, ChevronRight,
  LogOut, Bell, X
} from 'lucide-react'

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
  const [gapData, setGapData] = useState(null)
  const [careerData, setCareerData] = useState(null)
  const [matchedJobs, setMatchedJobs] = useState([])
  
  // UI states
  const [loading, setLoading] = useState(false)
  const [appliedJobIds, setAppliedJobIds] = useState(new Set())

  // Load initial data
  useEffect(() => {
    fetchDemandForecast()
    fetchGapAnalysis()
    fetchCareerPath()
    fetchMatchingJobs()
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

  const fetchGapAnalysis = async () => {
    try {
      const res = await fetch(`${API_URL}/skill-gap`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ skills: user.skills, target_role: user.target_role })
      })
      const data = await res.json()
      setGapData(data)
    } catch (e) {
      console.error("Error loading gap analysis", e)
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

  const fetchMatchingJobs = async () => {
    try {
      const res = await fetch(`${API_URL}/matching-jobs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ skills: user.skills })
      })
      const data = await res.json()
      setMatchedJobs(data)
    } catch (e) {
      console.error("Error loading matched jobs", e)
    }
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

        {/* Logout at bottom */}
        <div className="px-3 pb-5 border-t border-gray-100 pt-3">
          <button
            onClick={onLogout}
            className="w-full flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm font-medium text-red-500 hover:bg-red-50 transition-colors"
          >
            <LogOut className="h-4 w-4 shrink-0" />
            <span>Logout Session</span>
          </button>
        </div>
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

          {/* Right – Notification bell */}
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
        </header>

        {/* Tab Contents */}
        <section className="flex-1 p-6 overflow-y-auto">
          {/* TAB 1: MARKET DEMAND FORECASTING */}
          {activeTab === 'demand' && (
            <div className="space-y-6">
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
                    📈 Rapidly Ascending Core Skills
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
                    📉 Descending Core Skills
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

                  {/* Course Recommendations */}
                  <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
                    <h3 className="text-sm font-bold text-gray-900 mb-4 flex items-center space-x-2">
                      <GraduationCap className="h-4 w-4 text-brand" />
                      <span>Recommended Curated Courses from Coursera</span>
                    </h3>
                    <p className="text-xs text-gray-500 mb-4">Courses matched dynamically to address your <strong className="text-red-600">missing skills</strong> identified above.</p>

                    <div className="space-y-4">
                      {gapData.recommended_courses.map((course, idx) => (
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
                      ))}
                      {gapData.recommended_courses.length === 0 && (
                        <div className="p-6 text-center text-xs text-gray-500 border border-dashed rounded-lg bg-gray-50">
                          No specific course sync recommendations available for your current skills gaps.
                        </div>
                      )}
                    </div>
                  </div>
                </>
              ) : (
                <div className="h-64 flex items-center justify-center text-sm text-gray-500">Retrieving diagnostics...</div>
              )}
            </div>
          )}

          {/* TAB 3: CAREER PATH PLANNING */}
          {activeTab === 'path' && (
            <div className="space-y-6">
              {careerData ? (
                <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
                  <div className="mb-6 border-b border-gray-100 pb-4">
                    <h2 className="text-base font-bold text-gray-900">
                      AI Career Path Planner: Transition to <span className="text-brand">{careerData.target_role}</span>
                    </h2>
                    <p className="text-xs text-gray-500 mt-1">Est. Duration: <strong>{careerData.estimated_duration}</strong> starting from your current status: <strong>{careerData.current_role}</strong>.</p>
                  </div>

                  {/* Vertical Timeline Roadmap */}
                  <div className="relative border-l-2 border-gray-200 ml-4 pl-8 space-y-8">
                    {careerData.roadmap.map((step, idx) => (
                      <div key={idx} className="relative">
                        {/* Circle dot representing step status */}
                        <div className={`absolute -left-[41px] top-0.5 rounded-full border-4 border-white h-7 w-7 flex items-center justify-center text-xs font-bold text-white shadow-sm ${
                          step.status === 'completed' 
                            ? 'bg-emerald-500' 
                            : step.status === 'in-progress' 
                            ? 'bg-indigo-600' 
                            : 'bg-gray-300'
                        }`}>
                          {step.step}
                        </div>

                        <div>
                          <div className="flex items-center space-x-3">
                            <h3 className="text-xs font-bold text-gray-900">{step.title}</h3>
                            <span className={`px-2 py-0.5 rounded-full text-[9px] font-bold border uppercase ${
                              step.status === 'completed'
                                ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                                : step.status === 'in-progress'
                                ? 'bg-indigo-50 text-indigo-700 border-indigo-200'
                                : 'bg-gray-100 text-gray-400 border-gray-200'
                            }`}>
                              {step.status}
                            </span>
                          </div>
                          
                          <p className="text-xs text-gray-600 mt-1 max-w-2xl leading-relaxed">{step.description}</p>
                          <div className="text-[10px] text-gray-500 mt-2 flex flex-wrap items-center gap-x-4 gap-y-1">
                            <span>⏱️ Estimated: <strong>{step.duration}</strong></span>
                            <div className="flex items-center space-x-1">
                              <span>Focus:</span>
                              {step.skills_to_acquire.map((sk, i) => (
                                <span key={i} className="px-1.5 py-0.5 bg-gray-100 text-gray-700 rounded text-[9px] font-semibold border border-gray-200/50">
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
                      <div className="absolute -left-[41px] top-0.5 rounded-full border-4 border-white h-7 w-7 flex items-center justify-center text-xs font-bold text-white bg-brand shadow-sm">
                        ★
                      </div>
                      <div>
                        <h3 className="text-xs font-bold text-brand">Career Target Achieved</h3>
                        <p className="text-xs text-gray-600 mt-1">Ready for full-time placement matching for a <span className="font-semibold">{careerData.target_role}</span> role!</p>
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="h-64 flex items-center justify-center text-sm text-gray-500">Synthesizing path timeline...</div>
              )}
            </div>
          )}

          {/* TAB 4: SKILL MATCHING AND JOB ALIGNMENT */}
          {activeTab === 'matching' && (
            <div className="space-y-6">
              <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm mb-4">
                <h2 className="text-base font-bold text-gray-900">Skill Matching & Vacancy Alignment</h2>
                <p className="text-xs text-gray-500 mt-1">
                  Jobs scraped from LinkedIn, TopJobs.lk, and Indeed, matched automatically using your calculated skill matching coefficient.
                </p>
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
                              Scraped: {job.platform}
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
            <div className="max-w-2xl mx-auto space-y-6">
              {/* Profile summary card */}
              <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
                <div className="flex items-center space-x-4 mb-4">
                  <div className="p-3 bg-brand/10 text-brand rounded-full">
                    <User className="h-7 w-7" />
                  </div>
                  <div>
                    <h2 className="text-lg font-bold text-gray-900">{user.name}</h2>
                    <p className="text-sm text-gray-500">{user.current_role}</p>
                  </div>
                </div>
                <div className="text-sm text-gray-700 border-t border-gray-100 pt-4 space-y-2">
                  <p>Target role: <span className="font-semibold text-brand">{user.target_role}</span></p>
                  <div className="flex flex-wrap gap-1.5 mt-1">
                    {user.skills.map((sk, idx) => (
                      <span key={idx} className="px-2 py-0.5 bg-blue-50 text-blue-700 rounded text-xs font-medium border border-blue-100">
                        {sk}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              {/* Fast Diagnostics Editor */}
              <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
                <h3 className="text-sm font-bold text-gray-800 mb-4">Fast Diagnostics Editor</h3>
                <form onSubmit={handleSaveProfile} className="space-y-4">
                  {profileSuccessMsg && (
                    <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs rounded text-center">
                      {profileSuccessMsg}
                    </div>
                  )}
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">Edit Skills <span className="text-gray-400">(comma separated)</span></label>
                    <textarea
                      value={editSkills}
                      onChange={(e) => setEditSkills(e.target.value)}
                      className="block w-full p-3 text-sm border border-gray-300 rounded-lg focus:ring-brand focus:border-brand bg-white"
                      rows="3"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">Change Target Role</label>
                    <select
                      value={editTargetRole}
                      onChange={(e) => setEditTargetRole(e.target.value)}
                      className="block w-full p-3 text-sm border border-gray-300 bg-white rounded-lg focus:ring-brand focus:border-brand"
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
                    className="w-full flex justify-center py-2.5 px-4 rounded-lg text-sm font-semibold text-white bg-brand hover:bg-brand-light transition-all disabled:opacity-50"
                  >
                    {isUpdatingProfile ? 'Recalculating...' : 'Update & Run Diagnostic'}
                  </button>
                </form>
              </div>

              {/* CV Upload */}
              <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
                <h3 className="text-sm font-bold text-gray-800 mb-4">Upload CV <span className="text-gray-400 font-normal">(Mock Parser)</span></h3>
                <form onSubmit={handleCvUpload} className="space-y-4">
                  {cvSuccessMsg && (
                    <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs rounded text-center">
                      {cvSuccessMsg}
                    </div>
                  )}
                  <input
                    id="cv-file-input"
                    type="file"
                    accept=".pdf,.doc,.docx"
                    required
                    onChange={(e) => setCvFile(e.target.files[0])}
                    className="block w-full text-sm text-gray-500 file:mr-3 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
                  />
                  <button
                    type="submit"
                    disabled={!cvFile || cvUploadLoading}
                    className="w-full flex items-center justify-center py-2.5 px-4 border border-gray-300 rounded-lg text-sm font-semibold text-gray-700 bg-white hover:bg-gray-50 transition-all disabled:opacity-50"
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
          )}
        </section>
      </main>
    </div>
  )
}

export default SeekerDashboard

