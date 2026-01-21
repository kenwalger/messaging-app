/**
 * REST polling transport implementation for incoming messages.
 * 
 * References:
 * - API Contracts (#10)
 * - Message Delivery & Reliability docs
 * - Resolved Clarifications (#51)
 * 
 * REST polling is used as a fallback when WebSocket is unavailable.
 * Polls every 30 seconds per Resolved TBDs.
 */

import {
  ConnectionStatus,
  ConnectionStatusHandler,
  IncomingMessageHandler,
  MessageTransport,
} from "./messageTransport";
import { MessageViewModel } from "../types";

/**
 * REST polling transport implementation.
 * 
 * Polls /api/message/receive endpoint every 30 seconds.
 * Per Resolved TBDs: REST_POLLING_INTERVAL_SECONDS = 30
 */
export class PollingTransport implements MessageTransport {
  private deviceId: string = "";
  private onMessageHandler: IncomingMessageHandler | null = null;
  private onStatusChangeHandler: ConnectionStatusHandler | null = null;
  private status: ConnectionStatus = "disconnected";
  private pollingTimer: ReturnType<typeof setInterval> | null = null;
  private apiUrl: string;
  private lastReceivedId: string | null = null;
  private readonly POLLING_INTERVAL_MS = 30000; // 30 seconds per Resolved TBDs

  /**
   * Create polling transport instance.
   * 
   * @param apiUrl API server URL (e.g., "https://api.example.com")
   */
  constructor(apiUrl: string) {
    this.apiUrl = apiUrl;
  }

  /**
   * Connect to polling transport.
   * 
   * Starts polling immediately and continues every 30 seconds.
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

    this._updateStatus("connected");
    this._startPolling();
  }

  /**
   * Start polling for messages.
   */
  private _startPolling(): void {
    // Poll immediately
    this._poll();

    // Then poll every 30 seconds
    this.pollingTimer = setInterval(() => {
      this._poll();
    }, this.POLLING_INTERVAL_MS);
  }

  /**
   * Poll for new messages.
   * 
   * Calls /api/message/receive endpoint per API Contracts (#10), Section 3.4.
   */
  private async _poll(): Promise<void> {
    try {
      const url = new URL(`${this.apiUrl}/api/message/receive`);
      if (this.lastReceivedId) {
        url.searchParams.set("last_received_id", this.lastReceivedId);
      }

      const response = await fetch(url.toString(), {
        method: "GET",
        headers: {
          "X-Device-ID": this.deviceId,
        },
      });

      if (!response.ok) {
        // Handle errors silently - will retry on next poll
        return;
      }

      const data = await response.json();

      // Normalize API response to MessageViewModel array
      if (data.messages && Array.isArray(data.messages)) {
        for (const msgData of data.messages) {
          const message: MessageViewModel = {
            message_id: msgData.message_id,
            sender_id: msgData.sender_id,
            conversation_id: msgData.conversation_id,
            state: msgData.state,
            created_at: msgData.created_at,
            expires_at: msgData.expires_at,
            is_expired: false, // Will be checked by UI adapter
            is_failed: msgData.state === "failed",
            is_read_only: false, // Will be set by UI adapter based on device state
            display_state: msgData.state === "failed" ? "failed" : "delivered",
          };

          // Update last received ID for next poll
          this.lastReceivedId = message.message_id;

          if (this.onMessageHandler) {
            this.onMessageHandler(message);
          }
        }
      }
    } catch (error) {
      // Network errors - silently ignore, will retry on next poll
      // No content logged or leaked per deterministic rules
    }
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
   * Disconnect from polling transport.
   */
  async disconnect(): Promise<void> {
    if (this.pollingTimer) {
      clearInterval(this.pollingTimer);
      this.pollingTimer = null;
    }

    this._updateStatus("disconnected");
    this.lastReceivedId = null;
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
    return this.status === "connected" && this.pollingTimer !== null;
  }
}
