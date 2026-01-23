/**
 * Conversation management utility for auto-creation and joining.
 * 
 * Handles:
 * - Auto-creating a conversation on first load
 * - Storing conversation ID in localStorage
 * - Joining existing conversations by ID
 */

const CONVERSATION_ID_KEY = 'aam_conversation_id'

/**
 * Get stored conversation ID from localStorage.
 * 
 * @returns Conversation ID or null if not stored
 */
export function getStoredConversationId(): string | null {
  if (typeof window === 'undefined') {
    return null
  }

  try {
    return localStorage.getItem(CONVERSATION_ID_KEY)
  } catch (error) {
    return null
  }
}

/**
 * Store conversation ID in localStorage.
 * 
 * @param conversationId Conversation ID to store
 */
export function storeConversationId(conversationId: string): void {
  if (typeof window === 'undefined') {
    return
  }

  try {
    localStorage.setItem(CONVERSATION_ID_KEY, conversationId)
  } catch (error) {
    // Ignore errors (private browsing, etc.)
  }
}

/**
 * Clear stored conversation ID.
 */
export function clearConversationId(): void {
  if (typeof window !== 'undefined') {
    try {
      localStorage.removeItem(CONVERSATION_ID_KEY)
    } catch (error) {
      // Ignore errors
    }
  }
}
