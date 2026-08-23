import React, { useState } from 'react'
import Logo from './Logo.jsx'
import { API_URL } from '../App.jsx'
import { ArrowLeft, Loader2, Eye, EyeOff } from 'lucide-react'

function LoginSignup({ onLogin, onNavigate, isSignup }) {
  // Input fields state
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState('seeker') // 'seeker', 'recruiter', 'admin'
  
  // Job Seeker signup extras
  const [currentRole, setCurrentRole] = useState('')
  const [targetRole, setTargetRole] = useState('AI Engineer')
  const [skills, setSkills] = useState('')
  
  // Recruiter signup extras
  const [company, setCompany] = useState('')

  // UX controls
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [showPassword, setShowPassword] = useState(false)

  // Quick fill handler
  const handleQuickFill = (testEmail, testPass) => {
    setEmail(testEmail)
    setPassword(testPass)
    setError('')
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const endpoint = isSignup ? `${API_URL}/auth/signup` : `${API_URL}/auth/login`
      const payload = isSignup 
        ? {
            name,
            email,
            password,
            role,
            ...(role === 'seeker' ? { current_role: currentRole, target_role: targetRole, skills } : {}),
            ...(role === 'recruiter' ? { company } : {})
          }
        : { email, password }

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.error || 'Something went wrong. Please check inputs.')
      }

      onLogin(data.user)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex-1 flex flex-col justify-center py-12 px-4 sm:px-6 lg:px-8 bg-gray-50 relative">
      {/* Back button */}
      <button 
        onClick={() => onNavigate('landing')}
        className="absolute top-6 left-6 flex items-center space-x-2 text-sm text-gray-500 hover:text-brand font-medium transition-colors"
      >
        <ArrowLeft className="h-4 w-4" />
        <span>Back to Home</span>
      </button>

      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <Logo className="mx-auto h-12 w-auto" />
        <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
          {isSignup ? 'Create your account' : 'Sign in to your account'}
        </h2>
        <p className="mt-2 text-center text-sm text-gray-600">
          Or{' '}
          <button 
            onClick={() => {
              setError('');
              onNavigate(isSignup ? 'login' : 'signup');
            }}
            className="font-medium text-blue-600 hover:text-blue-500 underline"
          >
            {isSignup ? 'sign in to an existing account' : 'register a new workspace'}
          </button>
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        {/* Predefined credentials helper */}
        {!isSignup && (
          <div className="mb-6 bg-blue-50 border border-blue-200 rounded-lg p-4 text-xs text-blue-800">
            <span className="font-bold block mb-1">💡 Quick-Testing Demo Credentials:</span>
            <div className="space-y-1">
              <div className="flex justify-between items-center py-0.5 border-b border-blue-100">
                <span>Job Seeker: <strong>seeker@emploeralk.com</strong> (pass: password)</span>
                <button 
                  onClick={() => handleQuickFill('seeker@emploeralk.com', 'password')}
                  className="px-1.5 py-0.5 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
                >
                  Fill
                </button>
              </div>
              <div className="flex justify-between items-center py-0.5 border-b border-blue-100">
                <span>Recruiter: <strong>recruiter@emploeralk.com</strong> (pass: password)</span>
                <button 
                  onClick={() => handleQuickFill('recruiter@emploeralk.com', 'password')}
                  className="px-1.5 py-0.5 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
                >
                  Fill
                </button>
              </div>
              <div className="flex justify-between items-center py-0.5">
                <span>Administrator: <strong>admin@emploeralk.com</strong> (pass: password)</span>
                <button 
                  onClick={() => handleQuickFill('admin@emploeralk.com', 'password')}
                  className="px-1.5 py-0.5 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
                >
                  Fill
                </button>
              </div>
            </div>
          </div>
        )}

        <div className="bg-white py-8 px-4 shadow sm:rounded-lg sm:px-10 border border-gray-200">
          <form className="space-y-6" onSubmit={handleSubmit}>
            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 p-3 rounded-lg text-sm text-center">
                {error}
              </div>
            )}

            {isSignup && (
              <>
                {/* Account Name */}
                <div>
                  <label htmlFor="name" className="block text-sm font-medium text-gray-700">Full Name</label>
                  <input
                    id="name"
                    type="text"
                    required
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="e.g. Ruwan Fernando"
                    className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                  />
                </div>

                {/* Role Switcher */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">I am registering as a:</label>
                  <div className="grid grid-cols-2 gap-3">
                    <button
                      type="button"
                      onClick={() => setRole('seeker')}
                      className={`py-2 px-4 border rounded-md text-sm font-medium text-center transition-all ${
                        role === 'seeker'
                          ? 'bg-brand text-white border-brand shadow-sm'
                          : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
                      }`}
                    >
                      Job Seeker
                    </button>
                    <button
                      type="button"
                      onClick={() => setRole('recruiter')}
                      className={`py-2 px-4 border rounded-md text-sm font-medium text-center transition-all ${
                        role === 'recruiter'
                          ? 'bg-brand text-white border-brand shadow-sm'
                          : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
                      }`}
                    >
                      Recruiter
                    </button>
                  </div>
                </div>
              </>
            )}

            {/* Email Address */}
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700">Email Address</label>
              <input
                id="email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
              />
            </div>

            {/* Password */}
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700">Password</label>
              <div className="mt-1 relative">
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600"
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            {/* Role-Specific Sign Up Fields */}
            {isSignup && role === 'seeker' && (
              <div className="space-y-4 border-t border-gray-100 pt-4">
                <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider block">Skill Diagnostics Setup</span>
                
                <div>
                  <label htmlFor="currentRole" className="block text-sm font-medium text-gray-700">Current Role / Status</label>
                  <input
                    id="currentRole"
                    type="text"
                    required
                    value={currentRole}
                    onChange={(e) => setCurrentRole(e.target.value)}
                    placeholder="e.g. Junior Developer, Student"
                    className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                  />
                </div>

                <div>
                  <label htmlFor="targetRole" className="block text-sm font-medium text-gray-700">Target Role</label>
                  <select
                    id="targetRole"
                    value={targetRole}
                    onChange={(e) => setTargetRole(e.target.value)}
                    className="mt-1 block w-full px-3 py-2 border border-gray-300 bg-white rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                  >
                    <option value="AI Engineer">AI Engineer</option>
                    <option value="Machine Learning Engineer">Machine Learning Engineer</option>
                    <option value="Cloud Architect">Cloud Architect</option>
                    <option value="Data Analyst">Data Analyst</option>
                    <option value="Full Stack Developer">Full Stack Developer</option>
                  </select>
                </div>

                <div>
                  <label htmlFor="skills" className="block text-sm font-medium text-gray-700">Current Skills (comma separated)</label>
                  <input
                    id="skills"
                    type="text"
                    required
                    value={skills}
                    onChange={(e) => setSkills(e.target.value)}
                    placeholder="e.g. Python, SQL, Git, HTML, CSS"
                    className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                  />
                  <p className="mt-1 text-xs text-gray-400">Used as your baseline profile for matching computations.</p>
                </div>
              </div>
            )}

            {isSignup && role === 'recruiter' && (
              <div className="space-y-4 border-t border-gray-100 pt-4">
                <div>
                  <label htmlFor="company" className="block text-sm font-medium text-gray-700">Company Name</label>
                  <input
                    id="company"
                    type="text"
                    required
                    value={company}
                    onChange={(e) => setCompany(e.target.value)}
                    placeholder="e.g. Axiata LABS"
                    className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                  />
                </div>
              </div>
            )}

            {/* Submit Button */}
            <div>
              <button
                type="submit"
                disabled={loading}
                className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-brand hover:bg-brand-light focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-all disabled:opacity-50"
              >
                {loading ? (
                  <>
                    <Loader2 className="animate-spin h-5 w-5 mr-2 text-white" />
                    <span>Processing API request...</span>
                  </>
                ) : (
                  <span>{isSignup ? 'Register Account' : 'Sign In'}</span>
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}

export default LoginSignup

