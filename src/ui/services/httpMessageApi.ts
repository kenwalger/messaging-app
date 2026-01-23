/**
 * HTTP message API service implementation for client-side message sending.
 * 
 * References:
 * - API Contracts (#10)
 * - Client-Facing API Boundary
 * - Message Delivery & Reliability docs
 * 
 * Provides real HTTP implementation for sending messages via the backend API.
 * Uses VITE_API_BASE_URL environment variable for API endpoint.
 */

import { MessageApiService } from './messageApi'
import { MessageViewModel } from '../types'
import { encryptionModeStore } from './encryptionMode'
import { encryptMessage, isEncryptionAvailable } from './clientEncryption'

/**
 * HTTP message API service implementation.
 * 
 * Sends messages via POST /api/message/send endpoint.
 * Handles delivery state updates via WebSocket (handled separately by MessageTransport).
 */
export class HttpMessageApiService implements MessageApiService {
  private apiBaseUrl: string
  private deliveryCallbacks = new Map<string, (state: "delivered" | "failed") => void>()

  /**
   * Create HTTP message API service instance.
   * 
   * @param apiBaseUrl API base URL (e.g., "http://127.0.0.1:8000")
   */
  constructor(apiBaseUrl: string) {
    this.apiBaseUrl = apiBaseUrl.replace(/\/$/, '') // Remove trailing slash
  }

  /**
   * Send a message to a conversation.
   * 
   * Per API Contracts (#10), Section 3.3:
   * - POST /api/message/send
   * - Requires X-Device-ID header
   * - Returns message_id and status
   * 
   * Message enters PENDING state immediately (optimistic update).
   * 
   * Encryption handling:
   * - Client mode: Encrypts payload client-side before sending
   * - Server mode: Sends plaintext (backend encrypts)
   * 
   * @param conversationId Conversation ID
   * @param senderId Sender device ID (used for X-Device-ID header)
   * @param content Message content (plaintext)
   * @returns Promise resolving to MessageViewModel in PENDING state
   */
  async sendMessage(
    conversationId: string,
    senderId: string,
    content: string
  ): Promise<MessageViewModel> {
    // Validate inputs
    if (!conversationId || !senderId || !content) {
      throw new Error('Invalid message parameters')
    }

    // Validate payload is not empty after trimming
    const trimmedContent = content.trim()
    if (!trimmedContent) {
      throw new Error('Message content cannot be empty')
    }

    // Get current encryption mode
    const encryptionMode = encryptionModeStore.getMode()

    // Encrypt conditionally based on mode
    let payload: string
    if (encryptionMode === 'client') {
      // Client-side encryption mode: encrypt before sending
      if (!isEncryptionAvailable()) {
        throw new Error('Message could not be encrypted. Web Crypto API not available. Not sent.')
      }
      
      try {
        payload = await encryptMessage(trimmedContent, senderId)
        
        // Log for diagnostics
        if (import.meta.env.DEV) {
          console.log('[HttpMessageApi] Encryption mode: client, Payload type: encrypted')
        }
      } catch (error) {
        // Encryption failed - throw error to prevent sending plaintext
        const errorMessage = error instanceof Error ? error.message : 'Message could not be encrypted. Not sent.'
        throw new Error(errorMessage)
      }
    } else {
      // Server-side encryption mode: send plaintext
      payload = trimmedContent
      
      // Log for diagnostics
      if (import.meta.env.DEV) {
        console.log('[HttpMessageApi] Encryption mode: server, Payload type: plaintext')
      }
    }

    // Prepare request per API Contracts (#10), Section 3.3
    // ALWAYS include conversation_id in request body (required field)
    // Do NOT rely on implicit state or previous /join calls
    const requestBody = {
      conversation_id: conversationId, // REQUIRED: Always include active conversation ID
      payload: payload, // Encrypted (client mode) or plaintext (server mode)
      encryption: encryptionMode, // Encryption mode indicator (for backend logging/diagnostics)
      expiration: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(), // 7 days
    }
    
    // Validate conversation_id is present before sending
    if (!conversationId || !conversationId.trim()) {
      const error = 'conversation_id is required but was not provided'
      if (import.meta.env.DEV) {
        console.error('[HttpMessageApi]', error, { conversationId })
      }
      throw new Error(error)
    }
    
    // Log request details for debugging (always log in production for troubleshooting)
    console.log('[HttpMessageApi] Sending message:', {
      conversation_id: conversationId,
      payload_length: payload.length,
      encryption_mode: encryptionMode,
      api_base_url: this.apiBaseUrl,
    })

    try {
      // Send message via HTTP POST
      const response = await fetch(`${this.apiBaseUrl}/api/message/send`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Device-ID': senderId,
        },
        body: JSON.stringify(requestBody),
      })

