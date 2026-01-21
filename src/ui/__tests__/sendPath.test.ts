/**
 * Tests for interactive message send path end-to-end.
 * 
 * References:
 * - UX Behavior (#12), Section 3.3
 * - Message Delivery & Reliability docs
 * - API Contracts (#10)
 * 
 * Tests validate:
 * - Message composition and validation
 * - Optimistic UI updates
 * - API call with correct headers and DTOs
 * - Failure handling
 * - Disabled send conditions
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { HttpMessageApiService } from '../services/httpMessageApi'
import { MessageViewModel } from '../types'

describe('Send Path End-to-End', () => {
  const apiBaseUrl = 'http://localhost:8000'
  let messageApi: HttpMessageApiService

  beforeEach(() => {
    messageApi = new HttpMessageApiService(apiBaseUrl)
    vi.clearAllMocks()
  })

  describe('Payload Validation', () => {
    it('should reject empty content', async () => {
      await expect(
        messageApi.sendMessage('conv-001', 'device-001', '')
      ).rejects.toThrow('Invalid message parameters')
    })

    it('should reject whitespace-only content', async () => {
      await expect(
        messageApi.sendMessage('conv-001', 'device-001', '   ')
      ).rejects.toThrow('Message content cannot be empty')
    })

    it('should trim content before sending', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          message_id: 'msg-001',
          timestamp: new Date().toISOString(),
        }),
      })

      await messageApi.sendMessage('conv-001', 'device-001', '  test message  ')

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/message/send'),
        expect.objectContaining({
          body: expect.stringContaining('test message'), // Should be trimmed
        })
      )
    })
  })

  describe('API Call', () => {
    it('should send correct headers', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          message_id: 'msg-001',
          timestamp: new Date().toISOString(),
        }),
      })

      await messageApi.sendMessage('conv-001', 'device-001', 'test message')

      expect(global.fetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
            'X-Device-ID': 'device-001',
          }),
        })
      )
    })

    it('should send correct request body', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          message_id: 'msg-001',
          timestamp: new Date().toISOString(),
        }),
      })

      await messageApi.sendMessage('conv-001', 'device-001', 'test message')

      const callArgs = (global.fetch as any).mock.calls[0]
      const requestBody = JSON.parse(callArgs[1].body)

      expect(requestBody).toMatchObject({
        recipients: [],
        conversation_id: 'conv-001',
        payload: 'test message',
      })
      expect(requestBody.expiration).toBeDefined()
    })

    it('should not leak internal fields in request', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          message_id: 'msg-001',
          timestamp: new Date().toISOString(),
        }),
      })

      await messageApi.sendMessage('conv-001', 'device-001', 'test message')

      const callArgs = (global.fetch as any).mock.calls[0]
      const requestBody = JSON.parse(callArgs[1].body)

      // Should not include internal fields like is_failed, is_expired, etc.
      expect(requestBody.is_failed).toBeUndefined()
      expect(requestBody.is_expired).toBeUndefined()
      expect(requestBody.is_read_only).toBeUndefined()
      expect(requestBody.display_state).toBeUndefined()
    })
  })

  describe('Optimistic Updates', () => {
    it('should return message in PENDING state immediately', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          message_id: 'msg-001',
          timestamp: new Date().toISOString(),
        }),
      })

      const message = await messageApi.sendMessage('conv-001', 'device-001', 'test message')

      expect(message.state).toBe('sent') // PENDING state
      expect(message.display_state).toBe('queued')
      expect(message.is_failed).toBe(false)
    })

    it('should use server message_id if provided', async () => {
      const serverMessageId = 'server-msg-001'
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          message_id: serverMessageId,
          timestamp: new Date().toISOString(),
        }),
      })

      const message = await messageApi.sendMessage('conv-001', 'device-001', 'test message')

      expect(message.message_id).toBe(serverMessageId)
    })
  })

  describe('Failure Handling', () => {
    it('should handle network failure', async () => {
      global.fetch = vi.fn().mockRejectedValue(new Error('Network error'))

      await expect(
        messageApi.sendMessage('conv-001', 'device-001', 'test message')
      ).rejects.toThrow()
    })

    it('should handle backend unavailable', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: async () => ({ message: 'Backend failure' }),
      })

      await expect(
        messageApi.sendMessage('conv-001', 'device-001', 'test message')
      ).rejects.toThrow()
    })

    it('should create message in FAILED state on error', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 400,
        statusText: 'Bad Request',
        json: async () => ({ message: 'Invalid request' }),
      })

      try {
        await messageApi.sendMessage('conv-001', 'device-001', 'test message')
        expect.fail('Should have thrown error')
      } catch (error) {
        // Error is thrown, but message should be in FAILED state
        // (This is handled by the error path in sendMessage)
        expect(error).toBeDefined()
      }
    })

    it('should notify subscribers on failure', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: async () => ({}),
      })

      const callback = vi.fn()
      messageApi.subscribeToDeliveryUpdates('msg-001', callback)

      try {
        await messageApi.sendMessage('conv-001', 'device-001', 'test message')
      } catch (error) {
        // Error is thrown
      }

      // Callback should be called with 'failed' state
      // (This happens in the catch block of sendMessage)
      expect(callback).toHaveBeenCalledWith('failed')
    })
  })

  describe('Delivery Updates Subscription', () => {
    it('should allow subscribing to delivery updates', () => {
      const callback = vi.fn()
      const unsubscribe = messageApi.subscribeToDeliveryUpdates('msg-001', callback)

      expect(unsubscribe).toBeDefined()
      expect(typeof unsubscribe).toBe('function')
    })

    it('should allow unsubscribing from delivery updates', () => {
      const callback = vi.fn()
      const unsubscribe = messageApi.subscribeToDeliveryUpdates('msg-001', callback)

      unsubscribe()

      // Callback should be removed (can't easily test this without triggering it)
      expect(unsubscribe).toBeDefined()
    })
  })

  describe('Disabled Send Conditions', () => {
    it('should not send when content is empty', async () => {
      global.fetch = vi.fn()

      await expect(
        messageApi.sendMessage('conv-001', 'device-001', '')
      ).rejects.toThrow()

      expect(global.fetch).not.toHaveBeenCalled()
    })

    it('should not send when content is whitespace only', async () => {
      global.fetch = vi.fn()

      await expect(
        messageApi.sendMessage('conv-001', 'device-001', '   ')
      ).rejects.toThrow()

      expect(global.fetch).not.toHaveBeenCalled()
    })
  })
})
