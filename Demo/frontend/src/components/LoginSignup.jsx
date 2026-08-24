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

  // Social login placeholder SVGs
  const GoogleIcon = () => (
    <svg className="h-4 w-4 mr-2" viewBox="0 0 24 24" fill="currentColor">
      <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
      <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
      <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z" fill="#FBBC05"/>
      <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z" fill="#EA4335"/>
    </svg>
  )

  const LinkedInIcon = () => (
    <svg className="h-4 w-4 mr-2" viewBox="0 0 24 24" fill="#0077B5">
      <path d="M19 0h-14c-2.761 0-5 2.239-5 5v14c0 2.761 2.239 5 5 5h14c2.762 0 5-2.239 5-5v-14c0-2.761-2.238-5-5-5zm-11 19h-3v-11h3v11zm-1.5-12.268c-.966 0-1.75-.779-1.75-1.75s.784-1.75 1.75-1.75 1.75.779 1.75 1.75-.784 1.75-1.75 1.75zm13.5 12.268h-3v-5.604c0-3.368-4-3.113-4 0v5.604h-3v-11h3v1.765c1.396-2.586 7-2.777 7 2.476v6.759z"/>
    </svg>
  )

  const SocialButtons = () => (
    <>
      {/* Social Divider */}
      <div className="relative my-4">
        <div className="absolute inset-0 flex items-center" aria-hidden="true">
          <div className="w-full border-t border-gray-200"></div>
        </div>
        <div className="relative flex justify-center text-xs uppercase">
          <span className="bg-white px-2 text-gray-400 tracking-wider">Or continue with</span>
        </div>
      </div>

      {/* Social Buttons */}
      <div className="grid grid-cols-2 gap-3">
        <button
          type="button"
          className="w-full inline-flex justify-center items-center py-2 px-4 border border-gray-300 rounded-md shadow-sm bg-white text-xs font-medium text-gray-700 hover:bg-gray-50 transition-colors"
          onClick={() => alert('Google authentication is not configured in this demo.')}
        >
          <GoogleIcon />
          <span>Google</span>
        </button>
        <button
          type="button"
          className="w-full inline-flex justify-center items-center py-2 px-4 border border-gray-300 rounded-md shadow-sm bg-white text-xs font-medium text-gray-700 hover:bg-gray-50 transition-colors"
          onClick={() => alert('LinkedIn authentication is not configured in this demo.')}
        >
          <LinkedInIcon />
          <span>LinkedIn</span>
        </button>
      </div>
    </>
  )

  return (
    <div className={`flex-1 flex flex-col justify-center px-4 sm:px-6 lg:px-8 relative transition-all ${isSignup ? 'py-4' : 'py-12'}`} style={{ backgroundColor: '#e0f4f4' }}>
      {/* Back button */}
      <button 
        onClick={() => onNavigate('landing')}
        className="absolute top-6 left-6 flex items-center space-x-2 text-sm text-gray-500 hover:text-brand font-medium transition-colors"
      >
        <ArrowLeft className="h-4 w-4" />
        <span>Back to Home</span>
      </button>

      {/* Header */}
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <Logo className={`mx-auto w-auto transition-all ${isSignup ? 'h-8' : 'h-12'}`} />
        <h2 className={`text-center font-extrabold text-gray-900 transition-all ${isSignup ? 'mt-2 text-2xl' : 'mt-6 text-3xl'}`}>
          {isSignup ? 'Create your account' : 'Sign in to your account'}
        </h2>
        <p className="mt-1 text-center text-sm text-gray-600">
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

      {/* ── LOGIN PAGE: Form on left, Credentials panel on right ── */}
      {!isSignup && (
        <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-3xl">
          <div className="flex flex-col md:flex-row gap-6 items-start">
            {/* Left: Login Form */}
            <div className="flex-1 bg-white py-8 px-6 shadow sm:rounded-lg border border-gray-200">
              <form className="space-y-5" onSubmit={handleSubmit}>
                {error && (
                  <div className="bg-red-50 border border-red-200 text-red-700 p-3 rounded-lg text-sm text-center">
                    {error}
                  </div>
                )}

                {/* Email */}
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

                {/* Sign In Button */}
                <div>
                  <button
                    type="submit"
                    disabled={loading}
                    className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-brand hover:bg-brand-light focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-all disabled:opacity-50"
                  >
                    {loading ? (
                      <>
                        <Loader2 className="animate-spin h-5 w-5 mr-2 text-white" />
                        <span>Processing...</span>
                      </>
                    ) : (
                      <span>Sign In</span>
                    )}
                  </button>
                </div>

                <SocialButtons />
              </form>
            </div>

            {/* Right: Demo Credentials Panel */}
            <div className="md:w-72 bg-blue-50 border border-blue-200 rounded-lg p-4 text-xs text-blue-800 self-stretch flex flex-col justify-center">
              <span className="font-bold block mb-2 text-sm">💡 Quick-Testing Demo Credentials:</span>
              <div className="space-y-2">
                <div className="flex justify-between items-center py-1 border-b border-blue-100">
                  <div>
                    <span className="font-semibold block">Job Seeker</span>
                    <span className="text-blue-600">seeker@emploeralk.com</span>
                    <span className="text-blue-500 block">(pass: password)</span>
                  </div>
                  <button 
                    onClick={() => handleQuickFill('seeker@emploeralk.com', 'password')}
                    className="ml-2 px-2 py-1 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors text-xs font-medium"
                  >
                    Fill
                  </button>
                </div>
                <div className="flex justify-between items-center py-1 border-b border-blue-100">
                  <div>
                    <span className="font-semibold block">Recruiter</span>
                    <span className="text-blue-600">recruiter@emploeralk.com</span>
                    <span className="text-blue-500 block">(pass: password)</span>
                  </div>
                  <button 
                    onClick={() => handleQuickFill('recruiter@emploeralk.com', 'password')}
                    className="ml-2 px-2 py-1 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors text-xs font-medium"
                  >
                    Fill
                  </button>
                </div>
                <div className="flex justify-between items-center py-1">
                  <div>
                    <span className="font-semibold block">Administrator</span>
                    <span className="text-blue-600">admin@emploeralk.com</span>
                    <span className="text-blue-500 block">(pass: password)</span>
                  </div>
                  <button 
                    onClick={() => handleQuickFill('admin@emploeralk.com', 'password')}
                    className="ml-2 px-2 py-1 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors text-xs font-medium"
                  >
                    Fill
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── SIGNUP PAGE: Two-column form ── */}
      {isSignup && (
        <div className="mt-4 sm:mx-auto sm:w-full sm:max-w-3xl">
          <div className="bg-white py-5 px-4 sm:px-6 shadow sm:rounded-lg border border-gray-200">
            <form className="space-y-4" onSubmit={handleSubmit}>
              {error && (
                <div className="bg-red-50 border border-red-200 text-red-700 p-3 rounded-lg text-sm text-center">
                  {error}
                </div>
              )}

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 md:gap-8">
                {/* Left Column: Core account fields */}
                <div className="space-y-4">
                  {/* Full Name */}
                  <div>
                    <label htmlFor="name" className="block text-sm font-medium text-gray-700">Full Name</label>
                    <input
                      id="name"
                      type="text"
                      required
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      placeholder="e.g. Ruwan Fernando"
                      className="mt-1 block w-full px-3 py-1.5 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                    />
                  </div>

                  {/* Role Switcher */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1.5">I am registering as a:</label>
                    <div className="grid grid-cols-2 gap-3">
                      <button
                        type="button"
                        onClick={() => setRole('seeker')}
                        className={`py-1.5 px-4 border rounded-md text-sm font-medium text-center transition-all ${
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
                        className={`py-1.5 px-4 border rounded-md text-sm font-medium text-center transition-all ${
                          role === 'recruiter'
                            ? 'bg-brand text-white border-brand shadow-sm'
                            : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
                        }`}
                      >
                        Recruiter
                      </button>
                    </div>
                  </div>

                  {/* Email */}
                  <div>
                    <label htmlFor="email" className="block text-sm font-medium text-gray-700">Email Address</label>
                    <input
                      id="email"
                      type="email"
                      required
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="you@example.com"
                      className="mt-1 block w-full px-3 py-1.5 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
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
                        className="block w-full px-3 py-1.5 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
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
                </div>

                {/* Right Column: Role-specific fields + Register button */}
                <div className="space-y-4 md:border-l md:border-gray-200 md:pl-8">
                  {role === 'seeker' && (
                    <div className="space-y-4">
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
                          className="mt-1 block w-full px-3 py-1.5 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                        />
                      </div>

                      <div>
                        <label htmlFor="targetRole" className="block text-sm font-medium text-gray-700">Target Role</label>
                        <select
                          id="targetRole"
                          value={targetRole}
                          onChange={(e) => setTargetRole(e.target.value)}
                          className="mt-1 block w-full px-3 py-1.5 border border-gray-300 bg-white rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
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
                          className="mt-1 block w-full px-3 py-1.5 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                        />
                        <p className="mt-1 text-xs text-gray-400">Used as your baseline profile for matching computations.</p>
                      </div>
                    </div>
                  )}

                  {role === 'recruiter' && (
                    <div className="space-y-4">
                      <div>
                        <label htmlFor="company" className="block text-sm font-medium text-gray-700">Company Name</label>
                        <input
                          id="company"
                          type="text"
                          required
                          value={company}
                          onChange={(e) => setCompany(e.target.value)}
                          placeholder="e.g. Axiata LABS"
                          className="mt-1 block w-full px-3 py-1.5 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                        />
                      </div>
                    </div>
                  )}

                  {/* Register Account Button */}
                  <div className="pt-2">
                    <button
                      type="submit"
                      disabled={loading}
                      className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-brand hover:bg-brand-light focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-all disabled:opacity-50"
                    >
                      {loading ? (
                        <>
                          <Loader2 className="animate-spin h-5 w-5 mr-2 text-white" />
                          <span>Processing...</span>
                        </>
                      ) : (
                        <span>Register Account</span>
                      )}
                    </button>
                  </div>
                </div>
              </div>

              <SocialButtons />
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

export default LoginSignup
