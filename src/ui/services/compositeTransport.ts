/**
 * Composite transport that manages WebSocket and REST polling with automatic fallback.
 * 
 * References:
 * - API Contracts (#10)
 * - Message Delivery & Reliability docs
 * - Resolved Clarifications (#51)
 * 
 * Implements resilience behavior:
 * - WebSocket is preferred transport
 * - Automatic REST polling fallback after 15s WebSocket disconnect
 * - REST polling stops immediately when WebSocket reconnects
 * - No duplicate messages (deduplication handled by message store)
 * 
 * Per Resolved Clarifications (#51):
 * - Reconnect with exponential backoff
 * - Fallback to REST polling if disconnected >15s
 * - Stop REST polling when WebSocket reconnects
 */

import {
  ConnectionStatus,
  ConnectionStatusHandler,
  IncomingMessageHandler,
  MessageTransport,
} from "./messageTransport";
import { WebSocketTransport } from "./websocketTransport";
import { PollingTransport } from "./pollingTransport";

/**
 * Composite transport that manages WebSocket and REST polling.
 * 
 * Automatically switches between transports based on connection state.
 */
export class CompositeTransport implements MessageTransport {
  private wsTransport: WebSocketTransport;
  private pollingTransport: PollingTransport;
  private deviceId: string = "";
  private onMessageHandler: IncomingMessageHandler | null = null;
  private onStatusChangeHandler: ConnectionStatusHandler | null = null;
  private status: ConnectionStatus = "disconnected";
  private activeTransport: "websocket" | "polling" | null = null;
  private fallbackTimer: ReturnType<typeof setTimeout> | null = null;
  private readonly FALLBACK_TIMEOUT_MS = 15000; // 15 seconds per Resolved Clarifications (#51)

  /**
   * Create composite transport instance.
   * 
   * @param wsUrl WebSocket server URL
   * @param apiUrl REST API server URL
   */
  constructor(wsUrl: string, apiUrl: string) {
    this.wsTransport = new WebSocketTransport(wsUrl);
    this.pollingTransport = new PollingTransport(apiUrl);
  }

  /**
   * Connect to the message transport.
   * 
   * Starts with WebSocket, falls back to REST polling if needed.
   */
  async connect(
    deviceId: string,
    onMessage: IncomingMessageHandler,
    onStatusChange: ConnectionStatusHandler
  ): Promise<void> {
    this.deviceId = deviceId;
    this.onMessageHandler = onMessage;
    this.onStatusChangeHandler = onStatusChange;

    // Wrap message handler to ensure deduplication
    const wrappedMessageHandler: IncomingMessageHandler = (message) => {
      if (this.onMessageHandler) {
        this.onMessageHandler(message);
      }
    };

    // Wrap status change handler to manage transport switching
    const wrappedStatusHandler: ConnectionStatusHandler = (status) => {
      this._handleTransportStatusChange(status);
    };

    // Start with WebSocket (preferred)
    this.activeTransport = "websocket";
    await this.wsTransport.connect(deviceId, wrappedMessageHandler, wrappedStatusHandler);

    // Schedule fallback check after 15s only if WebSocket not connected immediately
    if (!this.wsTransport.isConnected()) {
      this._scheduleFallbackCheck();
    }
  }

  /**
   * Handle transport status change.
   * 
   * Manages automatic switching between WebSocket and REST polling.
   */
  private _handleTransportStatusChange(status: ConnectionStatus): void {
    // Check WebSocket connection status directly, not just activeTransport
    // This handles the case where WebSocket reconnects while polling is active
    if (status === "connected" && this.wsTransport.isConnected()) {
      // WebSocket connected - stop REST polling if active and switch back
      this._stopPollingFallback();
      this._updateStatus("connected");
    } else if (this.activeTransport === "websocket") {
      // Only handle WebSocket status changes when WebSocket is the active transport
      if (status === "disconnected" || status === "reconnecting") {
        // WebSocket disconnected - schedule REST fallback (only if not already scheduled)
        if (!this.fallbackTimer) {
          this._scheduleFallbackCheck();
        }
        this._updateStatus(status);
      } else {
        this._updateStatus(status);
      }
    } else if (this.activeTransport === "polling") {
      // Polling transport status changes
      this._updateStatus(status);
    }
  }

