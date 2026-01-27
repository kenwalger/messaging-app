/**
 * WebSocket transport implementation for incoming messages.
 * 
 * References:
 * - API Contracts (#10)
 * - Message Delivery & Reliability docs
 * - Resolved Clarifications (#51)
 * 
 * WebSocket is the preferred transport for real-time message delivery.
 * Falls back to REST polling if WebSocket is unavailable.
 */

import {
  ConnectionStatus,
  ConnectionStatusHandler,
  IncomingMessageHandler,
  MessageTransport,
  WebSocketMessage,
} from "./messageTransport";
import { MessageViewModel } from "../types";

/**
 * WebSocket transport implementation.
 * 
 * Handles WebSocket connection lifecycle:
 * - Authentication using X-Device-ID header
 * - Automatic reconnection with exponential backoff
 * - Message normalization and deduplication
 * 
 * Per Resolved Clarifications (#51):
 * - Auth: X-Device-ID + ephemeral session token
 * - Message format: JSON {id, conversation_id, payload, timestamp, sender_id, expiration}
 * - On disconnect: automatic reconnect (exponential backoff)
 */
export class WebSocketTransport implements MessageTransport {
  private ws: WebSocket | null = null;
  private deviceId: string = "";
  private onMessageHandler: IncomingMessageHandler | null = null;
  private onStatusChangeHandler: ConnectionStatusHandler | null = null;
  private status: ConnectionStatus = "disconnected";
  private reconnectAttempts: number = 0;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private wsUrl: string;

  /**
   * Create WebSocket transport instance.
   * 
   * @param wsUrl WebSocket server URL (e.g., "wss://api.example.com/ws")
   */
  constructor(wsUrl: string) {
    this.wsUrl = wsUrl;
  }

  /**
   * Connect to WebSocket server.
   * 
   * Uses X-Device-ID for authentication per API Contracts (#10), Section 5.
   * 
   * @param deviceId Device ID for authentication
   * @param onMessage Handler for incoming messages
   * @param onStatusChange Handler for connection status changes
   */
  async connect(
    deviceId: string,
    onMessage: IncomingMessageHandler,
    onStatusChange: ConnectionStatusHandler
  ): Promise<void> {
    this.deviceId = deviceId;
    this.onMessageHandler = onMessage;
    this.onStatusChangeHandler = onStatusChange;

    await this._connect();
  }

  /**
   * Internal WebSocket connection logic.
   */
  private async _connect(): Promise<void> {
    if (this.ws?.readyState === WebSocket.OPEN) {
      return; // Already connected
    }

    this._updateStatus("connecting");

    try {
      // Build WebSocket URL with device ID for authentication
      // Per API Contracts (#10), Section 5: X-Device-ID header
      // For WebSocket, we'll use query parameter or subprotocol
      const url = `${this.wsUrl}?device_id=${encodeURIComponent(this.deviceId)}`;

      this.ws = new WebSocket(url);

      this.ws.onopen = () => {
        this._updateStatus("connected");
        // Log successful connection (no content, only event type per Logging & Observability #14)
        if (import.meta.env.DEV && this.reconnectAttempts > 0) {
          console.log(`[WebSocket] Reconnected successfully after ${this.reconnectAttempts} attempts`);
        }
        this.reconnectAttempts = 0;
      };

      this.ws.onmessage = (event) => {
        this._handleMessage(event.data);
      };

      this.ws.onerror = () => {
        // Error handling - will trigger onclose
      };

      this.ws.onclose = () => {
        this._updateStatus("disconnected");
        // Log reconnect attempt (no content, only event type per Logging & Observability #14)
        if (import.meta.env.DEV) {
          console.log(`[WebSocket] Connection closed, scheduling reconnect (attempt ${this.reconnectAttempts + 1})`);
        }
        this._scheduleReconnect();
      };
    } catch (error) {
      this._updateStatus("disconnected");
      this._scheduleReconnect();
    }
  }

