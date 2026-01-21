/**
 * StatusIndicator component for device state display.
 * 
 * References:
 * - UX Behavior (#12), Section 3.1 and 3.5
 * - Copy Rules (#13), Section 4
 * 
 * Displays neutral device status with read-only mode indicator.
 * No sound, no animation, no urgency cues per UX Behavior (#12).
 */

import React from "react";

import { ConnectionStatus } from "../services/messageTransport";

export interface StatusIndicatorProps {
  /**
   * Device status string per Copy Rules (#13), Section 4.
   * "Active Messaging" or "Messaging Disabled"
   */
  status: "Active Messaging" | "Messaging Disabled";
  
  /**
   * True if in neutral enterprise mode (revoked device).
   * Per Resolved Clarifications (#38).
   */
  isReadOnly: boolean;
  
  /**
   * Connection status for developer-facing indicator.
   * Shows WebSocket/REST polling status for manual testing.
   */
  connectionStatus?: ConnectionStatus;
  
  /**
   * True if REST polling fallback is active.
   * Developer-facing indicator for transport status.
   */
  isPollingFallback?: boolean;
}

/**
 * StatusIndicator component per UX Behavior (#12), Section 3.1 and 3.5.
 * 
 * Displays device status with neutral, enterprise-safe visual tone.
 * No security-themed language or hidden features per UX Behavior (#12), Section 2.
 */
export const StatusIndicator: React.FC<StatusIndicatorProps> = ({
  status,
  isReadOnly,
  connectionStatus,
  isPollingFallback = false,
}) => {
  // Neutral color scheme per UX Behavior (#12), Section 5
  // No red/green/security color metaphors
  const statusColor = isReadOnly
    ? "text-gray-600" // Neutral gray for disabled state
    : "text-gray-900"; // Standard text color for active state

  // Developer-facing connection status indicator
  const getConnectionStatusText = (): string => {
    if (isPollingFallback) {
      return "REST polling";
    }
    if (connectionStatus === "connected") {
      return "WebSocket connected";
    }
    if (connectionStatus === "reconnecting") {
      return "WebSocket reconnecting";
    }
    if (connectionStatus === "connecting") {
      return "Connecting...";
    }
    if (connectionStatus === "disconnected") {
      return "Disconnected";
    }
    return "";
  };

  return (
    <div className="flex items-center justify-between gap-2 px-4 py-2 bg-white border-b border-gray-200">
      <div className="flex items-center gap-2">
        <div className={`text-sm font-medium ${statusColor}`}>
          {status}
        </div>
        {isReadOnly && (
          <span className="text-xs text-gray-500">
            (Read-only)
          </span>
        )}
      </div>
      {connectionStatus && (
        <div className="text-xs text-gray-500">
          {getConnectionStatusText()}
        </div>
      )}
    </div>
  );
};
