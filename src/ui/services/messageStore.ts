/**
 * Message store for managing incoming messages with deduplication and ordering.
 * 
 * References:
 * - Message Delivery & Reliability docs
 * - State Machines (#7)
 * - UX Behavior (#12)
 * 
 * Handles:
 * - Message deduplication by message ID
 * - Ordering guarantees (reverse chronological)
 * - State reconciliation (merge without overwriting incorrectly)
 */

import { MessageViewModel } from "../types";

/**
 * Message store interface for managing messages by conversation.
 */
export interface MessageStore {
  /**
   * Add or update a message in the store.
   * 
   * Deduplicates by message_id.
   * Preserves ordering (reverse chronological - newest first).
   * Merges state without overwriting incorrectly.
   * 
   * @param message Message to add or update
   * @returns True if message was added (new), False if updated (existing)
   */
  addMessage(message: MessageViewModel): boolean;

  /**
   * Get all messages for a conversation.
   * 
   * Returns messages in reverse chronological order (newest first).
   * Per Resolved Clarifications (#53).
   * 
   * @param conversationId Conversation ID
   * @returns Array of messages sorted newest first
   */
  getMessages(conversationId: string): MessageViewModel[];

  /**
   * Get all messages across all conversations.
   * 
   * @returns Map of conversation ID to messages
   */
  getAllMessages(): Record<string, MessageViewModel[]>;

  /**
   * Update message state (e.g., pending → delivered).
   * 
   * Used for delivery state transitions.
   * Does not overwrite if message doesn't exist.
   * 
   * @param messageId Message ID to update
   * @param updates Partial message updates
   * @returns True if message was found and updated
   */
  updateMessage(
    messageId: string,
    updates: Partial<MessageViewModel>
  ): boolean;

  /**
   * Remove expired messages from the store.
   * 
   * Per UX Behavior (#12), Section 3.4: expired messages removed automatically.
   * 
   * @param currentTime Current time for expiration check
   * @returns Number of messages removed
   */
  removeExpiredMessages(currentTime?: Date): number;

  /**
   * Clear all messages.
   */
  clear(): void;
}

/**
 * In-memory message store implementation.
 * 
 * Maintains messages by conversation with deduplication and ordering.
 */
export class InMemoryMessageStore implements MessageStore {
  /**
   * Messages by conversation ID.
   * Each conversation's messages are stored in reverse chronological order (newest first).
   */
  private messagesByConversation: Map<string, Map<string, MessageViewModel>> = new Map();

  /**
   * Add or update a message in the store.
   * 
   * Deduplicates by message_id (primary check per Message Delivery docs).
   * Preserves ordering: newest messages appear first.
   * Merges state: updates existing message if found, otherwise adds new.
   * 
   * @param message Message to add or update
   * @returns True if message was added (new), False if updated (existing)
   */
  addMessage(message: MessageViewModel): boolean {
    const conversationId = message.conversation_id;
    const messageId = message.message_id;

    // Get or create conversation message map
    if (!this.messagesByConversation.has(conversationId)) {
      this.messagesByConversation.set(conversationId, new Map());
    }

    const conversationMessages = this.messagesByConversation.get(conversationId)!;

    // Check if message already exists (deduplication)
    const isNew = !conversationMessages.has(messageId);

    if (isNew) {
      // Add new message
      conversationMessages.set(messageId, message);
    } else {
      // Update existing message - merge state without overwriting incorrectly
      const existing = conversationMessages.get(messageId)!;
      
      // State reconciliation: handle all valid state transitions
      // State progression: sent → delivered/failed (one-way)
      // delivered → failed (can happen if delivery later fails)
      // any → expired (can happen at any time if expiration timestamp passes)
      // Prevents overwriting delivered/failed with sent (backwards transition)
      const shouldUpdate =
        // sent → delivered/failed/expired (forward transition)
        (existing.state === "sent" && message.state !== "sent") ||
        // sent → sent (both pending, update with latest)
        (existing.state === "sent" && message.state === "sent") ||
        // delivered → failed (delivery failure after initial success)
        (existing.state === "delivered" && message.state === "failed") ||
        // any → expired (expiration can happen at any time)
        message.state === "expired" ||
        // expired → expired (update expiration metadata)
        (existing.state === "expired" && message.state === "expired");

      if (shouldUpdate) {
        conversationMessages.set(messageId, {
          ...existing,
          ...message,
          // Preserve created_at from original (don't overwrite with newer timestamp)
          created_at: existing.created_at,
        });
      }
    }

    // Maintain reverse chronological order (newest first)
    // Sort by created_at descending
    const sortedMessages = Array.from(conversationMessages.values()).sort(
      (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    );

    // Rebuild map with sorted order
    const sortedMap = new Map<string, MessageViewModel>();
    for (const msg of sortedMessages) {
      sortedMap.set(msg.message_id, msg);
    }
    this.messagesByConversation.set(conversationId, sortedMap);

    return isNew;
  }

  /**
   * Get all messages for a conversation.
   * 
   * Returns messages in reverse chronological order (newest first).
   * 
   * @param conversationId Conversation ID
   * @returns Array of messages sorted newest first
   */
  getMessages(conversationId: string): MessageViewModel[] {
    const conversationMessages = this.messagesByConversation.get(conversationId);
    if (!conversationMessages) {
      return [];
    }

    // Return in reverse chronological order (newest first)
    return Array.from(conversationMessages.values()).sort(
      (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    );
  }

  /**
   * Get all messages across all conversations.
   * 
   * @returns Map of conversation ID to messages
   */
  getAllMessages(): Record<string, MessageViewModel[]> {
    const result: Record<string, MessageViewModel[]> = {};

    for (const [conversationId] of this.messagesByConversation) {
      result[conversationId] = this.getMessages(conversationId);
    }

    return result;
  }

  /**
   * Update message state (e.g., pending → delivered).
   * 
   * Used for delivery state transitions.
   * Does not overwrite if message doesn't exist.
   * 
   * @param messageId Message ID to update
   * @param updates Partial message updates
   * @returns True if message was found and updated
   */
  updateMessage(
    messageId: string,
    updates: Partial<MessageViewModel>
  ): boolean {
    // Find message across all conversations
    for (const conversationMessages of this.messagesByConversation.values()) {
      if (conversationMessages.has(messageId)) {
        const existing = conversationMessages.get(messageId)!;
        conversationMessages.set(messageId, {
          ...existing,
          ...updates,
        });
        return true;
      }
    }

    return false;
  }

  /**
   * Remove expired messages from the store.
   * 
   * Per UX Behavior (#12), Section 3.4: expired messages removed automatically.
   * 
   * @param currentTime Current time for expiration check
   * @returns Number of messages removed
   */
  removeExpiredMessages(currentTime: Date = new Date()): number {
    let removedCount = 0;

    for (const [conversationId, conversationMessages] of this.messagesByConversation) {
      const toRemove: string[] = [];

      for (const [messageId, message] of conversationMessages) {
        const expiresAt = new Date(message.expires_at);
        if (expiresAt < currentTime) {
          toRemove.push(messageId);
        }
      }

      for (const messageId of toRemove) {
        conversationMessages.delete(messageId);
        removedCount++;
      }

      // Remove conversation if empty
      if (conversationMessages.size === 0) {
        this.messagesByConversation.delete(conversationId);
      }
    }

    return removedCount;
  }

  /**
   * Clear all messages.
   */
  clear(): void {
    this.messagesByConversation.clear();
  }
}
