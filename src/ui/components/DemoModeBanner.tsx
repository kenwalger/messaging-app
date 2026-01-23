/**
 * DemoModeBanner component for displaying demo mode indicator.
 * 
 * Shows a visible banner when demo mode is enabled, indicating that
 * WebSocket is optional and encryption is enforced.
 */

import React from 'react'

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
 */
export const DemoModeBanner: React.FC<DemoModeBannerProps> = ({ enabled }) => {
  if (!enabled) {
    return null
  }

  return (
    <div className="bg-yellow-50 border-b border-yellow-200 px-4 py-2">
      <div className="flex items-center gap-2 text-sm text-yellow-800">
        <span className="font-medium">🧪 Demo Mode</span>
        <span className="text-yellow-700">— Messages delivered via HTTP, WebSocket optional</span>
      </div>
    </div>
  )
}
