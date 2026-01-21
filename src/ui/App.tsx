/**
 * Main App component for read-only UI shell.
 * 
 * References:
 * - UX Behavior (#12)
 * - Copy Rules (#13)
 * - UI Domain Adapter Layer (latest)
 * 
 * Read-only UI shell that consumes UI domain models only.
 * No API calls, no WebSocket usage, no side effects.
 */

import React, { useState } from "react";
import { ConversationList } from "./components/ConversationList";
import { MessageList } from "./components/MessageList";
import { StatusIndicator } from "./components/StatusIndicator";
import { ConversationViewModel, DeviceStateViewModel, MessageViewModel } from "./types";

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
}

/**
 * App component per UX Behavior (#12), Section 3.1.
 * 
 * Read-only UI shell that displays conversations and messages.
 * No message sending, no WebSocket usage, no API calls per constraints.
 * 
 * Neutral, enterprise-safe visual tone per UX Behavior (#12), Section 2.
 */
export const App: React.FC<AppProps> = ({
  deviceState,
  conversations,
  messagesByConversation,
}) => {
  const [selectedConversationId, setSelectedConversationId] = useState<string | null>(
    conversations.length > 0 ? conversations[0].conversation_id : null
  );

  const selectedMessages = selectedConversationId
    ? messagesByConversation[selectedConversationId] || []
    : [];

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

      {/* Main: Message List */}
      <div className="flex-1 flex flex-col bg-white">
        {selectedConversationId ? (
          <div className="flex-1 overflow-y-auto">
            <MessageList
              messages={selectedMessages}
              conversationId={selectedConversationId}
              isReadOnly={deviceState.is_read_only}
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
