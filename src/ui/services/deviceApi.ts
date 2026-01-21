/**
 * Device API service for fetching device state from backend.
 * 
 * References:
 * - API Contracts (#10)
 * - UI Domain Adapter Layer
 * 
 * Provides methods to fetch device state information from the backend API.
 * Since there's no direct device info endpoint, device state is derived from
 * API responses and message sending capabilities.
 */

import { DeviceStateViewModel } from '../types'

/**
 * Device API service.
 * 
 * Derives device state from backend API responses.
 * Device state is inferred from whether the device can send messages
 * and interact with conversations.
 */
export class DeviceApiService {
  private apiBaseUrl: string

  /**
   * Create device API service instance.
   * 
   * @param apiBaseUrl API base URL (e.g., "http://127.0.0.1:8000")
   */
  constructor(apiBaseUrl: string) {
    this.apiBaseUrl = apiBaseUrl.replace(/\/$/, '') // Remove trailing slash
  }

  /**
   * Get device state view model.
   * 
   * Derives device state by checking if device can receive messages.
   * If device can receive messages, it's assumed to be active.
   * If device cannot receive messages (401/403), it's assumed to be revoked.
   * 
   * @param deviceId Device ID
   * @returns Promise resolving to DeviceStateViewModel
   */
  async getDeviceState(deviceId: string): Promise<DeviceStateViewModel> {
    // Try to fetch messages to determine device state
    // If device is active, it can receive messages
    // If device is revoked, it will get 401/403
    try {
      const response = await fetch(`${this.apiBaseUrl}/api/message/receive`, {
        method: 'GET',
        headers: {
          'X-Device-ID': deviceId,
        },
      })

      // If we can receive messages, device is active
      if (response.ok) {
        return {
          device_id: deviceId,
          is_read_only: false,
          can_send: true,
          can_create_conversations: true,
          can_join_conversations: true,
          display_status: 'Active Messaging',
        }
      }

      // If unauthorized, device might be revoked or invalid
      if (response.status === 401 || response.status === 403) {
        return {
          device_id: deviceId,
          is_read_only: true,
          can_send: false,
          can_create_conversations: false,
          can_join_conversations: false,
          display_status: 'Messaging Disabled',
        }
      }

      // Other errors - assume active but log in development
      if (import.meta.env.DEV) {
        console.log(`Device state check returned ${response.status}, assuming active`)
      }

      return {
        device_id: deviceId,
        is_read_only: false,
        can_send: true,
        can_create_conversations: true,
        can_join_conversations: true,
        display_status: 'Active Messaging',
      }
    } catch (error) {
      // Network errors - assume active (backend might be starting)
      if (import.meta.env.DEV) {
        console.log('Device state check failed, assuming active:', error)
      }

      return {
        device_id: deviceId,
        is_read_only: false,
        can_send: true,
        can_create_conversations: true,
        can_join_conversations: true,
        display_status: 'Active Messaging',
      }
    }
  }
}
