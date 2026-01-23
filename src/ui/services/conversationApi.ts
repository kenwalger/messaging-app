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

  /**
   * Create a new conversation.
   * 
   * Calls POST /api/conversation/create endpoint per API Contracts (#10).
   * 
   * @param deviceId Device ID creating the conversation (X-Device-ID header)
   * @param participants List of participant device IDs (optional, deviceId will be auto-included)
   * @returns Promise resolving to ConversationViewModel or null if creation failed
   */
  async createConversation(
    deviceId: string,
    participants?: string[]
  ): Promise<ConversationViewModel | null> {
    try {
      const response = await fetch(`${this.apiBaseUrl}/api/conversation/create`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Device-ID': deviceId,
        },
        body: JSON.stringify({
          participants: participants || [deviceId],
        }),
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const data = await response.json()

      if (data.status !== 'success') {
        return null
      }

      // Map backend response to ConversationViewModel
      return {
        conversation_id: data.conversation_id,
        state: 'active',
        participant_count: data.participants?.length || 1,
        can_send: true,
        is_read_only: false,
        send_disabled: false,
        last_message_at: null,
        created_at: new Date().toISOString(),
        display_name: `Conversation (${data.participants?.length || 1} participants)`,
      }
    } catch (error) {
      // Errors handled silently - will be logged in development
      if (import.meta.env.DEV) {
        console.error('Failed to create conversation:', error)
      }
      return null
    }
  }

  /**
   * Join an existing conversation.
   * 
   * Calls POST /api/conversation/join endpoint per API Contracts (#10).
   * 
   * @param conversationId Conversation ID to join
   * @param deviceId Device ID joining the conversation (X-Device-ID header)
   * @returns Promise resolving to true if joined successfully, false otherwise
   */
  async joinConversation(
    conversationId: string,
    deviceId: string
  ): Promise<boolean> {
    try {
      // Backend expects conversation_id as query parameter or form data
      const url = new URL(`${this.apiBaseUrl}/api/conversation/join`)
      url.searchParams.set('conversation_id', conversationId)

      const response = await fetch(url.toString(), {
        method: 'POST',
        headers: {
          'X-Device-ID': deviceId,
        },
      })

      return response.ok
    } catch (error) {
      // Errors handled silently
      return false
    }
  }

  /**
   * Ensure a conversation exists (idempotent creation).
   * 
   * Calls POST /api/conversation/create with conversation_id to create or retrieve
   * an existing conversation. This guarantees the conversation exists before sending messages.
   * 
   * @param conversationId Conversation ID to ensure exists
   * @param deviceId Device ID (X-Device-ID header)
   * @param participants List of participant device IDs (defaults to [deviceId])
   * @param encryptionMode Encryption mode for the conversation (optional)
   * @returns Promise resolving to ConversationViewModel if successful, null if failed
   */
  async ensureConversation(
    conversationId: string,
    deviceId: string,
    participants?: string[],
    encryptionMode?: string
  ): Promise<ConversationViewModel | null> {
    try {
      const response = await fetch(`${this.apiBaseUrl}/api/conversation/create`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Device-ID': deviceId,
        },
        body: JSON.stringify({
          conversation_id: conversationId,
          participants: participants || [deviceId],
        }),
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        const errorMessage = errorData.message || `HTTP ${response.status}: ${response.statusText}`
        if (import.meta.env.DEV) {
          console.error('[ConversationApi] ensureConversation failed:', {
            conversation_id: conversationId,
            status: response.status,
            error_code: errorData.error_code,
            message: errorMessage,
          })
        }
        return null
      }

      const data = await response.json()

      if (data.status !== 'success') {
        return null
      }

      // Log whether conversation was created or reused (for transparency)
      if (import.meta.env.DEV) {
        const action = data.created === false ? 'reused' : 'created'
        console.log(`[ConversationApi] Conversation ${conversationId} ${action} (idempotent)`)
      }

      // Map backend response to ConversationViewModel
      return {
        conversation_id: data.conversation_id,
        state: 'active',
        participant_count: data.participants?.length || 1,
        can_send: true,
        is_read_only: false,
        send_disabled: false,
        last_message_at: null,
        created_at: new Date().toISOString(),
        display_name: `Conversation (${data.participants?.length || 1} participants)`,
      }
    } catch (error) {
      if (import.meta.env.DEV) {
        console.error('[ConversationApi] ensureConversation error:', error)
      }
      return null
    }
  }
}
