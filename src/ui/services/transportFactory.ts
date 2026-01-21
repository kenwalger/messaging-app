/**
 * Transport factory for creating message transports.
 * 
 * References:
 * - API Contracts (#10)
 * - Message Delivery & Reliability docs
 * - Resolved Clarifications (#51)
 * 
 * Provides factory function to create appropriate transport:
 * - Composite transport (WebSocket + REST polling with automatic fallback) - preferred
 * - WebSocket only
 * - REST polling only
 * 
 * Uses VITE_API_BASE_URL environment variable for API endpoints.
 */

import { MessageTransport } from "./messageTransport";
import { WebSocketTransport } from "./websocketTransport";
import { PollingTransport } from "./pollingTransport";
import { CompositeTransport } from "./compositeTransport";

/**
 * Transport configuration.
 */
export interface TransportConfig {
  /**
   * WebSocket server URL (e.g., "wss://api.example.com/ws").
   * If not provided, REST polling will be used.
   */
  wsUrl?: string;

  /**
   * REST API server URL (e.g., "https://api.example.com").
   * Required for REST polling fallback.
   */
  apiUrl: string;

  /**
   * Preferred transport type.
   * "websocket" (preferred) or "polling" (fallback).
   */
  preferredTransport?: "websocket" | "polling";
}

/**
 * Create message transport based on configuration.
 * 
 * Returns composite transport (WebSocket + REST polling with automatic fallback)
 * if both wsUrl and apiUrl are provided, otherwise returns single transport.
 * 
 * Per Resolved Clarifications (#51):
 * - Composite transport provides automatic REST fallback after 15s WebSocket disconnect
 * - REST polling stops immediately when WebSocket reconnects
 * 
 * @param config Transport configuration
 * @returns MessageTransport instance
 */
export function createMessageTransport(config: TransportConfig): MessageTransport {
  // If both WebSocket and API URLs are provided, use composite transport with automatic fallback
  if (config.wsUrl && config.apiUrl && config.preferredTransport !== "polling") {
    return new CompositeTransport(config.wsUrl, config.apiUrl);
  }

  // Fallback to single transport if URLs not both available
  if (config.preferredTransport === "polling" || !config.wsUrl) {
    // Use REST polling transport
    return new PollingTransport(config.apiUrl);
  }

  // Use WebSocket transport only (no fallback)
  return new WebSocketTransport(config.wsUrl);
}