  /**
   * Schedule REST polling fallback check.
   * 
   * After 15s, if WebSocket is still not connected, start REST polling.
   * 
   * Note: This timer should only be scheduled once per disconnect event.
   * It should not be reset on each reconnection attempt to ensure fallback
   * activates after 15s total disconnect time.
   */
  private _scheduleFallbackCheck(): void {
    // Only schedule if timer not already set (prevent reset on reconnection attempts)
    if (this.fallbackTimer) {
      return; // Timer already scheduled, don't reset it
    }

    // Schedule fallback check after 15s
    this.fallbackTimer = setTimeout(() => {
      this._checkAndStartFallback();
      this.fallbackTimer = null; // Clear timer reference after execution
    }, this.FALLBACK_TIMEOUT_MS);
  }

  /**
   * Check if WebSocket is connected and start REST polling fallback if needed.
   */
  private _checkAndStartFallback(): void {
    // Only start fallback if WebSocket is not connected and we're not already polling
    if (this.activeTransport === "websocket" && !this.wsTransport.isConnected()) {
      // Start REST polling fallback
      this._startPollingFallback();
    }
  }

  /**
   * Start REST polling fallback.
   * 
   * Per Resolved Clarifications (#51): fallback to REST polling if WebSocket unavailable >15s.
   */
  private async _startPollingFallback(): Promise<void> {
    if (this.activeTransport === "polling") {
      return; // Already polling
    }

    // Log fallback activation (no content, only event type per Logging & Observability #14)
    // Only log in development to avoid exposing transport details in production
    if (import.meta.env.DEV) {
      console.log("[Transport] WebSocket unavailable >15s, falling back to REST polling");
    }

    // Switch to polling transport
    this.activeTransport = "polling";

    // Wrap message handler
    const wrappedMessageHandler: IncomingMessageHandler = (message) => {
      if (this.onMessageHandler) {
        this.onMessageHandler(message);
      }
    };

    // Wrap status handler
    const wrappedStatusHandler: ConnectionStatusHandler = (status) => {
      this._handleTransportStatusChange(status);
    };

    // Start polling
    await this.pollingTransport.connect(
      this.deviceId,
      wrappedMessageHandler,
      wrappedStatusHandler
    );

    this._updateStatus("connected");
  }

  /**
   * Stop REST polling fallback.
   * 
   * Called when WebSocket reconnects (preferred transport).
   */
  private _stopPollingFallback(): void {
    if (this.activeTransport === "polling") {
      // Log fallback deactivation (no content, only event type per Logging & Observability #14)
      // Only log in development to avoid exposing transport details in production
      if (import.meta.env.DEV) {
        console.log("[Transport] WebSocket reconnected, stopping REST polling fallback");
      }

      // Stop polling
      this.pollingTransport.disconnect().catch(() => {
        // Disconnect errors handled silently
      });

      // Switch back to WebSocket
      this.activeTransport = "websocket";
    }

    // Clear fallback timer
    if (this.fallbackTimer) {
      clearTimeout(this.fallbackTimer);
      this.fallbackTimer = null;
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
   * Disconnect from the message transport.
   */
  async disconnect(): Promise<void> {
    // Clear fallback timer
    if (this.fallbackTimer) {
      clearTimeout(this.fallbackTimer);
      this.fallbackTimer = null;
    }

    // Disconnect both transports
    await Promise.all([
      this.wsTransport.disconnect().catch(() => {
        // Disconnect errors handled silently
      }),
      this.pollingTransport.disconnect().catch(() => {
        // Disconnect errors handled silently
      }),
    ]);

    this.activeTransport = null;
    this._updateStatus("disconnected");
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
    if (this.activeTransport === "websocket") {
      return this.wsTransport.isConnected();
    } else if (this.activeTransport === "polling") {
      return this.pollingTransport.isConnected();
    }
    return false;
  }
}
