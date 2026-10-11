import { useEffect, useRef, useState } from 'react'
import {
  Bell,
  Briefcase,
  CheckCircle2,
  Cpu,
  Database,
  FileSearch,
  Info,
  Milestone,
  RefreshCw,
  TrendingUp,
  Users,
  X,
} from 'lucide-react'
import { API_URL } from '../App'
import { getAuthHeaders } from './notificationsApi.js'

const notificationIcons = {
  applicant: [Users, 'bg-emerald-100 text-emerald-600'],
  match: [CheckCircle2, 'bg-emerald-100 text-emerald-600'],
  post: [Briefcase, 'bg-blue-100 text-blue-600'],
  profile: [FileSearch, 'bg-amber-100 text-amber-600'],
  gap: [FileSearch, 'bg-amber-100 text-amber-600'],
  analytics: [TrendingUp, 'bg-purple-100 text-purple-600'],
  market: [TrendingUp, 'bg-blue-100 text-blue-600'],
  career: [Milestone, 'bg-purple-100 text-purple-600'],
  scraper: [Database, 'bg-blue-100 text-blue-600'],
  sync: [RefreshCw, 'bg-emerald-100 text-emerald-600'],
  system: [Cpu, 'bg-amber-100 text-amber-600'],
  pipeline: [RefreshCw, 'bg-blue-100 text-blue-600'],
}

const formatNotificationTime = (value) => {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  const elapsed = Math.max(0, Date.now() - date.getTime())
  const minutes = Math.floor(elapsed / 60000)
  if (minutes < 1) return 'Just now'
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  if (days < 7) return `${days}d ago`
  return date.toLocaleDateString()
}

function NotificationCenter() {
  const [isOpen, setIsOpen] = useState(false)
  const [notifications, setNotifications] = useState([])
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const panelRef = useRef(null)
  const unreadCount = notifications.filter((notification) => !notification.is_read).length

  const loadNotifications = async (showLoading = true) => {
    if (showLoading) setIsLoading(true)
    try {
      const response = await fetch(`${API_URL}/notifications`, { headers: getAuthHeaders() })
      if (!response.ok) throw new Error(`Could not load notifications (HTTP ${response.status})`)
      setNotifications(await response.json())
      setError('')
    } catch (requestError) {
      console.error('Error loading notifications', requestError)
      setError(requestError.message || 'Could not load notifications.')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    Promise.resolve().then(() => loadNotifications(false))
  }, [])

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (panelRef.current && !panelRef.current.contains(event.target)) setIsOpen(false)
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const markAllRead = async () => {
    try {
      const response = await fetch(`${API_URL}/notifications/read-all`, {
        method: 'PATCH',
        headers: getAuthHeaders(),
      })
      if (!response.ok) throw new Error(`Could not mark notifications as read (HTTP ${response.status})`)
      setNotifications((current) => current.map((notification) => ({ ...notification, is_read: true })))
    } catch (requestError) {
      console.error('Error marking notifications as read', requestError)
      setError(requestError.message || 'Could not mark notifications as read.')
    }
  }

  const dismissNotification = async (id) => {
    try {
      const response = await fetch(`${API_URL}/notifications/${id}`, {
        method: 'DELETE',
        headers: getAuthHeaders(),
      })
      if (!response.ok) throw new Error(`Could not delete notification (HTTP ${response.status})`)
      setNotifications((current) => current.filter((notification) => notification.id !== id))
    } catch (requestError) {
      console.error('Error deleting notification', requestError)
      setError(requestError.message || 'Could not delete notification.')
    }
  }

  const clearAll = async () => {
    try {
      const response = await fetch(`${API_URL}/notifications`, {
        method: 'DELETE',
        headers: getAuthHeaders(),
      })
      if (!response.ok) throw new Error(`Could not clear notifications (HTTP ${response.status})`)
      setNotifications([])
    } catch (requestError) {
      console.error('Error clearing notifications', requestError)
      setError(requestError.message || 'Could not clear notifications.')
    }
  }

  return (
    <div className="relative" ref={panelRef}>
      <button
        onClick={() => {
          const shouldOpen = !isOpen
          setIsOpen(shouldOpen)
          if (shouldOpen) loadNotifications()
        }}
        className="relative p-2 rounded-lg text-gray-500 hover:bg-gray-100 hover:text-gray-700 transition-colors focus:outline-none"
        aria-label="Notifications"
        aria-expanded={isOpen}
      >
        <Bell className="h-5 w-5" />
        {unreadCount > 0 && (
          <span className="absolute top-1 right-1 h-4 min-w-4 px-1 flex items-center justify-center rounded-full bg-red-500 text-white text-[9px] font-bold leading-none">
            {unreadCount}
          </span>
        )}
      </button>

      {isOpen && (
        <div className="fixed inset-x-4 top-[72px] sm:absolute sm:inset-auto sm:right-0 sm:top-auto sm:mt-2 sm:w-80 bg-white rounded-xl border border-gray-200 shadow-2xl sm:shadow-xl z-[100] sm:z-50 overflow-hidden">
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
              <button onClick={markAllRead} className="text-[11px] text-brand font-semibold hover:underline">
                Mark all read
              </button>
            )}
          </div>

          {error && (
            <div className="px-4 py-2 text-xs text-red-600 bg-red-50" role="alert">
              {error}
              <button onClick={loadNotifications} className="ml-2 underline font-semibold">Retry</button>
            </div>
          )}

          <ul className="max-h-80 overflow-y-auto divide-y divide-gray-50">
            {isLoading && notifications.length === 0 && (
              <li className="px-4 py-8 text-center text-sm text-gray-400">Loading notifications...</li>
            )}
            {!isLoading && !error && notifications.length === 0 && (
              <li className="px-4 py-8 text-center text-sm text-gray-400">You're all caught up!</li>
            )}
            {notifications.map((notification) => {
              const [Icon, iconColor] = notificationIcons[notification.type] || [Info, 'bg-gray-100 text-gray-600']
              return (
                <li
                  key={notification.id}
                  className={`flex items-start gap-3 px-4 py-3 group transition-colors ${
                    notification.is_read ? 'bg-white' : 'bg-blue-50/40'
                  }`}
                >
                  <div className={`mt-0.5 p-1.5 rounded-full shrink-0 ${iconColor}`}>
                    <Icon className="h-4 w-4" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-1">
                      <p className={`text-xs font-semibold truncate ${notification.is_read ? 'text-gray-700' : 'text-gray-900'}`}>
                        {notification.title}
                        {!notification.is_read && <span className="ml-1.5 inline-block h-1.5 w-1.5 rounded-full bg-blue-500 align-middle" />}
                      </p>
                      <span className="text-[10px] text-gray-400 shrink-0">{formatNotificationTime(notification.created_at)}</span>
                    </div>
                    <p className="text-[11px] text-gray-500 mt-0.5 leading-relaxed line-clamp-2">{notification.body}</p>
                  </div>
                  <button
                    onClick={() => dismissNotification(notification.id)}
                    className="opacity-0 group-hover:opacity-100 mt-0.5 text-gray-300 hover:text-gray-500 transition-opacity shrink-0"
                    aria-label="Delete notification"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                </li>
              )
            })}
          </ul>

          {notifications.length > 0 && (
            <div className="px-4 py-2.5 border-t border-gray-100 text-center">
              <button onClick={clearAll} className="text-[11px] text-gray-400 hover:text-gray-600 font-medium transition-colors">
                Clear all notifications
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default NotificationCenter
