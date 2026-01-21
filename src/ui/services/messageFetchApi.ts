/**
 * Message fetch API service for fetching initial messages from backend.
 * 
 * References:
 * - API Contracts (#10)
 * - UI Domain Adapter Layer
 * 
 * Provides methods to fetch messages from the backend API for initial load.
 */

import { MessageViewModel } from '../types'

/**
 * Message response from backend API.
 */
interface BackendMessage {
  message_id: string
  sender_id: string
  conversation_id: string
  state: 'sent' | 'delivered' | 'failed' | 'expired'
  created_at: string
  expires_at: string
  payload?: string // Hex-encoded payload (not used in UI)
}

/**
 * Receive messages response from backend API.
 */
interface ReceiveMessagesResponse {
  messages: BackendMessage[]
  api_version: string
  timestamp: string
}

/**
 * Message fetch API service.
 * 
 * Fetches messages from backend for initial conversation load.
 */
export class MessageFetchApiService {
  private apiBaseUrl: string

  /**
   * Create message fetch API service instance.
   * 
   * @param apiBaseUrl API base URL (e.g., "http://127.0.0.1:8000")
   */
  constructor(apiBaseUrl: string) {
    this.apiBaseUrl = apiBaseUrl.replace(/\/$/, '') // Remove trailing slash
  }

  /**
   * Fetch messages for a device.
   * 
   * Calls GET /api/message/receive endpoint per API Contracts (#10), Section 3.4.
   * 
   * @param deviceId Device ID for authentication (X-Device-ID header)
   * @param lastReceivedId Optional last received message ID for pagination
   * @returns Promise resolving to array of MessageViewModel
   */
  async fetchMessages(
    deviceId: string,
    lastReceivedId?: string
  ): Promise<MessageViewModel[]> {
    try {
      const url = new URL(`${this.apiBaseUrl}/api/message/receive`)
      if (lastReceivedId) {
        url.searchParams.set('last_received_id', lastReceivedId)
      }

      const response = await fetch(url.toString(), {
        method: 'GET',
        headers: {
          'X-Device-ID': deviceId,
        },
      })

      if (!response.ok) {
        // Errors handled silently - return empty array
        return []
      }

      const data: ReceiveMessagesResponse = await response.json()

      if (!data.messages || !Array.isArray(data.messages)) {
        return []
      }

      // Map backend messages to MessageViewModel
      const now = new Date()
      return data.messages.map((msg) => {
        const expiresAt = new Date(msg.expires_at)
        const isExpired = expiresAt < now

        return {
          message_id: msg.message_id,
          sender_id: msg.sender_id,
          conversation_id: msg.conversation_id,
          state: msg.state,
          created_at: msg.created_at,
          expires_at: msg.expires_at,
          is_expired: isExpired,
          is_failed: msg.state === 'failed',
          is_read_only: false, // Will be set based on device state
          display_state:
            msg.state === 'failed'
              ? 'failed'
              : msg.state === 'expired' || isExpired
                ? 'expired'
                : msg.state === 'sent'
                  ? 'queued'
                  : 'delivered',
        }
      })
    } catch (error) {
      // Network errors - return empty array
      return []
    }
  }

  /**
   * Fetch all messages for a device (multiple pages if needed).
   * 
   * Fetches messages in batches until no more messages are returned.
   * 
   * @param deviceId Device ID for authentication
   * @returns Promise resolving to array of MessageViewModel
   */
  async fetchAllMessages(deviceId: string): Promise<MessageViewModel[]> {
    const allMessages: MessageViewModel[] = []
    let lastReceivedId: string | undefined = undefined
    let hasMore = true

    while (hasMore) {
      const messages = await this.fetchMessages(deviceId, lastReceivedId)

      if (messages.length === 0) {
        hasMore = false
        break
      }

      allMessages.push(...messages)
      lastReceivedId = messages[messages.length - 1].message_id

      // Limit to prevent infinite loops (max 1000 messages)
      if (allMessages.length >= 1000) {
        hasMore = false
        break
      }
    }

    return allMessages
  }
}