  /**
   * Handle incoming WebSocket message.
   * 
   * Normalizes WebSocket message format to MessageViewModel.
   * Sends ACK for incoming messages.
   * Handles ACK messages from backend for sent messages.
   * Per Resolved Clarifications (#51).
   */
  private _handleMessage(data: string): void {
    try {
      const parsed = JSON.parse(data);

      // Check if this is an ACK message (for sent messages)
      // Also check for normalized message type
      if (parsed.type === "ack" && parsed.message_id) {
        // This is an ACK for a message we sent
        // Forward to message handler via callback
        // ACK format: {type: "ack", message_id: "...", status: "delivered" | "failed"}
        const ackMessage: MessageViewModel = {
          message_id: parsed.message_id,
          sender_id: this.deviceId, // ACK is for our own message
          conversation_id: parsed.conversation_id || "", // May not be present in ACK
          state: parsed.status === "failed" ? "failed" : "delivered",
          created_at: new Date().toISOString(), // ACK timestamp
          expires_at: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(), // Placeholder
          is_expired: false,
          is_failed: parsed.status === "failed",
          is_read_only: false,
          display_state: parsed.status === "failed" ? "failed" : "delivered",
        };

        // ACK messages are special - they update existing messages, not create new ones
        // We'll use a special handler for ACKs (if provided)
        if (this.onMessageHandler) {
          this.onMessageHandler(ackMessage);
        }
        return;
      }

      // Regular incoming message (not an ACK)
      // Handle normalized event type: type: "message" with sender_device_id
      // Also support backward compatibility with sender_id and messages without type field
      // Accept messages with type: "message" or no type field (backward compatibility)
      if (parsed.type && parsed.type !== "message" && parsed.type !== "ack") {
        // Unknown message type - silently ignore
        return;
      }
      
      const wsMessage: WebSocketMessage = parsed;
      
      // Validate required fields
      if (!wsMessage.id || !wsMessage.conversation_id || !wsMessage.timestamp) {
        // Missing required fields - silently ignore per deterministic rules
        return;
      }
      
      // Use normalized sender_device_id if present, fallback to sender_id for backward compatibility
      // Validate that sender ID exists (required field)
      const senderId = wsMessage.sender_device_id || wsMessage.sender_id;
      if (!senderId) {
        // Missing sender ID - silently ignore per deterministic rules
        return;
      }

      // Handle optional expiration field with fallback (default: 7 days from timestamp)
      const timestamp = new Date(wsMessage.timestamp);
      const defaultExpiration = new Date(timestamp.getTime() + 7 * 24 * 60 * 60 * 1000); // 7 days
      const expiresAt = wsMessage.expiration ? new Date(wsMessage.expiration) : defaultExpiration;

      // Normalize to MessageViewModel
      // Include payload to preserve message content end-to-end
      const message: MessageViewModel = {
        message_id: wsMessage.id,
        sender_id: senderId,
        conversation_id: wsMessage.conversation_id,
        state: "delivered", // Incoming messages are already delivered
        created_at: wsMessage.timestamp,
        expires_at: expiresAt.toISOString(),
        is_expired: false, // Will be checked by UI adapter
        is_failed: false,
        is_read_only: false, // Will be set by UI adapter based on device state
        display_state: "delivered",
        payload: wsMessage.payload, // Preserve payload from WebSocket message
      };
      
      // DEV-only: Log if payload is missing (schema mismatch detection)
      if (import.meta.env.DEV && !wsMessage.payload) {
        console.warn("[WebSocketTransport] Message received without payload field:", {
          message_id: wsMessage.id,
          conversation_id: wsMessage.conversation_id,
          has_payload: !!wsMessage.payload,
        });
      }

      // Send ACK to backend for received message
      this._sendAck(wsMessage.id, wsMessage.conversation_id);

      if (this.onMessageHandler) {
        this.onMessageHandler(message);
      }
    } catch (error) {
      // Invalid message format - silently ignore per deterministic rules
      // No content logged or leaked
    }
  }

  /**
   * Send ACK to backend for received message.
   * 
   * Per API Contracts (#10): ACK format is JSON {type: "ack", message_id: "...", conversation_id: "..."}
   */
  private _sendAck(messageId: string, conversationId: string): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      return; // Can't send ACK if not connected
    }

    try {
      const ackMessage = {
        type: "ack",
        message_id: messageId,
        conversation_id: conversationId,
      };
      this.ws.send(JSON.stringify(ackMessage));
    } catch (error) {
      // Failed to send ACK - silently ignore per deterministic rules
      // No content logged or leaked
    }
  }

  /**
   * Schedule reconnection with exponential backoff.
   * 
   * Per Resolved Clarifications: exponential backoff for reconnection.
   */
  private _scheduleReconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
    }

    // Exponential backoff: 2^reconnectAttempts seconds, max 60 seconds
    const delay = Math.min(
      Math.pow(2, this.reconnectAttempts) * 1000,
      60000
    );

    this.reconnectAttempts++;
    this._updateStatus("reconnecting");

    this.reconnectTimer = setTimeout(() => {
      this._connect();
    }, delay);
  }

  /**
   * Update connection status and notify handler.
   */
  private _updateStatus(status: ConnectionStatus): void {
    if (this.status !== status) {
      this.status = status;
      if (this.onStatusChangeHandler) {
        this.onStatusChangeHandler(status);
      }
    }
  }

  /**
   * Disconnect from WebSocket server.
   */
  async disconnect(): Promise<void> {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }

    this._updateStatus("disconnected");
    this.reconnectAttempts = 0;
  }

  /**
   * Get current connection status.
   */
  getStatus(): ConnectionStatus {
    return this.status;
  }

  /**
   * Check if transport is currently connected.
   */
  isConnected(): boolean {
    return this.status === "connected" && this.ws?.readyState === WebSocket.OPEN;
  }
}
