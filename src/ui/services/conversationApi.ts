/**
 * Conversation API service for fetching conversation data from backend.
 * 
 * References:
 * - API Contracts (#10)
 * - UI Domain Adapter Layer
 * 
 * Provides methods to fetch conversation information from the backend API.
 */

import { ConversationViewModel } from '../types'

/**
 * Conversation info response from backend API.
 */
interface ConversationInfoResponse {
  status: string
  conversation_id: string
  state: 'active' | 'closed'
  participants: string[]
  participant_count: number
  is_participant: boolean
}

/**
 * Conversation API service.
 * 
 * Fetches conversation data from backend endpoints.
 */
export class ConversationApiService {
  private apiBaseUrl: string

  /**
   * Create conversation API service instance.
   * 
   * @param apiBaseUrl API base URL (e.g., "http://127.0.0.1:8000")
   */
  constructor(apiBaseUrl: string) {
    this.apiBaseUrl = apiBaseUrl.replace(/\/$/, '') // Remove trailing slash
  }

  /**
   * Get conversation information.
   * 
   * Calls GET /api/conversation/info endpoint per API Contracts (#10).
   * 
   * @param conversationId Conversation ID
   * @param deviceId Device ID for authentication (X-Device-ID header)
   * @returns Promise resolving to ConversationViewModel or null if not found
   */
  async getConversationInfo(
    conversationId: string,
    deviceId: string
  ): Promise<ConversationViewModel | null> {
    try {
      const url = new URL(`${this.apiBaseUrl}/api/conversation/info`)
      url.searchParams.set('conversation_id', conversationId)

      const response = await fetch(url.toString(), {
        method: 'GET',
        headers: {
          'X-Device-ID': deviceId,
        },
      })

      if (!response.ok) {
        if (response.status === 404) {
          return null
        }
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const data: ConversationInfoResponse = await response.json()

      if (data.status !== 'success') {
        return null
      }

      // Map backend response to ConversationViewModel
      // Derive UX flags per UI Domain Adapter Layer
      const isReadOnly = false // Will be set based on device state
      const canSend = !isReadOnly && data.state === 'active'
      const sendDisabled = isReadOnly || data.state === 'closed'

      return {
        conversation_id: data.conversation_id,
        state: data.state,
        participant_count: data.participant_count,
        can_send: canSend,
        is_read_only: isReadOnly,
        send_disabled: sendDisabled,
        last_message_at: null, // Not provided by conversation/info endpoint
        created_at: new Date().toISOString(), // Not provided by conversation/info endpoint
        display_name:
          data.participant_count > 1
            ? `Conversation (${data.participant_count} participants)`
            : 'Conversation',
      }
    } catch (error) {
      // Errors handled silently - will be logged in development
      return null
    }
  }
}
