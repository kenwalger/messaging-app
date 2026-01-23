/**
 * DemoModeBanner component for displaying demo mode indicator.
 * 
 * Shows a visible banner when demo mode is enabled, indicating that
 * WebSocket is optional and encryption is enforced.
 * Also shows warning when conversation auto-creation occurs.
 */

import React, { useState, useEffect } from 'react'

export interface DemoModeBannerProps {
  /**
   * Whether demo mode is enabled.
   */
  enabled: boolean
}

/**
 * DemoModeBanner component.
 * 
 * Displays a banner indicating demo mode is active, with clear messaging
 * about WebSocket being optional and encryption being enforced.
 * Shows additional warning when conversation auto-creation occurs.
 */
export const DemoModeBanner: React.FC<DemoModeBannerProps> = ({ enabled }) => {
  const [showAutoCreateWarning, setShowAutoCreateWarning] = useState(false)

  useEffect(() => {
    if (!enabled) {
      return
    }

    // Check for demo_mode_auto_create flag in localStorage
    // This is set by httpMessageApi when backend returns X-Demo-Mode-Auto-Create header
    const checkForAutoCreate = () => {
      const autoCreated = localStorage.getItem('demo_mode_auto_create')
      if (autoCreated === 'true') {
        setShowAutoCreateWarning(true)
        // Clear flag after showing for 10 seconds
        setTimeout(() => {
          localStorage.removeItem('demo_mode_auto_create')
          setShowAutoCreateWarning(false)
        }, 10000)
      }
    }

    // Check on mount and when localStorage changes (via storage event)
    checkForAutoCreate()
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === 'demo_mode_auto_create' && e.newValue === 'true') {
        checkForAutoCreate()
      }
    }
    window.addEventListener('storage', handleStorageChange)
    
    // Also poll for same-tab updates (storage events don't fire for same-tab changes)
    // Use 2-second interval to reduce overhead while still catching updates promptly
    const pollInterval = setInterval(() => {
      checkForAutoCreate()
    }, 2000) // Check every 2 seconds
    
    return () => {
      window.removeEventListener('storage', handleStorageChange)
      clearInterval(pollInterval)
    }
  }, [enabled])

  if (!enabled) {
    return null
  }

  return (
    <div className="bg-yellow-50 border-b border-yellow-200 px-4 py-2">
      <div className="flex items-center gap-2 text-sm text-yellow-800">
        <span className="font-medium">🧪 Demo Mode</span>
        <span className="text-yellow-700">— Messages delivered via HTTP, WebSocket optional</span>
      </div>
      {showAutoCreateWarning && (
        <div className="mt-1 text-xs text-yellow-700">
          ⚠️ Demo mode: Conversation state may reset between sessions
        </div>
      )}
    </div>
  )
}
