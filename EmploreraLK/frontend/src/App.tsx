import { useState } from 'react'
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
  [key: string]: any
}

export type ViewType = 'landing' | 'login' | 'signup' | 'dashboard'

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

  const handleLogin = (loggedUser: User) => {
    setUser(loggedUser)
    localStorage.setItem('emploeralk_user', JSON.stringify(loggedUser))
    setCurrentView('dashboard')
  }

  const handleLogout = () => {
    setUser(null)
    localStorage.removeItem('emploeralk_user')
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
