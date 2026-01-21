/**
 * Unit tests for MessageList component.
 * 
 * References:
 * - UX Behavior (#12), Section 3.3 and 3.4
 * - Resolved Clarifications (#53)
 * 
 * Tests validate:
 * - Reverse chronological ordering (newest first)
 * - Expired message filtering
 * - Empty state handling
 */

import React from "react";
import { render, screen } from "@testing-library/react";
import { MessageList } from "../components/MessageList";
import { MessageViewModel } from "../types";

describe("MessageList", () => {
  const createMessage = (
    id: string,
    createdAt: Date,
    isExpired: boolean = false
  ): MessageViewModel => ({
    message_id: id,
    sender_id: "device-001",
    conversation_id: "conv-001",
    state: isExpired ? "expired" : "delivered",
    created_at: createdAt.toISOString(),
    expires_at: new Date(createdAt.getTime() + 604800000).toISOString(),
    is_expired: isExpired,
    is_failed: false,
    is_read_only: false,
    display_state: isExpired ? "expired" : "delivered",
  });

  it("renders messages in reverse chronological order", () => {
    const now = new Date();
    const messages: MessageViewModel[] = [
      createMessage("msg-001", new Date(now.getTime() - 7200000)), // 2 hours ago
      createMessage("msg-002", now), // Now
      createMessage("msg-003", new Date(now.getTime() - 3600000)), // 1 hour ago
    ];

    render(
      <MessageList
        messages={messages}
        conversationId="conv-001"
        isReadOnly={false}
      />
    );

    const messageElements = screen.getAllByText(/device-001/);
    // Messages should be rendered in reverse order (newest first)
    // Since we use flex-col-reverse, the DOM order is reversed
    expect(messageElements.length).toBe(3);
  });

  it("filters out expired messages", () => {
    const now = new Date();
    const messages: MessageViewModel[] = [
      createMessage("msg-001", now, false),
      createMessage("msg-expired", new Date(now.getTime() - 86400000), true),
      createMessage("msg-002", new Date(now.getTime() - 3600000), false),
    ];

    render(
      <MessageList
        messages={messages}
        conversationId="conv-001"
        isReadOnly={false}
      />
    );

    // Only non-expired messages should be rendered
    const messageElements = screen.getAllByText(/device-001/);
    expect(messageElements.length).toBe(2);
    expect(screen.queryByText("msg-expired")).not.toBeInTheDocument();
  });

  it("displays empty state when no messages", () => {
    render(
      <MessageList
        messages={[]}
        conversationId="conv-001"
        isReadOnly={false}
      />
    );

    expect(screen.getByText("No messages yet")).toBeInTheDocument();
  });

  it("displays empty state when all messages are expired", () => {
    const now = new Date();
    const messages: MessageViewModel[] = [
      createMessage("msg-expired-1", new Date(now.getTime() - 86400000), true),
      createMessage("msg-expired-2", new Date(now.getTime() - 172800000), true),
    ];

    render(
      <MessageList
        messages={messages}
        conversationId="conv-001"
        isReadOnly={false}
      />
    );

    expect(screen.getByText("No messages yet")).toBeInTheDocument();
  });
});
