/**
 * Unit tests for ConversationList component.
 * 
 * References:
 * - UX Behavior (#12), Section 3.2
 * - Copy Rules (#13), Section 3
 * 
 * Tests validate:
 * - Correct rendering of conversations
 * - Neutral mode visual enforcement
 * - Empty state handling
 */

import React from "react";
import { render, screen } from "@testing-library/react";
import { ConversationList } from "../components/ConversationList";
import { ConversationViewModel } from "../types";

describe("ConversationList", () => {
  const createConversation = (
    id: string,
    participantCount: number,
    isReadOnly: boolean = false
  ): ConversationViewModel => ({
    conversation_id: id,
    state: "active",
    participant_count: participantCount,
    can_send: !isReadOnly,
    is_read_only: isReadOnly,
    send_disabled: isReadOnly,
    last_message_at: new Date().toISOString(),
    created_at: new Date().toISOString(),
    display_name: participantCount === 1
      ? "Conversation"
      : `Conversation (${participantCount} participants)`,
  });

  it("renders conversations correctly", () => {
    const conversations: ConversationViewModel[] = [
      createConversation("conv-001", 3),
      createConversation("conv-002", 2),
    ];

    render(
      <ConversationList
        conversations={conversations}
        isReadOnly={false}
      />
    );

    expect(screen.getByText("Conversations")).toBeInTheDocument();
    expect(screen.getByText("Conversation (3 participants)")).toBeInTheDocument();
    expect(screen.getByText("Conversation (2 participants)")).toBeInTheDocument();
  });

  it("shows read-only indicator when in neutral enterprise mode", () => {
    const conversations: ConversationViewModel[] = [
      createConversation("conv-001", 2, true),
    ];

    render(
      <ConversationList
        conversations={conversations}
        isReadOnly={true}
      />
    );

    expect(screen.getAllByText("Read-only").length).toBeGreaterThan(0);
  });

  it("displays empty state when no conversations", () => {
    render(
      <ConversationList
        conversations={[]}
        isReadOnly={false}
      />
    );

    expect(screen.getByText("No conversations")).toBeInTheDocument();
  });

  it("calls onSelectConversation when conversation is clicked", () => {
    const conversations: ConversationViewModel[] = [
      createConversation("conv-001", 2),
    ];

    const handleSelect = jest.fn();

    render(
      <ConversationList
        conversations={conversations}
        onSelectConversation={handleSelect}
        isReadOnly={false}
      />
    );

    const conversationElement = screen.getByText("Conversation (2 participants)");
    conversationElement.click();

    expect(handleSelect).toHaveBeenCalledWith("conv-001");
  });

  it("applies correct styling for read-only mode", () => {
    const conversations: ConversationViewModel[] = [
      createConversation("conv-001", 2, true),
    ];

    const { container } = render(
      <ConversationList
        conversations={conversations}
        isReadOnly={true}
      />
    );

    const conversationElement = container.querySelector(".opacity-75");
    expect(conversationElement).toBeInTheDocument();
  });
});
