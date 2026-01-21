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
}) => {
  // Neutral color scheme per UX Behavior (#12), Section 5
  // No red/green/security color metaphors
  const statusColor = isReadOnly
    ? "text-gray-600" // Neutral gray for disabled state
    : "text-gray-900"; // Standard text color for active state

  return (
    <div className="flex items-center gap-2 px-4 py-2 bg-white border-b border-gray-200">
      <div className={`text-sm font-medium ${statusColor}`}>
        {status}
      </div>
      {isReadOnly && (
        <span className="text-xs text-gray-500">
          (Read-only)
        </span>
      )}
    </div>
  );
};
