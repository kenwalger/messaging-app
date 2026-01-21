/**
 * Transport factory for creating message transports.
 * 
 * References:
 * - API Contracts (#10)
 * - Message Delivery & Reliability docs
 * - Resolved Clarifications (#51)
 * 
 * Provides factory function to create appropriate transport:
 * - WebSocket (preferred)
 * - REST polling (fallback)
 * 
 * Uses VITE_API_BASE_URL environment variable for API endpoints.
 */

import { MessageTransport } from "./messageTransport";
import { WebSocketTransport } from "./websocketTransport";
import { PollingTransport } from "./pollingTransport";

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
 * Returns WebSocket transport if wsUrl is provided and preferred,
 * otherwise returns REST polling transport.
 * 
 * @param config Transport configuration
 * @returns MessageTransport instance
 */
export function createMessageTransport(config: TransportConfig): MessageTransport {
  if (config.preferredTransport === "polling" || !config.wsUrl) {
    // Use REST polling transport
    return new PollingTransport(config.apiUrl);
  }

  // Use WebSocket transport (preferred)
  return new WebSocketTransport(config.wsUrl);
}