      // Check for demo mode auto-create header from backend (check for both success and error responses)
      const autoCreateHeader = response.headers.get('X-Demo-Mode-Auto-Create')
      if (autoCreateHeader === 'true') {
        // Set flag for demo mode banner
        localStorage.setItem('demo_mode_auto_create', 'true')
        console.log('[HttpMessageApi] Demo mode: Conversation was auto-created by backend')
      }
      
      // In demo mode, treat HTTP 200/202 as success (message accepted)
      // WebSocket failures don't block message acceptance
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        const errorMessage = errorData.message || `HTTP ${response.status}: ${response.statusText}`
        const errorCode = errorData.error_code || 'unknown_error'
        
        // Log detailed error for debugging (always log for troubleshooting)
        console.error('[HttpMessageApi] Message send failed:', {
          status: response.status,
          error_code: errorCode,
          message: errorMessage,
          conversation_id: conversationId,
          request_id: errorData.request_id,
        })
        
        throw new Error(errorMessage)
      }

      const responseData = await response.json()
      
      // HTTP 200/202 means message was accepted and queued
      // In demo mode, this is always success (WebSocket optional)
      
      // In demo mode, log demo-mode warnings (non-fatal, message still accepted)
      if (responseData.demo_mode_warning && import.meta.env.DEV) {
        console.log(`[Demo Mode] ${responseData.demo_mode_warning}`)
      }

      // Create message in PENDING state (optimistic update)
      const now = new Date()
      const expiresAt = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000) // 7 days

      const message: MessageViewModel = {
        message_id: responseData.message_id || `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
        sender_id: senderId,
        conversation_id: conversationId,
        state: 'sent', // PENDING state (maps to "sent" in client API)
        created_at: responseData.timestamp || now.toISOString(),
        expires_at: expiresAt.toISOString(),
        is_expired: false,
        is_failed: false,
        is_read_only: false,
        display_state: 'queued', // UI shows "Queued" per UX Behavior (#12), Section 3.3
      }

      return message
    } catch (error) {
      // On error, create message in FAILED state
      const now = new Date()
      const expiresAt = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000)

      const message: MessageViewModel = {
        message_id: `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
        sender_id: senderId,
        conversation_id: conversationId,
        state: 'failed',
        created_at: now.toISOString(),
        expires_at: expiresAt.toISOString(),
        is_expired: false,
        is_failed: true,
        is_read_only: false,
        display_state: 'failed',
      }

      // Notify subscribers of failure
      const callback = this.deliveryCallbacks.get(message.message_id)
      if (callback) {
        callback('failed')
      }

      throw error
    }
  }

  /**
   * Subscribe to delivery state updates for a message.
   * 
   * Note: In this implementation, delivery state updates come from WebSocket transport,
   * not from this service. This method exists for interface compatibility.
   * 
   * @param messageId Message ID to track
   * @param callback Callback with new state
   * @returns Unsubscribe function
   */
  subscribeToDeliveryUpdates(
    messageId: string,
    callback: (newState: "delivered" | "failed") => void
  ): () => void {
    this.deliveryCallbacks.set(messageId, callback)
    return () => {
      this.deliveryCallbacks.delete(messageId)
    }
  }
}
