import React from 'react'
import Logo from './Logo.jsx'
import { TrendingUp, FileSearch, Milestone, CheckSquare, ShieldCheck, Database, Award } from 'lucide-react'

function LandingPage({ onNavigate, user, onLogout }) {
  return (
    <div className="flex flex-col min-h-screen">
      {/* Navigation Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16 items-center">
            <div className="flex items-center space-x-3 cursor-pointer" onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}>
              <Logo className="h-10 w-auto" />
            </div>
            
            <nav className="hidden md:flex space-x-8 text-sm font-medium text-gray-600">
              <a href="#features" className="hover:text-brand transition-colors">Platform Modules</a>
              <a href="#data-sources" className="hover:text-brand transition-colors">Data Collection</a>
              <a href="#statistics" className="hover:text-brand transition-colors">Metrics</a>
            </nav>

            <div className="flex items-center space-x-4">
              {user ? (
                <>
                  <button 
                    onClick={() => onNavigate('dashboard')}
                    className="px-4 py-2 text-sm font-medium bg-brand text-white rounded-md hover:bg-brand-light transition-all shadow-sm"
                  >
                    Go to Dashboard
                  </button>
                  <button 
                    onClick={onLogout}
                    className="px-4 py-2 text-sm font-medium text-gray-700 border border-gray-300 rounded-md hover:bg-gray-50 transition-all"
                  >
                    Log Out
                  </button>
                </>
              ) : (
                <>
                  <button 
                    onClick={() => onNavigate('login')}
                    className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-brand transition-colors"
                  >
                    Sign In
                  </button>
                  <button 
                    onClick={() => onNavigate('signup')}
                    className="px-4 py-2 text-sm font-medium bg-brand text-white rounded-md hover:bg-brand-light transition-all shadow-sm"
                  >
                    Get Started
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="relative bg-gradient-to-br from-brand-dark to-brand text-white py-20 px-4 sm:px-6 lg:px-8">
        <div className="absolute inset-0 opacity-10 bg-[radial-gradient(#ffffff_1px,transparent_1px)] [background-size:16px_16px]"></div>
        <div className="max-w-5xl mx-auto text-center relative z-10">
          <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-brand-accent/30 text-blue-200 border border-brand-accent/50 mb-6">
            AI-Driven Recruiting & Pathing
          </span>
          <h1 className="text-4xl sm:text-5xl md:text-6xl font-extrabold tracking-tight mb-6">
            Align Your Skills with the <br/>
            <span className="text-blue-400">Future Job Market</span>
          </h1>
          <p className="text-lg sm:text-xl text-gray-300 max-w-3xl mx-auto mb-10 leading-relaxed">
            Emploeralk is an intelligent recruiter and job alignment platform that maps talent profiles to real industry demands. We analyze data from LinkedIn, Indeed, and TopJobs.lk to find your skill gaps and pave your career roadmap.
          </p>
          <div className="flex flex-col sm:flex-row justify-center items-center gap-4">
            <button
              onClick={() => onNavigate(user ? 'dashboard' : 'signup')}
              className="w-full sm:w-auto px-8 py-4 text-base font-medium bg-blue-500 hover:bg-blue-600 text-white rounded-lg shadow-lg hover:shadow-xl transition-all"
            >
              Start Skill Diagnostics
            </button>
            <button
              onClick={() => {
                if(user) onNavigate('dashboard');
                else onNavigate('login');
              }}
              className="w-full sm:w-auto px-8 py-4 text-base font-medium bg-transparent border border-gray-400 hover:bg-white/10 text-white rounded-lg transition-all"
            >
              Enterprise Portal
            </button>
          </div>
        </div>
      </section>

      {/* Modules Grid */}
      <section id="features" className="py-20 bg-gray-50 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-gray-900 sm:text-4xl">Platform Core Modules</h2>
            <p className="mt-4 text-lg text-gray-600 max-w-2xl mx-auto">
              Our system coordinates four specialized intelligence engines to optimize the talent lifecycle.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            {/* Module 1 */}
            <div className="bg-white p-8 rounded-xl shadow-sm border border-gray-100 hover:shadow-md transition-all group">
              <div className="p-3 bg-blue-50 text-blue-600 rounded-lg w-fit group-hover:bg-blue-600 group-hover:text-white transition-all">
                <TrendingUp className="h-6 w-6" />
              </div>
              <h3 className="mt-6 text-xl font-semibold text-gray-900">Job Demand Forecasting</h3>
              <p className="mt-3 text-sm text-gray-600 leading-relaxed">
                Aggregates scraped listings from major platforms to output predictive trend analysis on ascending and descending roles.
              </p>
            </div>

            {/* Module 2 */}
            <div className="bg-white p-8 rounded-xl shadow-sm border border-gray-100 hover:shadow-md transition-all group">
              <div className="p-3 bg-indigo-50 text-indigo-600 rounded-lg w-fit group-hover:bg-indigo-600 group-hover:text-white transition-all">
                <FileSearch className="h-6 w-6" />
              </div>
              <h3 className="mt-6 text-xl font-semibold text-gray-900">Skill Gap Discovery</h3>
              <p className="mt-3 text-sm text-gray-600 leading-relaxed">
                Compares your CV details and surveys against modern vacancy requirements to pinpoint missing technological stack items.
              </p>
            </div>

            {/* Module 3 */}
            <div className="bg-white p-8 rounded-xl shadow-sm border border-gray-100 hover:shadow-md transition-all group">
              <div className="p-3 bg-emerald-50 text-emerald-600 rounded-lg w-fit group-hover:bg-emerald-600 group-hover:text-white transition-all">
                <Milestone className="h-6 w-6" />
              </div>
              <h3 className="mt-6 text-xl font-semibold text-gray-900">Career Path Planning</h3>
              <p className="mt-3 text-sm text-gray-600 leading-relaxed">
                Establishes step-by-step milestone roadmaps and matches you with specific learning content from Coursera.
              </p>
            </div>

            {/* Module 4 */}
            <div className="bg-white p-8 rounded-xl shadow-sm border border-gray-100 hover:shadow-md transition-all group">
              <div className="p-3 bg-purple-50 text-purple-600 rounded-lg w-fit group-hover:bg-purple-600 group-hover:text-white transition-all">
                <CheckSquare className="h-6 w-6" />
              </div>
              <h3 className="mt-6 text-xl font-semibold text-gray-900">Job Matching Engine</h3>
              <p className="mt-3 text-sm text-gray-600 leading-relaxed">
                Computes a compatibility coefficient matching profiles against harvested live postings to optimize fit and hiring time.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Data Source Pipeline */}
      <section id="data-sources" className="py-20 bg-white px-4 sm:px-6 lg:px-8 border-t border-gray-100">
        <div className="max-w-7xl mx-auto flex flex-col lg:flex-row items-center gap-12">
          <div className="lg:w-1/2">
            <span className="text-xs font-semibold tracking-wider text-brand uppercase">Integrated Data Pipeline</span>
            <h2 className="text-3xl font-bold text-gray-900 mt-2 sm:text-4xl">Multi-Platform Gathering</h2>
            <p className="mt-4 text-gray-600 leading-relaxed">
              Emploeralk continuously gathers, processes, and structured datasets from external endpoints to populate its diagnostic algorithms. It connects with major channels to support matching calculations:
            </p>
            <div className="mt-8 space-y-4">
              <div className="flex items-start space-x-3">
                <div className="mt-1 bg-green-100 text-green-700 p-1.5 rounded-full">
                  <Database className="h-4 w-4" />
                </div>
                <div>
                  <h4 className="font-semibold text-gray-900">Job Boards</h4>
                  <p className="text-sm text-gray-600">Scrapes requirements, salaries, and levels from LinkedIn, TopJobs.lk, and Indeed.</p>
                </div>
              </div>
              <div className="flex items-start space-x-3">
                <div className="mt-1 bg-green-100 text-green-700 p-1.5 rounded-full">
                  <Award className="h-4 w-4" />
                </div>
                <div>
                  <h4 className="font-semibold text-gray-900">Online Courses</h4>
                  <p className="text-sm text-gray-600">Indexes skills taught, duration, and ratings from Coursera to suggest target curriculum courses.</p>
                </div>
              </div>
              <div className="flex items-start space-x-3">
                <div className="mt-1 bg-green-100 text-green-700 p-1.5 rounded-full">
                  <ShieldCheck className="h-4 w-4" />
                </div>
                <div>
                  <h4 className="font-semibold text-gray-900">Candidate Surveys & CV Uploads</h4>
                  <p className="text-sm text-gray-600">Gathers offline skills assessments, cv uploads, and surveys responses to build profiles.</p>
                </div>
              </div>
            </div>
          </div>
          
          <div className="lg:w-1/2 bg-gradient-to-tr from-gray-900 to-brand-dark p-8 rounded-2xl text-white shadow-xl flex flex-col justify-between min-h-[300px]">
            <div>
              <div className="flex space-x-2 mb-6">
                <span className="h-3 w-3 rounded-full bg-red-500"></span>
                <span className="h-3 w-3 rounded-full bg-yellow-500"></span>
                <span className="h-3 w-3 rounded-full bg-green-500"></span>
              </div>
              <p className="font-mono text-xs text-blue-400 mb-2">// Scraper Engine Logs (Prototype Simulation)</p>
              <p className="font-mono text-sm mb-1 text-gray-300">&gt; GET /linkedin-scraper/run ... <span className="text-green-400">200 OK</span></p>
              <p className="font-mono text-sm mb-1 text-gray-300">&gt; Collected 142 new jobs from linkedin.com</p>
              <p className="font-mono text-sm mb-1 text-gray-300">&gt; GET /coursera-api/sync ... <span className="text-green-400">200 OK</span></p>
              <p className="font-mono text-sm mb-1 text-gray-300">&gt; Synced 50 courses mapping to 18 active skills</p>
              <p className="font-mono text-sm mb-4 text-gray-300">&gt; Survey collector: parsed 34 CV profiles</p>
              <p className="font-mono text-xs text-emerald-400 blink">&gt; Listening on port 5000 ...</p>
            </div>
            <div className="mt-6 border-t border-white/10 pt-4 flex justify-between text-xs text-gray-400 font-mono">
              <span>DB Status: Connected</span>
              <span>Platform: Emploeralk AI</span>
            </div>
          </div>
        </div>
      </section>

      {/* Statistics Section */}
      <section id="statistics" className="py-20 bg-gray-50 px-4 sm:px-6 lg:px-8 border-b border-gray-100">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
            <div className="bg-white p-6 rounded-lg border border-gray-100 shadow-sm">
              <p className="text-4xl font-extrabold text-brand">350+</p>
              <p className="text-sm font-semibold text-gray-500 uppercase mt-2">Vacancies Scraped</p>
            </div>
            <div className="bg-white p-6 rounded-lg border border-gray-100 shadow-sm">
              <p className="text-4xl font-extrabold text-brand">50+</p>
              <p className="text-sm font-semibold text-gray-500 uppercase mt-2">Courses Indexed</p>
            </div>
            <div className="bg-white p-6 rounded-lg border border-gray-100 shadow-sm">
              <p className="text-4xl font-extrabold text-brand">100%</p>
              <p className="text-sm font-semibold text-gray-500 uppercase mt-2">Skill Gap Analysis</p>
            </div>
            <div className="bg-white p-6 rounded-lg border border-gray-100 shadow-sm">
              <p className="text-4xl font-extrabold text-brand">&lt; 1s</p>
              <p className="text-sm font-semibold text-gray-500 uppercase mt-2">Matching Coefficient Speed</p>
            </div>
          </div>
        </div>
      </section>

      {/* Call to action */}
      <section className="bg-white py-16 px-4 text-center">
        <h2 className="text-3xl font-bold text-gray-900">Ready to explore Emploeralk?</h2>
        <p className="text-gray-600 mt-2 max-w-xl mx-auto">Sign up for a free prototype demo account and see how our logic matches skills instantly.</p>
        <div className="mt-8 flex justify-center space-x-4">
          <button 
            onClick={() => onNavigate('signup')} 
            className="px-6 py-3 bg-brand text-white font-medium rounded-lg hover:bg-brand-light transition-all shadow-md"
          >
            Create Account
          </button>
          <button 
            onClick={() => onNavigate('login')} 
            className="px-6 py-3 border border-gray-300 font-medium rounded-lg hover:bg-gray-50 transition-all text-gray-700"
          >
            Login to Panel
          </button>
        </div>
      </section>

      {/* Footer */}
      <footer className="mt-auto bg-brand-dark text-gray-400 py-8 px-4 border-t border-white/5">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center text-sm">
          <div className="flex items-center space-x-2">
            <Logo className="h-6 w-auto" light={true} />
            <span className="font-semibold text-white">Emploeralk</span>
            <span>© 2026. All rights reserved.</span>
          </div>
          <div className="flex space-x-6 mt-4 md:mt-0">
            <a href="#features" className="hover:text-white transition-colors">Features</a>
            <a href="#data-sources" className="hover:text-white transition-colors">Data Pipeline</a>
            <span>Prototype Version 1.5</span>
          </div>
        </div>
      </footer>
    </div>
  )
}

export default LandingPage

