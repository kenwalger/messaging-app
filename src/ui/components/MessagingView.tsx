/**
 * Store-connected messaging view component.
 * 
 * References:
 * - UX Behavior (#12)
 * - Message Delivery & Reliability docs
 * - State Machines (#7)
 * 
 * Subscribes to message store and displays conversations and messages in real time.
 * No duplicate state - all data comes from the message store.
 */

import React, { useState, useEffect, useCallback } from "react";
import { ConversationList } from "./ConversationList";
import { MessageList } from "./MessageList";
import { MessageHandlerService } from "../services/messageHandler";
import { MessageViewModel } from "../types";
import { ConversationViewModel } from "../types";

export interface MessagingViewProps {
  /**
   * Message handler service that manages the message store.
   */
  messageHandler: MessageHandlerService;

  /**
   * Device ID for display purposes.
   */
  deviceId: string;

  /**
   * True if in neutral enterprise mode (revoked device).
   */
  isReadOnly: boolean;
}

/**
 * MessagingView component.
 * 
 * Store-connected view that:
 * - Subscribes to message store updates
 * - Derives conversations from message store
 * - Displays conversations and messages in real time
 * - Updates automatically when store state changes
 */
export const MessagingView: React.FC<MessagingViewProps> = ({
  messageHandler,
  deviceId,
  isReadOnly,
}) => {
  const [selectedConversationId, setSelectedConversationId] = useState<string | null>(null);
  const [conversations, setConversations] = useState<ConversationViewModel[]>([]);
  const [messagesByConversation, setMessagesByConversation] = useState<
    Record<string, MessageViewModel[]>
  >({});

  /**
   * Derive conversations from message store.
   * 
   * Creates ConversationViewModel from messages in the store.
   * Each conversation shows:
   * - Conversation identifier
   * - Last message preview
   * - Last activity timestamp
   */
  const deriveConversations = useCallback((): ConversationViewModel[] => {
    const allMessages = messageHandler.getAllMessages();
    const conversationList: ConversationViewModel[] = [];

    for (const [conversationId, messages] of Object.entries(allMessages)) {
      if (messages.length === 0) {
        continue;
      }

      // Get last message for preview and timestamp
      const lastMessage = messages[0]; // Messages are in reverse chronological order (newest first)

      // Derive unique sender IDs for participant count
      const uniqueSenders = new Set(messages.map((msg) => msg.sender_id));
      const participantCount = uniqueSenders.size;

      // Create last message preview (truncated, no content per deterministic rules)
      const lastMessagePreview = lastMessage.is_failed
        ? "(Failed)"
        : lastMessage.state === "sent"
        ? "(Queued)"
        : `Message from ${lastMessage.sender_id.slice(-8)}`;

      // Derive conversation view model
      const conversation: ConversationViewModel = {
        conversation_id: conversationId,
        state: "active",
        participant_count: participantCount,
        can_send: !isReadOnly,
        is_read_only: isReadOnly,
        send_disabled: isReadOnly,
        last_message_at: lastMessage.created_at,
        created_at: messages[messages.length - 1].created_at, // Oldest message timestamp
        display_name:
          participantCount > 1
            ? `Conversation (${participantCount} participants)`
            : "Conversation",
        last_message_preview: lastMessagePreview,
      };

      conversationList.push(conversation);
    }

    // Sort conversations by last_message_at (newest first)
    conversationList.sort((a, b) => {
      const timeA = a.last_message_at ? new Date(a.last_message_at).getTime() : 0;
      const timeB = b.last_message_at ? new Date(b.last_message_at).getTime() : 0;
      return timeB - timeA;
    });

    return conversationList;
  }, [messageHandler, isReadOnly]);

  /**
   * Subscribe to message store updates.
   * 
   * Sets up callback once and keeps it stable to avoid re-subscriptions.
   */
  useEffect(() => {
    // Set up callback for message updates
    // Use functional state updates to avoid dependency on state values
    messageHandler.setOnMessagesUpdate((conversationId, messages) => {
      // Update messages for this conversation
      setMessagesByConversation((prev) => ({
        ...prev,
        [conversationId]: messages,
      }));

      // Re-derive conversations (last message timestamp may have changed)
      // Call deriveConversations directly (it's stable via useCallback)
      const derivedConversations = deriveConversations();
      setConversations(derivedConversations);
    });

    // Initial load from store
    const derivedConversations = deriveConversations();
    setConversations(derivedConversations);

    // Update messages for all conversations
    const allMessages = messageHandler.getAllMessages();
    setMessagesByConversation(allMessages);

    // Auto-select first conversation if none selected
    setSelectedConversationId((prev) => {
      if (!prev && derivedConversations.length > 0) {
        return derivedConversations[0].conversation_id;
      }
      return prev;
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [messageHandler]); // Only depend on messageHandler - deriveConversations is stable via useCallback

  const selectedMessages = selectedConversationId
    ? messagesByConversation[selectedConversationId] || []
    : [];

  // Convert messages to chronological order (oldest first) for display
  const chronologicalMessages = [...selectedMessages].reverse();

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar: Conversation List */}
      <div className="w-80 bg-white border-r border-gray-200 flex flex-col">
        <div className="px-4 py-3 bg-gray-50 border-b border-gray-200">
          <h1 className="text-sm font-semibold text-gray-900">Messaging</h1>
        </div>
        <div className="flex-1 overflow-y-auto">
          <ConversationList
            conversations={conversations}
            onSelectConversation={setSelectedConversationId}
            isReadOnly={isReadOnly}
          />
        </div>
      </div>

      {/* Main: Message Pane */}
      <div className="flex-1 flex flex-col bg-white">
        {selectedConversationId ? (
          <div className="flex-1 overflow-y-auto">
            <MessageList
              messages={chronologicalMessages}
              conversationId={selectedConversationId}
              isReadOnly={isReadOnly}
            />
          </div>
        ) : (
          <div className="flex items-center justify-center h-full text-gray-500">
            <p className="text-sm">Select a conversation to view messages</p>
          </div>
        )}
      </div>
    </div>
  );
};
