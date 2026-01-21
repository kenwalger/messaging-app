/**
 * Main entry point for Abiqua Asset Management UI.
 * 
 * References:
 * - UX Behavior (#12)
 * - Copy Rules (#13)
 * - UI Domain Adapter Layer
 * 
 * Initializes React application with Vite.
 */

import React from 'react'
import ReactDOM from 'react-dom/client'
import { App } from '../App'
import './index.css'
import { mockActiveDeviceState, mockConversations, mockMessages } from '../fixtures/mockData'
import { createMessageTransport } from '../services/transportFactory'
import { HttpMessageApiService } from '../services/httpMessageApi'

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

// Get device ID from mock data (in production, this would come from auth)
const deviceId = mockActiveDeviceState.device_id

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App
      deviceState={mockActiveDeviceState}
      conversations={mockConversations}
      messagesByConversation={mockMessages}
      messageApi={messageApi}
      messageTransport={messageTransport}
    />
  </React.StrictMode>,
)
