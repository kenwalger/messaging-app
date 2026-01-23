/**
 * ConversationJoin component for joining conversations by ID.
 * 
 * Allows users to:
 * - View current conversation ID
 * - Paste a conversation ID to join from another device
 * 
 * For Heroku deployment: enables multi-device demos.
 */

import React, { useState } from 'react'
import { storeConversationId } from '../services/conversationManager'

export interface ConversationJoinProps {
  /**
   * Current conversation ID (if any)
   */
  currentConversationId: string | null
  
  /**
   * Callback when conversation ID is set/joined
   */
  onConversationJoined: (conversationId: string) => void
}

/**
 * ConversationJoin component for multi-device demos.
 */
export const ConversationJoin: React.FC<ConversationJoinProps> = ({
  currentConversationId,
  onConversationJoined,
}) => {
  const [joinId, setJoinId] = useState('')
  const [error, setError] = useState<string | null>(null)

  const handleJoin = () => {
    const trimmedId = joinId.trim()
    if (!trimmedId) {
      setError('Please enter a conversation ID')
      return
    }

    // Store conversation ID
    storeConversationId(trimmedId)
    onConversationJoined(trimmedId)
    setJoinId('')
    setError(null)
  }

  const handleCopyId = () => {
    if (currentConversationId) {
      navigator.clipboard.writeText(currentConversationId).catch(() => {
        // Fallback for older browsers
        const textArea = document.createElement('textarea')
        textArea.value = currentConversationId
        document.body.appendChild(textArea)
        textArea.select()
        document.execCommand('copy')
        document.body.removeChild(textArea)
      })
    }
  }

  return (
    <div className="border-t border-gray-200 bg-gray-50 p-4">
      <div className="space-y-3">
        {currentConversationId && (
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">
              Current Conversation ID
            </label>
            <div className="flex items-center gap-2">
              <input
                type="text"
                readOnly
                value={currentConversationId}
                className="flex-1 text-xs px-2 py-1 border border-gray-300 rounded bg-white font-mono"
              />
              <button
                onClick={handleCopyId}
                className="text-xs px-2 py-1 border border-gray-300 rounded hover:bg-gray-50"
              >
                Copy
              </button>
            </div>
          </div>
        )}
        
        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">
            Join Conversation
          </label>
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={joinId}
              onChange={(e) => {
                setJoinId(e.target.value)
                setError(null)
              }}
              placeholder="Paste conversation ID"
              className="flex-1 text-xs px-2 py-1 border border-gray-300 rounded"
            />
            <button
              onClick={handleJoin}
              className="text-xs px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              Join
            </button>
          </div>
          {error && (
            <p className="text-xs text-red-600 mt-1">{error}</p>
          )}
        </div>
      </div>
    </div>
  )
}
