import { useEffect, useState } from 'react'
import { API_URL } from '../App'
import { getAuthHeaders } from './notificationsApi.js'
import { Clock3, ExternalLink, RefreshCw, Search, UserRound } from 'lucide-react'

const requestProfiles = async (query = '') => {
  const params = new URLSearchParams({ limit: '50' })
  if (query.trim()) params.set('query', query.trim())
  const response = await fetch(`${API_URL}/skill-gap/candidates?${params}`, {
    headers: getAuthHeaders(),
  })
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || data.error || `Could not load your profiles (HTTP ${response.status})`)
  return data
}

function CandidateProfileCollection() {
  const [profileUrls, setProfileUrls] = useState('')
  const [collectionRun, setCollectionRun] = useState(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [collectionError, setCollectionError] = useState('')
  const [profiles, setProfiles] = useState([])
  const [profileTotal, setProfileTotal] = useState(0)
  const [searchQuery, setSearchQuery] = useState('')
  const [isLoadingProfiles, setIsLoadingProfiles] = useState(true)
  const [profilesError, setProfilesError] = useState('')

  const loadProfiles = async (query = '') => {
    setIsLoadingProfiles(true)
    setProfilesError('')
    try {
      const data = await requestProfiles(query)
      setProfiles(data.items || [])
      setProfileTotal(data.total || 0)
    } catch (error) {
      setProfilesError(error.message || 'Could not load your stored profiles.')
    } finally {
      setIsLoadingProfiles(false)
    }
  }

  useEffect(() => {
    let isCurrent = true
    requestProfiles()
      .then((data) => {
        if (!isCurrent) return
        setProfiles(data.items || [])
        setProfileTotal(data.total || 0)
      })
      .catch((error) => {
        if (isCurrent) setProfilesError(error.message || 'Could not load your stored profiles.')
      })
      .finally(() => {
        if (isCurrent) setIsLoadingProfiles(false)
      })
    return () => { isCurrent = false }
  }, [])

  const runId = collectionRun?.run_id
  const runStatus = collectionRun?.status
  useEffect(() => {
    if (!runId || !['queued', 'running'].includes(runStatus)) return

    const pollRun = async () => {
      try {
        const response = await fetch(
          `${API_URL}/skill-gap/candidate-collections/${encodeURIComponent(runId)}`,
          { headers: getAuthHeaders() },
        )
        const data = await response.json()
        if (!response.ok) throw new Error(data.detail || data.error || `Could not refresh collection status (HTTP ${response.status})`)
        setCollectionRun(data)
        if (['completed', 'failed'].includes(data.status)) loadProfiles()
      } catch (error) {
        setCollectionError(error.message || 'Could not refresh collection status.')
      }
    }

    const intervalId = window.setInterval(pollRun, 2500)
    return () => window.clearInterval(intervalId)
  }, [runId, runStatus])

  const submitCollection = async (event) => {
    event.preventDefault()
    const urls = profileUrls.split(/[\n,]+/).map((url) => url.trim()).filter(Boolean)
    if (!urls.length) {
      setCollectionError('Enter at least one public profile URL.')
      return
    }
    if (urls.length > 50) {
      setCollectionError('Submit no more than 50 URLs at a time.')
      return
    }

    setIsSubmitting(true)
    setCollectionError('')
    try {
      const response = await fetch(`${API_URL}/skill-gap/candidates/collect`, {
        method: 'POST',
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ profile_urls: urls }),
      })
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail || data.error || `Could not start collection (HTTP ${response.status})`)
      setCollectionRun(data)
      setProfileUrls('')
    } catch (error) {
      setCollectionError(error.message || 'Could not start profile collection.')
    } finally {
      setIsSubmitting(false)
    }
  }

  const isRunActive = ['queued', 'running'].includes(runStatus)

  return (
    <div className="space-y-5">
      <section className="bg-white p-5 sm:p-6 rounded-xl border border-gray-200 shadow-sm" aria-labelledby="my-profile-collection-title">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 id="my-profile-collection-title" className="text-base font-bold text-gray-900">Build your profile from public work</h2>
            <p className="mt-1 max-w-2xl text-xs leading-relaxed text-gray-500">
              Submit your own public GitHub or portfolio URLs to save your skills and projects to your career profile.
            </p>
          </div>
          <span className="rounded border border-gray-200 px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-gray-500">HTTPS · Up to 50 URLs</span>
        </div>

        <form onSubmit={submitCollection} className="mt-4 space-y-3">
          <label htmlFor="my-profile-urls" className="block text-xs font-semibold text-gray-700">Your profile URLs, one per line</label>
          <textarea
            id="my-profile-urls"
            value={profileUrls}
            onChange={(event) => setProfileUrls(event.target.value)}
            rows={3}
            placeholder={'https://github.com/your-username\nhttps://your-portfolio.example'}
            className="w-full resize-y rounded-lg border border-gray-300 bg-gray-50 px-3 py-2.5 text-sm text-gray-800 placeholder:text-gray-400 focus:border-brand focus:outline-none focus:ring-2 focus:ring-brand/15"
            disabled={isSubmitting || isRunActive}
          />
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-[11px] text-gray-500">LinkedIn, private pages, and pages that disallow collection are not supported.</p>
            <button
              type="submit"
              disabled={isSubmitting || isRunActive}
              className="inline-flex items-center gap-2 rounded-md bg-brand px-4 py-2 text-xs font-semibold text-white shadow-sm transition-colors hover:bg-brand-dark disabled:cursor-not-allowed disabled:opacity-50"
            >
              <RefreshCw className={`h-4 w-4 ${isSubmitting || isRunActive ? 'animate-spin' : ''}`} />
              {isSubmitting || isRunActive ? 'Collecting profile' : 'Collect my profile'}
            </button>
          </div>
        </form>

        {collectionError && <p role="alert" className="mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">{collectionError}</p>}

        {collectionRun && (
          <div className="mt-4 border-t border-gray-100 pt-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2 text-xs font-semibold text-gray-800">
                {isRunActive ? <RefreshCw className="h-4 w-4 animate-spin text-brand" /> : <Clock3 className="h-4 w-4 text-gray-400" />}
                <span>Collection {collectionRun.status}</span>
                <span className="font-normal text-gray-500">{collectionRun.collected_count} saved · {collectionRun.failed_count} failed · {collectionRun.requested_count} submitted</span>
              </div>
              <span className="font-mono text-[10px] text-gray-400">{collectionRun.run_id}</span>
            </div>
            {collectionRun.results?.length > 0 && (
              <ul className="mt-3 divide-y divide-gray-100">
                {collectionRun.results.map((result, index) => (
                  <li key={`${result.source_url}-${index}`} className="flex flex-wrap items-start justify-between gap-2 py-2 text-xs">
                    <div className="min-w-0">
                      <p className="truncate font-medium text-gray-800">{result.candidate?.full_name || result.source_url}</p>
                      {result.message && <p className="mt-0.5 text-[11px] text-gray-500">{result.message}</p>}
                    </div>
                    <span className={`shrink-0 rounded px-2 py-0.5 text-[10px] font-semibold ${result.status === 'failed' ? 'bg-red-50 text-red-700' : result.status === 'collected' ? 'bg-emerald-50 text-emerald-700' : 'bg-gray-100 text-gray-600'}`}>
                      {result.status.replaceAll('_', ' ')}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </section>

      <section className="bg-white rounded-xl border border-gray-200 shadow-sm" aria-labelledby="my-saved-profiles-title">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-gray-100 p-4 sm:p-5">
          <div>
            <h2 id="my-saved-profiles-title" className="text-sm font-bold text-gray-900">My collected profile details</h2>
            <p className="mt-1 text-xs text-gray-500">{profileTotal} saved profile{profileTotal === 1 ? '' : 's'}</p>
          </div>
          <form onSubmit={(event) => { event.preventDefault(); loadProfiles(searchQuery) }} className="flex w-full items-center gap-2 sm:w-auto">
            <div className="relative min-w-0 flex-1 sm:w-64">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
              <input
                type="search"
                value={searchQuery}
                onChange={(event) => setSearchQuery(event.target.value)}
                placeholder="Search skills or headline"
                className="w-full rounded-md border border-gray-300 py-2 pl-9 pr-3 text-xs outline-none focus:border-brand focus:ring-2 focus:ring-brand/15"
              />
            </div>
            <button type="submit" disabled={isLoadingProfiles} className="rounded-md border border-gray-300 p-2 text-gray-600 hover:bg-gray-50 disabled:opacity-50" title="Search my profiles" aria-label="Search my profiles">
              <Search className="h-4 w-4" />
            </button>
            <button type="button" onClick={() => loadProfiles(searchQuery)} disabled={isLoadingProfiles} className="rounded-md border border-gray-300 p-2 text-gray-600 hover:bg-gray-50 disabled:opacity-50" title="Refresh my profiles" aria-label="Refresh my profiles">
              <RefreshCw className={`h-4 w-4 ${isLoadingProfiles ? 'animate-spin' : ''}`} />
            </button>
          </form>
        </div>

        {profilesError && <p role="alert" className="m-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">{profilesError}</p>}
        {isLoadingProfiles ? (
          <div className="p-8 text-center text-xs text-gray-500">Loading your saved profile details...</div>
        ) : profiles.length ? (
          <ul className="divide-y divide-gray-100">
            {profiles.map((profile) => (
              <li key={profile.id} className="flex flex-col gap-3 p-4 sm:flex-row sm:items-start sm:justify-between sm:p-5">
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <UserRound className="h-4 w-4 text-brand" />
                    <h3 className="text-sm font-semibold text-gray-900">{profile.full_name || 'Unnamed profile'}</h3>
                    <span className="rounded bg-gray-100 px-2 py-0.5 text-[10px] font-semibold text-gray-600">{profile.source}</span>
                  </div>
                  {profile.headline && <p className="mt-1 text-xs text-gray-600">{profile.headline}</p>}
                  {profile.location && <p className="mt-1 text-[11px] text-gray-500">{profile.location}</p>}
                  {profile.skills?.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {profile.skills.map((skill) => <span key={skill} className="rounded border border-emerald-100 bg-emerald-50 px-2 py-0.5 text-[10px] font-medium text-emerald-800">{skill}</span>)}
                    </div>
                  )}
                  {profile.projects?.length > 0 && <p className="mt-2 text-[11px] text-gray-500">{profile.projects.length} public project{profile.projects.length === 1 ? '' : 's'}</p>}
                </div>
                <a href={profile.source_url} target="_blank" rel="noopener noreferrer" className="inline-flex shrink-0 items-center gap-1.5 text-xs font-semibold text-brand hover:underline">
                  View source <ExternalLink className="h-3.5 w-3.5" />
                </a>
              </li>
            ))}
          </ul>
        ) : (
          <div className="p-8 text-center text-xs text-gray-500">No collected profiles yet.</div>
        )}
      </section>
    </div>
  )
}

export default CandidateProfileCollection