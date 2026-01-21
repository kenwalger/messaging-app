/**
 * Message transport abstraction for incoming messages.
 * 
 * References:
 * - API Contracts (#10)
 * - Message Delivery & Reliability docs
 * - Resolved Clarifications (#51)
 * 
 * Provides transport abstraction supporting:
 * - WebSocket (preferred)
 * - REST polling (fallback)
 * 
 * The UI must not care which transport is active.
 */

import { MessageViewModel } from "../types";

/**
 * Connection status for transport layer.
 */
export type ConnectionStatus = "connected" | "disconnected" | "connecting" | "reconnecting";

/**
 * Incoming message event handler.
 * 
 * Called when a new message is received from the backend.
 */
export type IncomingMessageHandler = (message: MessageViewModel) => void;

/**
 * Connection status change handler.
 * 
 * Called when connection status changes.
 */
export type ConnectionStatusHandler = (status: ConnectionStatus) => void;

/**
 * Message transport interface.
 * 
 * Abstracts WebSocket and REST polling implementations.
 * UI components should use this interface, not specific transport implementations.
 */
export interface MessageTransport {
  /**
   * Connect to the message transport.
   * 
   * Uses existing device authentication mechanism (X-Device-ID header).
   * Per API Contracts (#10), Section 5.
   * 
   * @param deviceId Device ID for authentication
   * @param onMessage Handler for incoming messages
   * @param onStatusChange Handler for connection status changes
   */
  connect(
    deviceId: string,
    onMessage: IncomingMessageHandler,
    onStatusChange: ConnectionStatusHandler
  ): Promise<void>;

  /**
   * Disconnect from the message transport.
   */
  disconnect(): Promise<void>;

  /**
   * Get current connection status.
   */
  getStatus(): ConnectionStatus;

  /**
   * Check if transport is currently connected.
   */
  isConnected(): boolean;
}

/**
 * WebSocket message format per Resolved Clarifications (#51).
 * 
 * Message format: JSON {id, conversation_id, payload, timestamp, sender_id, expiration}
 */
export interface WebSocketMessage {
  id: string; // Message ID
  conversation_id: string;
  payload: string; // Hex-encoded encrypted payload
  timestamp: string; // ISO datetime string
  sender_id: string;
  expiration: string; // ISO datetime string
}
