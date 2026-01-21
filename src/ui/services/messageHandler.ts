/**
 * Message handler service for incoming messages and live updates.
 * 
 * References:
 * - Message Delivery & Reliability docs
 * - State Machines (#7)
 * - UX Behavior (#12)
 * - Resolved Clarifications (#51)
 * 
 * Coordinates:
 * - Transport layer (WebSocket or REST polling)
 * - Message store (deduplication and ordering)
 * - UI updates (automatic message appearance)
 */

import {
  ConnectionStatus,
  ConnectionStatusHandler,
  MessageTransport,
} from "./messageTransport";
import { InMemoryMessageStore, MessageStore } from "./messageStore";
import { MessageViewModel } from "../types";

/**
 * Message handler service.
 * 
 * Handles incoming messages, deduplication, ordering, and state reconciliation.
 * Provides automatic UI updates when new messages arrive.
 */
export class MessageHandlerService {
  private transport: MessageTransport;
  private store: MessageStore;
  private deviceId: string;
  private onMessagesUpdate: ((conversationId: string, messages: MessageViewModel[]) => void) | null = null;
  private connectionStatus: ConnectionStatus = "disconnected";

  /**
   * Create message handler service.
   * 
   * @param transport Message transport (WebSocket or REST polling)
   * @param deviceId Device ID for authentication
   */
  constructor(transport: MessageTransport, deviceId: string) {
    this.transport = transport;
    this.deviceId = deviceId;
    this.store = new InMemoryMessageStore();
  }

  /**
   * Set callback for message updates.
   * 
   * Called when messages are added or updated.
   * 
   * @param callback Callback with conversation ID and updated messages
   */
  setOnMessagesUpdate(
    callback: (conversationId: string, messages: MessageViewModel[]) => void
  ): void {
    this.onMessagesUpdate = callback;
  }

  /**
   * Start receiving messages.
   * 
   * Connects to transport and begins receiving incoming messages.
   * Handles deduplication, ordering, and state reconciliation automatically.
   */
  async start(): Promise<void> {
    await this.transport.connect(
      this.deviceId,
      (message) => this._handleIncomingMessage(message),
      (status) => this._handleConnectionStatusChange(status)
    );
  }

  /**
   * Stop receiving messages.
   * 
   * Disconnects from transport.
   */
  async stop(): Promise<void> {
    await this.transport.disconnect();
  }

  /**
   * Get current connection status.
   */
  getConnectionStatus(): ConnectionStatus {
    return this.connectionStatus;
  }

  /**
   * Get all messages for a conversation.
   * 
   * @param conversationId Conversation ID
   * @returns Array of messages in reverse chronological order
   */
  getMessages(conversationId: string): MessageViewModel[] {
    return this.store.getMessages(conversationId);
  }

  /**
   * Get all messages across all conversations.
   * 
   * @returns Map of conversation ID to messages
   */
  getAllMessages(): Record<string, MessageViewModel[]> {
    return this.store.getAllMessages();
  }

  /**
   * Add a message to the store (for optimistic updates from sending).
   * 
   * @param message Message to add
   */
  addMessage(message: MessageViewModel): void {
    const isNew = this.store.addMessage(message);
    if (isNew) {
      this._notifyUpdate(message.conversation_id);
    }
  }

  /**
   * Update message state (for delivery state transitions).
   * 
   * @param messageId Message ID to update
   * @param updates Partial message updates
   */
  updateMessage(messageId: string, updates: Partial<MessageViewModel>): void {
    const updated = this.store.updateMessage(messageId, updates);
    if (updated) {
      // Find conversation ID for this message
      const allMessages = this.store.getAllMessages();
      for (const [conversationId, messages] of Object.entries(allMessages)) {
        if (messages.some((msg) => msg.message_id === messageId)) {
          this._notifyUpdate(conversationId);
          break;
        }
      }
    }
  }

  /**
   * Handle incoming message from transport.
   * 
   * Normalizes, deduplicates, and merges into store.
   * Preserves ordering and state reconciliation.
   */
  private _handleIncomingMessage(message: MessageViewModel): void {
    // Add message to store (deduplication happens automatically)
    const isNew = this.store.addMessage(message);

    if (isNew) {
      // Notify UI of new message
      this._notifyUpdate(message.conversation_id);
    }
  }

  /**
   * Handle connection status change.
   * 
   * Tracks connection status internally (no UI indicator yet per constraints).
   */
  private _handleConnectionStatusChange(status: ConnectionStatus): void {
    this.connectionStatus = status;

    // On reconnect, reconcile missed messages using REST
    // This is handled by the transport layer automatically
    // (polling transport will fetch missed messages on next poll)
  }

  /**
   * Notify UI of message updates.
   * 
   * @param conversationId Conversation ID that was updated
   */
  private _notifyUpdate(conversationId: string): void {
    if (this.onMessagesUpdate) {
      const messages = this.store.getMessages(conversationId);
      this.onMessagesUpdate(conversationId, messages);
    }
  }

  /**
   * Remove expired messages.
   * 
   * Should be called periodically to clean up expired messages.
   * 
   * @returns Number of messages removed
   */
  removeExpiredMessages(): number {
    const removed = this.store.removeExpiredMessages();
    
    // Notify UI of updates for all affected conversations
    if (removed > 0 && this.onMessagesUpdate) {
      const allMessages = this.store.getAllMessages();
      for (const conversationId of Object.keys(allMessages)) {
        const messages = this.store.getMessages(conversationId);
        this.onMessagesUpdate(conversationId, messages);
      }
    }

    return removed;
  }
}
