/**
 * Main App component for interactive messaging UI.
 * 
 * References:
 * - UX Behavior (#12)
 * - Copy Rules (#13)
 * - UI Domain Adapter Layer (latest)
 * - Message Delivery & Reliability docs
 * 
 * Interactive UI shell with message composition and sending.
 * Handles optimistic updates and delivery state transitions.
 */

import React, { useState, useCallback } from "react";
import { ConversationList } from "./components/ConversationList";
import { MessageList } from "./components/MessageList";
import { MessageComposer } from "./components/MessageComposer";
import { StatusIndicator } from "./components/StatusIndicator";
import { ConversationViewModel, DeviceStateViewModel, MessageViewModel } from "./types";
import { MessageApiService } from "./services/messageApi";

export interface AppProps {
  /**
   * Device state view model per UI Domain Adapter Layer.
   */
  deviceState: DeviceStateViewModel;
  
  /**
   * List of conversation view models per UI Domain Adapter Layer.
   * Should be pre-filtered to active conversations only.
   */
  conversations: ConversationViewModel[];
  
  /**
   * Map of conversation ID to messages per UI Domain Adapter Layer.
   * Messages should be pre-sorted in reverse chronological order.
   */
  messagesByConversation: Record<string, MessageViewModel[]>;
  
  /**
   * Message API service for sending messages.
   */
  messageApi: MessageApiService;
  
  /**
   * Callback when messages are updated (for parent state management).
   */
  onMessagesUpdate?: (conversationId: string, messages: MessageViewModel[]) => void;
}

/**
 * App component per UX Behavior (#12), Section 3.1 and 3.3.
 * 
 * Interactive UI shell with message composition and sending.
 * Handles optimistic updates and delivery state transitions.
 * 
 * Neutral, enterprise-safe visual tone per UX Behavior (#12), Section 2.
 */
export const App: React.FC<AppProps> = ({
  deviceState,
  conversations,
  messagesByConversation: initialMessagesByConversation,
  messageApi,
  onMessagesUpdate,
}) => {
  const [selectedConversationId, setSelectedConversationId] = useState<string | null>(
    conversations.length > 0 ? conversations[0].conversation_id : null
  );

  const [messagesByConversation, setMessagesByConversation] = useState<
    Record<string, MessageViewModel[]>
  >(initialMessagesByConversation);

  const selectedMessages = selectedConversationId
    ? messagesByConversation[selectedConversationId] || []
    : [];

  const selectedConversation = selectedConversationId
    ? conversations.find((c) => c.conversation_id === selectedConversationId)
    : null;

  /**
   * Handle sending a message per UX Behavior (#12), Section 3.3.
   * 
   * On send:
   * - Message enters PENDING state immediately (optimistic update)
   * - UI updates optimistically
   * - Delivery state transitions handled via subscription mechanism
   */
  const handleSendMessage = useCallback(
    async (
      conversationId: string,
      senderId: string,
      content: string
    ): Promise<MessageViewModel> => {
      // Send message via API
      const message = await messageApi.sendMessage(conversationId, senderId, content);

      // Optimistic update: add message to conversation
      setMessagesByConversation((prev) => {
        const conversationMessages = prev[conversationId] || [];
        const updated = [message, ...conversationMessages]; // Newest first
        const next = { ...prev, [conversationId]: updated };
        
        // Notify parent of update
        if (onMessagesUpdate) {
          onMessagesUpdate(conversationId, updated);
        }
        
        return next;
      });

      // Subscribe to delivery updates
      messageApi.subscribeToDeliveryUpdates(message.message_id, (newState) => {
        setMessagesByConversation((prev) => {
          const conversationMessages = prev[conversationId] || [];
          const updated = conversationMessages.map((msg) =>
            msg.message_id === message.message_id
              ? {
                  ...msg,
                  state: newState,
                  is_failed: newState === "failed",
                  display_state: newState === "failed" ? "failed" : "delivered",
                }
              : msg
          );
          const next = { ...prev, [conversationId]: updated };
          
          // Notify parent of update
          if (onMessagesUpdate) {
            onMessagesUpdate(conversationId, updated);
          }
          
          return next;
        });
      });

      return message;
    },
    [messageApi, onMessagesUpdate]
  );


  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar: Conversation List */}
      <div className="w-80 bg-white border-r border-gray-200 flex flex-col">
        <StatusIndicator
          status={deviceState.display_status}
          isReadOnly={deviceState.is_read_only}
        />
        <div className="flex-1 overflow-y-auto">
          <ConversationList
            conversations={conversations}
            onSelectConversation={setSelectedConversationId}
            isReadOnly={deviceState.is_read_only}
          />
        </div>
      </div>

      {/* Main: Message List and Composer */}
      <div className="flex-1 flex flex-col bg-white">
        {selectedConversationId && selectedConversation ? (
          <>
            <div className="flex-1 overflow-y-auto">
              <MessageList
                messages={selectedMessages}
                conversationId={selectedConversationId}
                isReadOnly={deviceState.is_read_only}
              />
            </div>
            <MessageComposer
              conversationId={selectedConversationId}
              senderId={deviceState.device_id}
              sendDisabled={
                deviceState.is_read_only ||
                !deviceState.can_send ||
                selectedConversation.send_disabled
              }
              onSendMessage={handleSendMessage}
            />
          </>
        ) : (
          <div className="flex items-center justify-center h-full text-gray-500">
            <p className="text-sm">Select a conversation to view messages</p>
          </div>
        )}
      </div>
    </div>
  );
};
