/**
 * MessageRow component for individual message display.
 * 
 * References:
 * - UX Behavior (#12), Section 3.3 and 3.4
 * - Copy Rules (#13), Section 3
 * 
 * Displays messages with visual distinction for delivered/failed/expired states.
 * No sound, no animation, no urgency cues per UX Behavior (#12).
 */

import React from "react";
import { MessageViewModel } from "../types";

export interface MessageRowProps {
  /**
   * Message view model per UI Domain Adapter Layer.
   */
  message: MessageViewModel;
  
  /**
   * True if in neutral enterprise mode (revoked device).
   * Per Resolved Clarifications (#38).
   */
  isReadOnly: boolean;
}

/**
 * MessageRow component per UX Behavior (#12), Section 3.3 and 3.4.
 * 
 * Displays individual messages with visual distinction for:
 * - Delivered messages (normal display)
 * - Failed messages (explicitly distinguishable)
 * - Expired messages (removed automatically, no undo)
 * 
 * Neutral, enterprise-safe visual tone per UX Behavior (#12), Section 2.
 */
export const MessageRow: React.FC<MessageRowProps> = ({
  message,
  isReadOnly,
}) => {
  // Format timestamp for display per Copy Rules (#13), Section 3
  const formatTimestamp = (isoString: string): string => {
    const date = new Date(isoString);
    return date.toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  };

  // Visual distinction per UX Behavior (#12), Section 3.3, 3.4, and 3.6
  // Neutral color scheme (no red/green/security color metaphors)
  const getMessageStyles = () => {
    if (message.is_expired) {
      // Expired messages are removed automatically per UX Behavior (#12), Section 3.4
      // Should not be displayed, but handle gracefully if present
      return "opacity-50 text-gray-400";
    }
    if (message.is_failed) {
      // Failed messages are explicitly distinguishable per UX Behavior (#12), Section 3.6
      return "text-gray-700 border-l-4 border-gray-400";
    }
    if (message.state === "sent" || message.display_state === "queued") {
      // Pending messages (queued) per UX Behavior (#12), Section 3.3
      // UI shows "Queued" until backend acknowledges delivery
      return "text-gray-600 opacity-75";
    }
    // Delivered messages (normal display)
    return "text-gray-900";
  };

  // Don't render expired messages per UX Behavior (#12), Section 3.4
  if (message.is_expired) {
    return null;
  }

  return (
    <div className={`px-4 py-3 border-b border-gray-100 ${getMessageStyles()}`}>
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-sm font-medium text-gray-700">
              {message.sender_id}
            </span>
            {message.is_failed && (
              <span className="text-xs text-gray-500">
                (Failed)
              </span>
            )}
            {(message.state === "sent" || message.display_state === "queued") && (
              <span className="text-xs text-gray-500">
                (Queued)
              </span>
            )}
          </div>
          <div className="text-sm text-gray-600">
            {formatTimestamp(message.created_at)}
          </div>
        </div>
        {isReadOnly && (
          <span className="text-xs text-gray-400">
            Read-only
          </span>
        )}
      </div>
    </div>
  );
};
