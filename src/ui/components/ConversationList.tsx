/**
 * ConversationList component for conversation list display.
 * 
 * References:
 * - UX Behavior (#12), Section 3.2
 * - Copy Rules (#13), Section 3
 * - Resolved Clarifications (#53)
 * 
 * Displays active conversations only in reverse chronological order.
 * No sound, no animation, no urgency cues per UX Behavior (#12).
 */

import React from "react";
import { ConversationViewModel } from "../types";

export interface ConversationListProps {
  /**
   * List of conversation view models per UI Domain Adapter Layer.
   * Should be pre-filtered to active conversations only.
   * Per UX Behavior (#12), Section 3.2.
   */
  conversations: ConversationViewModel[];
  
  /**
   * Optional handler for conversation selection.
   * Not used in read-only mode, but provided for future extensibility.
   */
  onSelectConversation?: (conversationId: string) => void;
  
  /**
   * True if in neutral enterprise mode (revoked device).
   * Per Resolved Clarifications (#38).
   */
  isReadOnly: boolean;
}

/**
 * ConversationList component per UX Behavior (#12), Section 3.2.
 * 
 * Displays active conversations only per UX Behavior (#12), Section 3.2.
 * Each conversation shows participant count and last message timestamp.
 * 
 * Conversations with all participants revoked disappear automatically
 * per UX Behavior (#12), Section 3.2.
 */
export const ConversationList: React.FC<ConversationListProps> = ({
  conversations,
  onSelectConversation,
  isReadOnly,
}) => {
  // Format timestamp for display per Copy Rules (#13), Section 3
  const formatTimestamp = (isoString: string | null): string => {
    if (!isoString) return "No messages";
    const date = new Date(isoString);
    return date.toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  };

  // Handle empty state per Copy Rules (#13), Section 3
  if (conversations.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-500">
        <p className="text-sm">No conversations</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col">
      <div className="px-4 py-3 bg-gray-50 border-b border-gray-200">
        <h2 className="text-sm font-semibold text-gray-900">
          Conversations
        </h2>
      </div>
      <div className="flex flex-col">
        {conversations.map((conversation) => (
          <div
            key={conversation.conversation_id}
            className={`px-4 py-3 border-b border-gray-100 cursor-pointer hover:bg-gray-50 ${
              isReadOnly ? "opacity-75" : ""
            }`}
            onClick={() => onSelectConversation?.(conversation.conversation_id)}
          >
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-gray-900 mb-1">
                  {conversation.display_name}
                </div>
                <div className="text-xs text-gray-500">
                  {formatTimestamp(conversation.last_message_at)}
                </div>
              </div>
              {isReadOnly && (
                <span className="text-xs text-gray-400">
                  Read-only
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
