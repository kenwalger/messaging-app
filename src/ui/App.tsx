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

import React, { useState, useCallback, useEffect, useRef } from "react";
import { ConversationList } from "./components/ConversationList";
import { MessageList } from "./components/MessageList";
import { MessageComposer } from "./components/MessageComposer";
import { StatusIndicator } from "./components/StatusIndicator";
import { ConversationViewModel, DeviceStateViewModel, MessageViewModel } from "./types";
import { MessageApiService } from "./services/messageApi";
import { MessageHandlerService } from "./services/messageHandler";
import { MessageTransport } from "./services/messageTransport";

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
   * Message transport for receiving incoming messages.
   * WebSocket (preferred) or REST polling (fallback).
   */
  messageTransport: MessageTransport;
  
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
  messageTransport,
  onMessagesUpdate,
}) => {
  const [selectedConversationId, setSelectedConversationId] = useState<string | null>(
    conversations.length > 0 ? conversations[0].conversation_id : null
  );

  const [messagesByConversation, setMessagesByConversation] = useState<
    Record<string, MessageViewModel[]>
  >(initialMessagesByConversation);

  // Message handler service for incoming messages
  const messageHandlerRef = useRef<MessageHandlerService | null>(null);
  // Use ref for onMessagesUpdate to avoid stale closure
  const onMessagesUpdateRef = useRef(onMessagesUpdate);
  // Use ref for initialMessagesByConversation to avoid recreating handler on every message change
  const initialMessagesRef = useRef(initialMessagesByConversation);
  
  // Update refs when callbacks/props change
  useEffect(() => {
    onMessagesUpdateRef.current = onMessagesUpdate;
  }, [onMessagesUpdate]);

  useEffect(() => {
    initialMessagesRef.current = initialMessagesByConversation;
  }, [initialMessagesByConversation]);

  /**
   * Initialize message handler service for incoming messages.
   * 
   * Sets up transport connection and message store integration.
   * Handles deduplication, ordering, and state reconciliation automatically.
   * 
   * Note: initialMessagesByConversation is excluded from deps to avoid recreating
   * the handler on every message change. It's handled via ref instead.
   */
  useEffect(() => {
    // Create message handler service
    const messageHandler = new MessageHandlerService(messageTransport, deviceState.device_id);

    // Set callback for message updates
    // Use ref to avoid stale closure
    messageHandler.setOnMessagesUpdate((conversationId, messages) => {
      // Update local state to trigger re-render
      setMessagesByConversation((prev) => {
        const next = { ...prev, [conversationId]: messages };
        
        // Notify parent of update using ref to avoid stale closure
        if (onMessagesUpdateRef.current) {
          onMessagesUpdateRef.current(conversationId, messages);
        }
        
        return next;
      });
    });

    // Initialize store with existing messages
    // Use ref to avoid recreating handler on every message change
    const initialMessages = initialMessagesRef.current;
    for (const [conversationId, messages] of Object.entries(initialMessages)) {
      for (const message of messages) {
        messageHandler.addMessage(message);
      }
    }

    // Start receiving messages
    messageHandler.start().catch(() => {
      // Connection errors handled silently - transport will retry
    });

    messageHandlerRef.current = messageHandler;

    // Cleanup on unmount
    return () => {
      messageHandler.stop().catch(() => {
        // Disconnect errors handled silently
      });
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [messageTransport, deviceState.device_id]); // onMessagesUpdate and initialMessagesByConversation handled via refs

  /**
   * Periodic cleanup of expired messages.
   * 
   * Per UX Behavior (#12), Section 3.4: expired messages removed automatically.
   */
  useEffect(() => {
    const interval = setInterval(() => {
      if (messageHandlerRef.current) {
        messageHandlerRef.current.removeExpiredMessages();
      }
    }, 60000); // Check every minute

    return () => clearInterval(interval);
  }, []);

  // Get messages from handler store (which includes both sent and received messages)
  // Handler may be null during initialization or after unmount
  const selectedMessages = selectedConversationId
    ? (messageHandlerRef.current
        ? messageHandlerRef.current.getMessages(selectedConversationId)
        : messagesByConversation[selectedConversationId] || [])
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

      // Optimistic update: add message to message handler store
      // This ensures deduplication and proper ordering
      if (messageHandlerRef.current) {
        messageHandlerRef.current.addMessage(message);
      } else {
        // Fallback if handler not initialized yet
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
      }

      // Subscribe to delivery updates
      messageApi.subscribeToDeliveryUpdates(message.message_id, (newState) => {
        // Update message in handler store (ensures proper state reconciliation)
        if (messageHandlerRef.current) {
          messageHandlerRef.current.updateMessage(message.message_id, {
            state: newState,
            is_failed: newState === "failed",
            display_state: newState === "failed" ? "failed" : "delivered",
          });
        } else {
          // Fallback if handler not initialized yet
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
        }
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
