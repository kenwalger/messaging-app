/**
 * MessageComposer component for message composition and sending.
 * 
 * References:
 * - UX Behavior (#12), Section 3.3
 * - Copy Rules (#13), Section 3
 * - Resolved Clarifications (#38)
 * - State Machines (#7)
 * 
 * Handles message composition, optimistic updates, and delivery state transitions.
 */

import React, { useState, useCallback } from "react";
import { SendButton } from "./SendButton";
import { MessageViewModel } from "../types";

export interface MessageComposerProps {
  /**
   * Current conversation ID.
   */
  conversationId: string;
  
  /**
   * Current device/sender ID.
   */
  senderId: string;
  
  /**
   * True if sending is disabled.
   * Per deterministic rules: neutral enterprise mode, revoked device, or closed conversation.
   */
  sendDisabled: boolean;
  
  /**
   * Handler for sending a message.
   * Returns a promise that resolves with the created message view model.
   */
  onSendMessage: (
    conversationId: string,
    senderId: string,
    content: string
  ) => Promise<MessageViewModel>;
}

/**
 * MessageComposer component per UX Behavior (#12), Section 3.3.
 * 
 * Handles message composition and sending with:
 * - Optimistic updates (message enters PENDING state immediately)
 * - Delivery state transitions handled by parent via subscription
 * - Visual indicators for pending/delivered/failed states
 * 
 * No attachments, no message editing, no retry UI per constraints.
 * No content logged or leaked per deterministic rules.
 */
export const MessageComposer: React.FC<MessageComposerProps> = ({
  conversationId,
  senderId,
  sendDisabled,
  onSendMessage,
}) => {
  const [messageContent, setMessageContent] = useState("");
  const [isSending, setIsSending] = useState(false);

  /**
   * Handle send button click per UX Behavior (#12), Section 3.3.
   * 
   * On send:
   * - Message enters PENDING state immediately (optimistic update)
   * - UI updates optimistically
   * - Message is sent via API
   * - Delivery state transitions handled by parent via subscription mechanism
   */
  const handleSend = useCallback(async () => {
    if (!messageContent.trim() || sendDisabled || isSending) {
      return;
    }

    const content = messageContent.trim();
    setMessageContent("");
    setIsSending(true);

    try {
      // Send message via API
      // Message enters PENDING state immediately per deterministic rules
      await onSendMessage(conversationId, senderId, content);
      // Optimistic update and delivery state transitions are handled by parent (App)
    } catch (error) {
      // Handle failure: message transitions to FAILED state
      // In real implementation, this would be handled by the API adapter
      // No content logged or leaked per deterministic rules
      // Log error for debugging (metadata only, no content)
      if (import.meta.env.DEV) {
        console.error("Failed to send message:", error);
      }
      // Error handling is done silently; failed state will be updated via delivery subscription
      // The subscription mechanism in handleSendMessage will handle delivery state transitions
      // Development-only logging for observability (metadata only, no content)
      if (import.meta.env.DEV) {
        console.error("Failed to send message:", error);
      }
    } finally {
      setIsSending(false);
    }
  }, [messageContent, sendDisabled, isSending, conversationId, senderId, onSendMessage]);

  /**
   * Handle Enter key press for sending per UX Behavior (#12), Section 3.3.
   */
  const handleKeyPress = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend]
  );

  return (
    <div className="border-t border-gray-200 bg-white p-4">
      <div className="flex items-end gap-2">
        <textarea
          value={messageContent}
          onChange={(e) => setMessageContent(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Type your message"
          disabled={sendDisabled || isSending}
          rows={3}
          className={`
            flex-1 px-3 py-2 text-sm border border-gray-300 rounded
            resize-none focus:outline-none focus:ring-2 focus:ring-gray-400
            ${
              sendDisabled || isSending
                ? "bg-gray-100 text-gray-400 cursor-not-allowed"
                : "bg-white text-gray-900"
            }
          `}
        />
        <SendButton
          disabled={sendDisabled || !messageContent.trim()}
          isSending={isSending}
          onClick={handleSend}
        />
      </div>
    </div>
  );
};
