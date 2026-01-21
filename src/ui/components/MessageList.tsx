/**
 * MessageList component for conversation message display.
 * 
 * References:
 * - UX Behavior (#12), Section 3.3 and 3.4
 * - Copy Rules (#13), Section 3
 * - Resolved Clarifications (#53)
 * 
 * Displays messages in reverse chronological order (newest first).
 * No sound, no animation, no urgency cues per UX Behavior (#12).
 */

import React from "react";
import { MessageViewModel } from "../types";
import { MessageRow } from "./MessageRow";

export interface MessageListProps {
  /**
   * List of message view models per UI Domain Adapter Layer.
   * Should be pre-sorted in reverse chronological order (newest first).
   * Per Resolved Clarifications (#53).
   */
  messages: MessageViewModel[];
  
  /**
   * Current conversation ID for context.
   */
  conversationId: string;
  
  /**
   * True if in neutral enterprise mode (revoked device).
   * Per Resolved Clarifications (#38).
   */
  isReadOnly: boolean;
}

/**
 * MessageList component per UX Behavior (#12), Section 3.3 and 3.4.
 * 
 * Displays messages in reverse chronological order (newest first).
 * Messages appear in order of device-local receipt per UX Behavior (#12), Section 3.4.
 * 
 * Expired messages are removed automatically; no undo per UX Behavior (#12), Section 3.3.
 * Failed messages are explicitly distinguishable per UX Behavior (#12), Section 3.6.
 */
export const MessageList: React.FC<MessageListProps> = ({
  messages,
  conversationId,
  isReadOnly,
}) => {
  // Filter out expired messages per UX Behavior (#12), Section 3.4
  // Expired messages disappear silently
  const visibleMessages = messages.filter((msg) => !msg.is_expired);

  // Handle empty state per Copy Rules (#13), Section 3
  if (visibleMessages.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-500">
        <p className="text-sm">No messages yet</p>
      </div>
    );
  }

  // Messages are expected to be in chronological order (oldest first) for display
  // Display in chronological order (oldest at top, newest at bottom)
  return (
    <div className="flex flex-col">
      {visibleMessages.map((message) => (
        <MessageRow
          key={message.message_id}
          message={message}
          isReadOnly={isReadOnly}
        />
      ))}
    </div>
  );
};
