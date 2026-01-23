/**
 * Message API service interface for client-side message sending.
 * 
 * References:
 * - API Contracts (#10)
 * - Client-Facing API Boundary (latest)
 * - Message Delivery & Reliability docs
 * 
 * Provides interface for sending messages via the client API adapter.
 * In production, this would integrate with the actual HTTP client.
 */

import { MessageViewModel } from "../types";

/**
 * Message API service interface.
 * 
 * Handles message sending and delivery state updates.
 * No content logged or leaked per deterministic rules.
 */
export interface MessageApiService {
  /**
   * Send a message to a conversation.
   * 
   * Per deterministic rules:
   * - Message enters PENDING state immediately (optimistic update)
   * - UI updates optimistically
   * - Delivery state transitions handled via callbacks
   * 
   * @param conversationId Conversation ID
   * @param senderId Sender device ID
   * @param content Message content (will be encrypted by backend)
   * @returns Promise resolving to MessageViewModel in PENDING state
   */
  sendMessage(
    conversationId: string,
    senderId: string,
    content: string
  ): Promise<MessageViewModel>;

  /**
   * Subscribe to delivery state updates for a message.
   * 
   * Called when message transitions from PENDING to DELIVERED or FAILED.
   * 
   * @param messageId Message ID to track
   * @param callback Callback with new state
   */
  subscribeToDeliveryUpdates(
    messageId: string,
    callback: (newState: "delivered" | "failed") => void
  ): () => void; // Returns unsubscribe function
}

/**
 * Mock implementation for testing.
 * 
 * In production, this would use the actual HTTP client and WebSocket connection.
 */
export class MockMessageApiService implements MessageApiService {
  private deliveryCallbacks = new Map<string, (state: "delivered" | "failed") => void>();

  async sendMessage(
    conversationId: string,
    senderId: string,
    _content: string
  ): Promise<MessageViewModel> {
    // Simulate API delay
    await new Promise((resolve) => setTimeout(resolve, 100));

    // Create message in PENDING state (optimistic update)
    const messageId = `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    const now = new Date();
    const expiresAt = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000); // 7 days

    const message: MessageViewModel = {
      message_id: messageId,
      sender_id: senderId,
      conversation_id: conversationId,
      state: "sent", // PENDING state (maps to "sent" in client API)
      created_at: now.toISOString(),
      expires_at: expiresAt.toISOString(),
      is_expired: false,
      is_failed: false,
      is_read_only: false,
      display_state: "queued", // UI shows "Queued" per UX Behavior (#12), Section 3.3
    };

    // Simulate delivery state transition after delay
    setTimeout(() => {
      const callback = this.deliveryCallbacks.get(messageId);
      if (callback) {
        // Simulate successful delivery (in production, this would come from WebSocket)
        callback("delivered");
      }
    }, 1000);

    return message;
  }

  subscribeToDeliveryUpdates(
    messageId: string,
    callback: (newState: "delivered" | "failed") => void
  ): () => void {
    this.deliveryCallbacks.set(messageId, callback);
    return () => {
      this.deliveryCallbacks.delete(messageId);
    };
  }
}
