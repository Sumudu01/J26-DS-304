import React, { useState, useEffect, useRef } from 'react'
import  Logo  from './Logo.jsx'
import { API_URL } from '../App.jsx'
import { 
  Briefcase, Users, BarChart3, Plus, Search, 
  MapPin, DollarSign, Check, X, FileText, UserCheck, AlertTriangle, LogOut, Bell
} from 'lucide-react'

function RecruiterDashboard({ user, onLogout }) {
  const [activeTab, setActiveTab] = useState('posts') // 'posts', 'candidates', 'analytics'
  
  // Notification state
  const [showNotifications, setShowNotifications] = useState(false)
  const notifRef = useRef(null)
  const [notifications, setNotifications] = useState([
    { id: 1, type: 'applicant', read: false, title: 'New Candidate Match', body: 'Kamal Perera matched 95% with your AI Specialist posting.', time: '5m ago' },
    { id: 2, type: 'post',      read: false, title: 'Job Post Live',        body: 'Your post for "Data Scientist" is now active on all platforms.', time: '2h ago' },
    { id: 3, type: 'analytics', read: false, title: 'Market Insight',       body: 'Average salary for AI roles in Colombo rose by 8% this month.', time: '1d ago' },
    { id: 4, type: 'applicant', read: true,  title: 'Profile Updated',      body: 'A shortlisted candidate updated their experience profile.', time: '2d ago' },
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
    applicant: 'bg-emerald-100 text-emerald-600',
    post:      'bg-blue-100 text-blue-600',
    analytics: 'bg-purple-100 text-purple-600',
  }
  const notifIcon = {
    applicant: <Users className="h-4 w-4" />,
    post:      <Briefcase className="h-4 w-4" />,
    analytics: <BarChart3 className="h-4 w-4" />,
  }
  
  // Posted jobs state
  const [recruiterJobs, setRecruiterJobs] = useState([])
  const [selectedJobId, setSelectedJobId] = useState('')
  
  // Job Post form fields
  const [jobTitle, setJobTitle] = useState('')
  const [jobLocation, setJobLocation] = useState('Colombo, Sri Lanka')
  const [jobSalary, setJobSalary] = useState('LKR 250,000 - 350,000')
  const [jobDescription, setJobDescription] = useState('')
  const [jobSkills, setJobSkills] = useState('')
  const [postSuccess, setPostSuccess] = useState('')
  const [postLoading, setPostLoading] = useState(false)

  // Candidate match states
  const [matchedCandidates, setMatchedCandidates] = useState([])
  const [candidatesLoading, setCandidatesLoading] = useState(false)
  const [shortlistedCandIds, setShortlistedCandIds] = useState(new Set())

  // Market analytics state
  const [marketData, setMarketData] = useState([])

  useEffect(() => {
    fetchJobs()
    fetchMarketAnalytics()
  }, [])

  // Auto-fetch candidates when selected job changes
  useEffect(() => {
    if (selectedJobId) {
      fetchCandidatesForJob(selectedJobId)
    } else {
      setMatchedCandidates([])
    }
  }, [selectedJobId])

  const fetchJobs = async () => {
    try {
      const res = await fetch(`${API_URL}/recruiter/posted-jobs`)
      const data = await res.json()
      setRecruiterJobs(data)
      // Default to first job if available
      if (data.length > 0 && !selectedJobId) {
        setSelectedJobId(data[0].id)
      }
    } catch (e) {
      console.error("Error loading posted jobs", e)
    }
  }

  const fetchCandidatesForJob = async (jobId) => {
    setCandidatesLoading(true)
    try {
      const res = await fetch(`${API_URL}/recruiter/matching-candidates?job_id=${jobId}`)
      const data = await res.json()
      setMatchedCandidates(data)
    } catch (e) {
      console.error("Error loading matched candidates", e)
    } finally {
      setCandidatesLoading(false)
    }
  }

  const fetchMarketAnalytics = async () => {
    try {
      const res = await fetch(`${API_URL}/recruiter/market-analytics`)
      const data = await res.json()
      setMarketData(data)
    } catch (e) {
      console.error("Error loading market analytics", e)
    }
  }

  const handlePostJob = async (e) => {
    e.preventDefault()
    setPostLoading(true)
    setPostSuccess('')

    const skillList = jobSkills.split(',').map(s => s.trim()).filter(Boolean)
    if (!jobTitle || skillList.length === 0) {
      setPostLoading(false)
      return
    }

    try {
      const res = await fetch(`${API_URL}/recruiter/posted-jobs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: jobTitle,
          company: user.company || 'Axiata Labs',
          location: jobLocation,
          salary: jobSalary,
          description: jobDescription,
          required_skills: skillList
        })
      })
      
      const data = await res.json()
      if (res.ok) {
        setPostSuccess('Job posting added successfully!')
        // Reset form
        setJobTitle('')
        setJobDescription('')
        setJobSkills('')
        
        // Refresh list
        fetchJobs()
        
        // Select newly added job
        setSelectedJobId(data.job.id)
        
        setTimeout(() => setPostSuccess(''), 4000)
      }
    } catch (e) {
      console.error("Error posting job", e)
    } finally {
      setPostLoading(false)
    }
  }

  const handleShortlist = (candId) => {
    setShortlistedCandIds(prev => {
      const updated = new Set(prev)
      if (updated.has(candId)) {
        updated.delete(candId)
      } else {
        updated.add(candId)
      }
      return updated
    })
  }

  return (
    <div className="flex-1 flex flex-col md:flex-row min-h-screen">
      {/* Sidebar navigation */}
      <aside className="w-full md:w-64 bg-white border-r border-gray-200 p-6 flex flex-col justify-between shrink-0">
        <div>
          <div className="flex items-center space-x-2 mb-8">
            <Logo className="h-8 w-auto" />
          </div>

          <div className="bg-gray-50 border border-gray-100 rounded-xl p-4 mb-6 text-xs">
            <span className="font-bold block text-gray-900 mb-1">Recruiter Profile:</span>
            <p className="text-gray-600 font-semibold">{user.name}</p>
            <p className="text-gray-400 mt-0.5">{user.company}</p>
          </div>

          <nav className="space-y-1">
            <button
              onClick={() => setActiveTab('posts')}
              className={`w-full flex items-center space-x-2 px-3 py-2 text-xs font-semibold rounded-md transition-all ${
                activeTab === 'posts' ? 'bg-brand text-white' : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              <Plus className="h-4 w-4" />
              <span> Post Job Openings</span>
            </button>
            <button
              onClick={() => setActiveTab('candidates')}
              className={`w-full flex items-center space-x-2 px-3 py-2 text-xs font-semibold rounded-md transition-all ${
                activeTab === 'candidates' ? 'bg-brand text-white' : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              <Users className="h-4 w-4" />
              <span> Candidate Matching</span>
            </button>
            <button
              onClick={() => setActiveTab('analytics')}
              className={`w-full flex items-center space-x-2 px-3 py-2 text-xs font-semibold rounded-md transition-all ${
                activeTab === 'analytics' ? 'bg-brand text-white' : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              <BarChart3 className="h-4 w-4" />
              <span> Market Analytics</span>
            </button>
          </nav>
        </div>
      </aside>

      {/* Main content body */}
      <main className="flex-1 flex flex-col bg-gray-50">
        <header className="bg-white border-b border-gray-200 px-6 py-4 flex justify-between items-center shrink-0">
          <div>
            <h1 className="text-xl font-bold text-gray-900">Recruiter Portal</h1>
            <p className="text-xs text-gray-500 mt-0.5">Post requirements, analyze talent pools, and match candidate metrics</p>
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

        <section className="flex-1 p-6 overflow-y-auto">
          {/* TAB 1: POST A JOB */}
          {activeTab === 'posts' && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Form card */}
              <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm lg:col-span-2">
                <h2 className="text-sm font-bold text-gray-900 mb-4">Create New Job Requirement</h2>
                
                {postSuccess && (
                  <div className="mb-4 p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded text-xs text-center font-semibold">
                    {postSuccess}
                  </div>
                )}

                <form onSubmit={handlePostJob} className="space-y-4">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-semibold text-gray-500 mb-1">Job Title</label>
                      <input
                        type="text"
                        required
                        value={jobTitle}
                        onChange={(e) => setJobTitle(e.target.value)}
                        placeholder="e.g. AI Specialist"
                        className="w-full p-2 border border-gray-300 rounded text-xs focus:ring-brand focus:border-brand bg-white"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-gray-500 mb-1">Location</label>
                      <input
                        type="text"
                        required
                        value={jobLocation}
                        onChange={(e) => setJobLocation(e.target.value)}
                        className="w-full p-2 border border-gray-300 rounded text-xs focus:ring-brand focus:border-brand bg-white"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-semibold text-gray-500 mb-1">Salary Range</label>
                      <input
                        type="text"
                        required
                        value={jobSalary}
                        onChange={(e) => setJobSalary(e.target.value)}
                        className="w-full p-2 border border-gray-300 rounded text-xs focus:ring-brand focus:border-brand bg-white"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-gray-500 mb-1">Required Skills (comma separated)</label>
                      <input
                        type="text"
                        required
                        value={jobSkills}
                        onChange={(e) => setJobSkills(e.target.value)}
                        placeholder="e.g. Python, Generative AI, AWS, Git"
                        className="w-full p-2 border border-gray-300 rounded text-xs focus:ring-brand focus:border-brand bg-white"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-gray-500 mb-1">Role Description</label>
                    <textarea
                      value={jobDescription}
                      onChange={(e) => setJobDescription(e.target.value)}
                      placeholder="Enter description..."
                      rows="4"
                      className="w-full p-2 border border-gray-300 rounded text-xs focus:ring-brand focus:border-brand bg-white"
                    />
                  </div>

                  <button
                    type="submit"
                    disabled={postLoading}
                    className="w-full py-2 bg-brand text-white font-semibold rounded text-xs hover:bg-brand-light shadow transition-all disabled:opacity-50"
                  >
                    {postLoading ? 'Adding job requirement...' : 'Post Job Opening'}
                  </button>
                </form>
              </div>

              {/* Sidebar list of posted jobs */}
              <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
                <h3 className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-4">Current Active Openings ({recruiterJobs.length})</h3>
                <div className="space-y-3">
                  {recruiterJobs.map((job) => (
                    <div 
                      key={job.id} 
                      onClick={() => {
                        setSelectedJobId(job.id);
                        setActiveTab('candidates');
                      }}
                      className="p-3 border border-gray-100 rounded-lg hover:border-brand/40 hover:bg-brand/5 transition-all cursor-pointer"
                    >
                      <h4 className="text-xs font-bold text-gray-900">{job.title}</h4>
                      <p className="text-[10px] text-gray-500 mt-0.5">{job.company} • {job.location}</p>
                      <div className="flex flex-wrap gap-1 mt-2">
                        {job.required_skills.slice(0, 3).map((s, i) => (
                          <span key={i} className="px-1 py-0.5 bg-gray-100 border border-gray-200 rounded text-[9px] font-medium text-gray-600">
                            {s}
                          </span>
                        ))}
                        {job.required_skills.length > 3 && (
                          <span className="text-[9px] text-gray-400 font-semibold mt-0.5">+{job.required_skills.length - 3}</span>
                        )}
                      </div>
                    </div>
                  ))}
                  {recruiterJobs.length === 0 && (
                    <p className="text-xs text-gray-400 italic">No job postings created yet.</p>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: CANDIDATE MATCHING */}
          {activeTab === 'candidates' && (
            <div className="space-y-6">
              {/* Select Job dropdown */}
              <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm flex items-center justify-between flex-wrap gap-4">
                <div className="flex items-center space-x-2">
                  <span className="text-xs font-bold text-gray-600">Analyze Matches for Role:</span>
                  <select
                    value={selectedJobId}
                    onChange={(e) => setSelectedJobId(e.target.value)}
                    className="border border-gray-300 rounded p-1.5 text-xs bg-white font-semibold text-brand"
                  >
                    <option value="">-- Choose Job Opening --</option>
                    {recruiterJobs.map((j) => (
                      <option key={j.id} value={j.id}>{j.title} ({j.company})</option>
                    ))}
                  </select>
                </div>
                
                {selectedJobId && (
                  <div className="text-xs text-gray-500">
                    Required: <span className="font-semibold text-gray-700">
                      {recruiterJobs.find(j => j.id === selectedJobId)?.required_skills.join(', ')}
                    </span>
                  </div>
                )}
              </div>

              {/* Candidates list matching */}
              {selectedJobId ? (
                candidatesLoading ? (
                  <div className="h-64 flex items-center justify-center text-sm text-gray-500">Querying CV database & candidate surveys...</div>
                ) : (
                  <div className="space-y-4">
                    {matchedCandidates.map((cand) => {
                      const isShortlisted = shortlistedCandIds.has(cand.id)
                      return (
                        <div key={cand.id} className="bg-white border border-gray-200 rounded-xl p-5 hover:border-brand/40 transition-all shadow-sm flex flex-col sm:flex-row justify-between gap-6">
                          <div className="flex-1 space-y-3">
                            <div className="flex items-center space-x-3">
                              <h3 className="text-sm font-bold text-gray-900">{cand.name}</h3>
                              <span className="px-2 py-0.5 bg-blue-50 text-blue-700 border border-blue-100 rounded text-[9px] font-semibold">
                                {cand.title}
                              </span>
                            </div>
                            
                            <p className="text-xs text-gray-500 font-mono">Email: {cand.email} • Document: {cand.resume_filename}</p>

                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 bg-gray-50/50 border border-gray-150 p-3 rounded-lg text-xs">
                              <div>
                                <span className="font-bold text-emerald-800 uppercase block mb-1">✔️ Matching Skills ({cand.matching_skills.length})</span>
                                <div className="flex flex-wrap gap-1">
                                  {cand.matching_skills.map((s, i) => (
                                    <span key={i} className="px-1.5 py-0.5 bg-emerald-100 text-emerald-800 rounded font-medium text-[10px]">
                                      {s}
                                    </span>
                                  ))}
                                  {cand.matching_skills.length === 0 && <span className="text-[10px] text-gray-400 italic">No skills align.</span>}
                                </div>
                              </div>
                              <div>
                                <span className="font-bold text-red-800 uppercase block mb-1">❌ Missing Required Skills ({cand.missing_skills.length})</span>
                                <div className="flex flex-wrap gap-1">
                                  {cand.missing_skills.map((s, i) => (
                                    <span key={i} className="px-1.5 py-0.5 bg-red-100 text-red-800 rounded font-medium text-[10px]">
                                      {s}
                                    </span>
                                  ))}
                                  {cand.missing_skills.length === 0 && <span className="text-[10px] text-green-700 font-semibold italic">Perfect match!</span>}
                                </div>
                              </div>
                            </div>
                          </div>

                          <div className="flex sm:flex-col items-center justify-between sm:justify-center border-t sm:border-t-0 sm:border-l border-gray-100 pt-4 sm:pt-0 sm:pl-6 gap-4 shrink-0">
                            <div className="text-center sm:mb-2">
                              <span className="text-2xl font-black text-brand block">{cand.match_score}%</span>
                              <span className="text-[9px] font-bold text-gray-400 uppercase tracking-wider block">Match Score</span>
                            </div>

                            <div className="flex space-x-2">
                              <button 
                                onClick={() => handleShortlist(cand.id)}
                                className={`px-3 py-1.5 border rounded text-xs font-semibold transition-all ${
                                  isShortlisted 
                                    ? 'bg-emerald-600 text-white border-emerald-600' 
                                    : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
                                }`}
                              >
                                {isShortlisted ? 'Shortlisted ✓' : 'Shortlist'}
                              </button>
                            </div>
                          </div>
                        </div>
                      )
                    })}
                    {matchedCandidates.length === 0 && (
                      <div className="p-8 text-center text-xs text-gray-500 border border-dashed rounded bg-white">
                        No candidates have matched skills with this job specification.
                      </div>
                    )}
                  </div>
                )
              ) : (
                <div className="p-8 text-center text-xs text-gray-500 border border-dashed rounded bg-white">
                  Please choose a job requirement from the dropdown list above to compute skill compatibility.
                </div>
              )}
            </div>
          )}

          {/* TAB 3: MARKET ANALYTICS */}
          {activeTab === 'analytics' && (
            <div className="space-y-6">
              <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
                <div className="flex items-start space-x-2.5 mb-6 bg-amber-50 border border-amber-200 text-amber-900 p-3.5 rounded-lg">
                  <AlertTriangle className="h-5 w-5 text-amber-700 shrink-0 mt-0.5" />
                  <div>
                    <h3 className="text-xs font-bold text-amber-800 uppercase tracking-wider">Talent Shortage Alert: AI Competencies</h3>
                    <p className="text-xs text-amber-700 mt-1 leading-relaxed">
                      Market analytics from LinkedIn job postings and candidate surveys indicates a steep supply shortage for <strong>Generative AI</strong> and <strong>Prompt Engineering</strong> in Sri Lanka. Expect higher compensation requests and prioritize rapid shortlisting.
                    </p>
                  </div>
                </div>

                <h2 className="text-sm font-bold text-gray-900 mb-4">Tech Skills Market Gap (Aggregate Demand vs Supply)</h2>
                
                <div className="overflow-x-auto">
                  <table className="min-w-full text-xs text-gray-600">
                    <thead className="bg-gray-100 text-gray-700 uppercase font-bold text-[10px]">
                      <tr>
                        <th className="py-2.5 px-4 text-left">Skill Name</th>
                        <th className="py-2.5 px-4 text-center">Market Demand Index</th>
                        <th className="py-2.5 px-4 text-center">Candidate Supply Index</th>
                        <th className="py-2.5 px-4 text-center">Shortage Gap</th>
                        <th className="py-2.5 px-4 text-right">Recruiting Recommendation</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200">
                      {marketData.map((data, index) => {
                        const isSevere = data.gap > 35
                        return (
                          <tr key={index} className="hover:bg-gray-50">
                            <td className="py-3 px-4 font-bold text-gray-900">{data.skill}</td>
                            <td className="py-3 px-4 text-center">
                              <div className="flex items-center justify-center space-x-1.5">
                                <span className="font-semibold">{data.demand}/100</span>
                                <div className="w-16 bg-gray-200 h-1.5 rounded">
                                  <div style={{ width: `${data.demand}%` }} className="bg-blue-600 h-1.5 rounded"></div>
                                </div>
                              </div>
                            </td>
                            <td className="py-3 px-4 text-center">
                              <div className="flex items-center justify-center space-x-1.5">
                                <span className="font-semibold">{data.supply}/100</span>
                                <div className="w-16 bg-gray-200 h-1.5 rounded">
                                  <div style={{ width: `${data.supply}%` }} className="bg-indigo-400 h-1.5 rounded"></div>
                                </div>
                              </div>
                            </td>
                            <td className="py-3 px-4 text-center">
                              <span className={`px-2 py-0.5 rounded font-bold ${
                                isSevere ? 'bg-red-50 text-red-700 border border-red-200' : 'bg-yellow-50 text-yellow-700 border border-yellow-200'
                              }`}>
                                {data.gap} pts gap
                              </span>
                            </td>
                            <td className="py-3 px-4 text-right font-medium text-gray-700">
                              {isSevere ? (
                                <span className="text-red-600 font-semibold">Offer Premium Pay / Train internally</span>
                              ) : (
                                <span className="text-gray-500">Standard market rates</span>
                              )}
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </section>
      </main>
    </div>
  )
}

export default RecruiterDashboard

