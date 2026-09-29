import { useState, useEffect } from 'react'
import LandingPage from './components/LandingPage.jsx'
import LoginSignup from './components/LoginSignup.jsx'
import SeekerDashboard from './components/SeekerDashboard.jsx'
import RecruiterDashboard from './components/RecruiterDashboard.jsx'
import AdminDashboard from './components/AdminDashboard.jsx'

export const API_URL = 'http://127.0.0.1:5000/api'

export interface User {
  id?: string | number
  name?: string
  email?: string
  role?: 'seeker' | 'recruiter' | 'admin' | string
  current_role?: string
  target_role?: string
  skills?: string
  company?: string
  avatar_url?: string
  [key: string]: any
}

export type ViewType = 'landing' | 'login' | 'signup' | 'dashboard' | 'google-callback'

function App() {
  // Initialize user and view from localStorage if available
  const [user, setUser] = useState<User | null>(() => {
    try {
      const savedUser = localStorage.getItem('emploeralk_user')
      return savedUser ? JSON.parse(savedUser) : null
    } catch {
      localStorage.removeItem('emploeralk_user')
      return null
    }
  })

  const [currentView, setCurrentView] = useState<ViewType>(() => {
    try {
      const savedUser = localStorage.getItem('emploeralk_user')
      return savedUser ? 'dashboard' : 'landing'
    } catch {
      return 'landing'
    }
  })

  // ── Google OAuth callback handler ──────────────────────────────────────────
  useEffect(() => {
    const hash = window.location.hash

    // Detect Google OAuth success: #google-auth?token=...&user=...
    if (hash.startsWith('#google-auth')) {
      const queryString = hash.replace('#google-auth', '')
      const params = new URLSearchParams(queryString.startsWith('?') ? queryString.slice(1) : queryString)

      const token = params.get('token')
      const userRaw = params.get('user')

      if (token && userRaw) {
        try {
          const parsedUser: User = JSON.parse(decodeURIComponent(userRaw))
          // Persist token and user
          localStorage.setItem('emploeralk_token', token)
          localStorage.setItem('emploeralk_user', JSON.stringify(parsedUser))
          // Clear URL fragment
          window.history.replaceState(null, '', window.location.pathname)
          setUser(parsedUser)
          setCurrentView('dashboard')
        } catch (e) {
          console.error('Failed to parse Google auth response:', e)
          window.history.replaceState(null, '', window.location.pathname)
          setCurrentView('login')
        }
      }
    }

    // Detect Google OAuth error: #google-error=...
    if (hash.startsWith('#google-error')) {
      const errorCode = hash.split('=')[1] || 'unknown'
      console.error('Google OAuth error:', errorCode)
      window.history.replaceState(null, '', window.location.pathname)
      setCurrentView('login')
    }
  }, [])

  const handleLogin = (loggedUser: User, token?: string) => {
    setUser(loggedUser)
    localStorage.setItem('emploeralk_user', JSON.stringify(loggedUser))
    if (token) {
      localStorage.setItem('emploeralk_token', token)
    }
    setCurrentView('dashboard')
  }

  const handleLogout = () => {
    setUser(null)
    localStorage.removeItem('emploeralk_user')
    localStorage.removeItem('emploeralk_token')
    setCurrentView('landing')
  }

  const navigateTo = (view: ViewType) => {
    setCurrentView(view)
  }

  // Choose which dashboard to show based on user role
  const renderDashboard = () => {
    if (!user) return <LoginSignup onLogin={handleLogin} onNavigate={navigateTo} isSignup={false} />
    
    switch (user.role) {
      case 'seeker':
        return <SeekerDashboard user={user} onUpdateUser={(u: User) => setUser(u)} onLogout={handleLogout} />
      case 'recruiter':
        return <RecruiterDashboard user={user} onLogout={handleLogout} />
      case 'admin':
        return <AdminDashboard user={user} onLogout={handleLogout} />
      default:
        return (
          <div className="flex flex-col items-center justify-center min-h-screen">
            <p className="text-red-500 font-semibold mb-4">Invalid role associated with this user account.</p>
            <button onClick={handleLogout} className="px-4 py-2 bg-brand text-white rounded">Log Out</button>
          </div>
        )
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {currentView === 'landing' && (
        <LandingPage onNavigate={navigateTo} user={user} onLogout={handleLogout} />
      )}
      {currentView === 'login' && (
        <LoginSignup onLogin={handleLogin} onNavigate={navigateTo} isSignup={false} />
      )}
      {currentView === 'signup' && (
        <LoginSignup onLogin={handleLogin} onNavigate={navigateTo} isSignup={true} />
      )}
      {currentView === 'dashboard' && renderDashboard()}
    </div>
  )
}

export default App
