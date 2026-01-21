/**
 * Main entry point for Abiqua Asset Management UI.
 * 
 * References:
 * - UX Behavior (#12)
 * - Copy Rules (#13)
 * - UI Domain Adapter Layer
 * 
 * Initializes React application with Vite and fetches data from backend.
 */

import React, { useEffect, useState } from 'react'
import ReactDOM from 'react-dom/client'
import { App } from '../App'
import './index.css'
import { mockActiveDeviceState, mockConversations, mockMessages } from '../fixtures/mockData'
import { createMessageTransport } from '../services/transportFactory'
import { HttpMessageApiService } from '../services/httpMessageApi'
import { checkHealth } from '../services/healthCheck'
import { DeviceApiService } from '../services/deviceApi'
import { ConversationApiService } from '../services/conversationApi'
import { MessageFetchApiService } from '../services/messageFetchApi'
import { ConversationViewModel, DeviceStateViewModel, MessageViewModel } from '../types'

// Get API base URL from environment variable
// Defaults to localhost backend if not set
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

// Derive WebSocket URL from API base URL
const wsUrl = apiBaseUrl.replace(/^http/, 'ws') + '/ws/messages'

// Create message transport (WebSocket preferred, REST polling fallback)
const messageTransport = createMessageTransport({
  wsUrl: wsUrl,
  apiUrl: apiBaseUrl,
  preferredTransport: 'websocket',
})

// Create HTTP message API service
const messageApi = new HttpMessageApiService(apiBaseUrl)

// Create API services
const deviceApi = new DeviceApiService(apiBaseUrl)
const conversationApi = new ConversationApiService(apiBaseUrl)
const messageFetchApi = new MessageFetchApiService(apiBaseUrl)

// Get device ID from mock data (in production, this would come from auth)
// TODO: Replace with actual device ID from authentication
const deviceId = mockActiveDeviceState.device_id

/**
 * Root component that fetches data from backend and renders App.
 */
function Root() {
  const [deviceState, setDeviceState] = useState<DeviceStateViewModel | null>(null)
  const [conversations, setConversations] = useState<ConversationViewModel[]>([])
  const [messagesByConversation, setMessagesByConversation] = useState<
    Record<string, MessageViewModel[]>
  >({})
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    /**
     * Initialize app: health check, fetch device state, messages, and conversations.
     */
    async function initialize() {
      // Health check (development logging only)
      if (import.meta.env.DEV) {
        const isHealthy = await checkHealth(apiBaseUrl)
        if (isHealthy) {
          console.log('Backend health check: OK')
        } else {
          console.log('Backend health check: Failed (backend may be starting)')
        }
      }

      try {
        // Fetch device state first (needed for message/conversation read-only flags)
        const fetchedDeviceState = await deviceApi.getDeviceState(deviceId)
        setDeviceState(fetchedDeviceState)

        // Fetch all messages
        const allMessages = await messageFetchApi.fetchAllMessages(deviceId)

        // Fetch device state first to set read-only flags
        const fetchedDeviceState = await deviceApi.getDeviceState(deviceId)
        setDeviceState(fetchedDeviceState)

        // Group messages by conversation ID
        const messagesByConv: Record<string, MessageViewModel[]> = {}
        const conversationIds = new Set<string>()

        for (const message of allMessages) {
          if (!messagesByConv[message.conversation_id]) {
            messagesByConv[message.conversation_id] = []
          }
          // Set read-only state based on device state
          messagesByConv[message.conversation_id].push({
            ...message,
            is_read_only: fetchedDeviceState.is_read_only,
          })
          conversationIds.add(message.conversation_id)
        }

        // Sort messages in reverse chronological order (newest first)
        for (const convId of Object.keys(messagesByConv)) {
          messagesByConv[convId].sort((a, b) => {
            return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
          })
        }

        setMessagesByConversation(messagesByConv)

        // Fetch conversation info for each unique conversation ID
        const conversationPromises = Array.from(conversationIds).map((convId) =>
          conversationApi.getConversationInfo(convId, deviceId)
        )

        const conversationResults = await Promise.all(conversationPromises)

        // Filter out null results and update with message data
        const fetchedConversations: ConversationViewModel[] = []

        for (let i = 0; i < conversationResults.length; i++) {
          const conv = conversationResults[i]
          if (conv) {
            // Update conversation with message-derived data
            const convId = Array.from(conversationIds)[i]
            const convMessages = messagesByConv[convId] || []
            const lastMessage = convMessages[0] // Newest first

            // Update message read-only state based on device state
            const updatedMessages = convMessages.map((msg) => ({
              ...msg,
              is_read_only: fetchedDeviceState.is_read_only,
            }))
            messagesByConv[convId] = updatedMessages

            fetchedConversations.push({
              ...conv,
              is_read_only: fetchedDeviceState.is_read_only,
              can_send: !fetchedDeviceState.is_read_only && conv.state === 'active',
              send_disabled: fetchedDeviceState.is_read_only || conv.state === 'closed',
              last_message_at: lastMessage?.created_at || null,
              created_at: lastMessage
                ? lastMessage.created_at
                : conv.created_at || new Date().toISOString(),
              last_message_preview: lastMessage
                ? lastMessage.is_failed
                  ? '(Failed)'
                  : lastMessage.state === 'sent'
                    ? '(Queued)'
                    : `Message from ${lastMessage.sender_id.slice(-8)}`
                : undefined,
            })
          }
        }

        // Sort conversations by last_message_at (newest first)
        fetchedConversations.sort((a, b) => {
          const timeA = a.last_message_at ? new Date(a.last_message_at).getTime() : 0
          const timeB = b.last_message_at ? new Date(b.last_message_at).getTime() : 0
          return timeB - timeA
        })

        setConversations(fetchedConversations)
      } catch (error) {
        // Errors handled silently - fall back to mock data if backend unavailable
        if (import.meta.env.DEV) {
          console.log('Backend unavailable, using mock data:', error)
        }

        setDeviceState(mockActiveDeviceState)
        setConversations(mockConversations)
        setMessagesByConversation(mockMessages)
      } finally {
        setIsLoading(false)
      }
    }

    initialize()
  }, [deviceId])

  // Show loading state or fallback to mock data
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-50">
        <p className="text-sm text-gray-500">Loading...</p>
      </div>
    )
  }

  // Use mock data as fallback if device state not loaded
  const finalDeviceState = deviceState || mockActiveDeviceState
  const finalConversations = conversations.length > 0 ? conversations : mockConversations
  const finalMessages =
    Object.keys(messagesByConversation).length > 0
      ? messagesByConversation
      : mockMessages

  return (
    <App
      deviceState={finalDeviceState}
      conversations={finalConversations}
      messagesByConversation={finalMessages}
      messageApi={messageApi}
      messageTransport={messageTransport}
    />
  )
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <Root />
  </React.StrictMode>,
)
