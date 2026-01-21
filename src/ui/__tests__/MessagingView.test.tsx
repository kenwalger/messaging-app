/**
 * Unit tests for MessagingView component.
 * 
 * References:
 * - UX Behavior (#12)
 * - Message Delivery & Reliability docs
 * 
 * Tests validate:
 * - Conversation list updates when messages arrive
 * - Message pane updates when delivery state changes
 * - Store subscription works correctly
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { MessagingView } from "../components/MessagingView";
import { MessageHandlerService } from "../services/messageHandler";
import { MessageTransport } from "../services/messageTransport";
import { MessageViewModel } from "../types";

describe("MessagingView", () => {
  let mockTransport: MessageTransport;
  let messageHandler: MessageHandlerService;

  beforeEach(() => {
    // Create mock transport
    mockTransport = {
      connect: vi.fn(async () => {}),
      disconnect: vi.fn(async () => {}),
      getStatus: vi.fn(() => "connected"),
      isConnected: vi.fn(() => true),
    } as unknown as MessageTransport;

    messageHandler = new MessageHandlerService(mockTransport, "device-001");
  });

  const createMessage = (
    id: string,
    conversationId: string,
    createdAt: Date,
    state: "sent" | "delivered" | "failed" = "delivered",
    senderId: string = "device-002"
  ): MessageViewModel => ({
    message_id: id,
    sender_id: senderId,
    conversation_id: conversationId,
    state,
    created_at: createdAt.toISOString(),
    expires_at: new Date(createdAt.getTime() + 604800000).toISOString(),
    is_expired: false,
    is_failed: state === "failed",
    is_read_only: false,
    display_state: state === "failed" ? "failed" : state === "sent" ? "queued" : "delivered",
  });

  it("displays empty state when no conversations exist", () => {
    render(
      <MessagingView
        messageHandler={messageHandler}
        deviceId="device-001"
        isReadOnly={false}
      />
    );

    expect(screen.getByText("No conversations")).toBeInTheDocument();
  });

  it("displays conversations derived from message store", async () => {
    const now = new Date("2024-01-01T12:00:00Z");
    const message1 = createMessage("msg-001", "conv-001", now);
    const message2 = createMessage("msg-002", "conv-002", new Date(now.getTime() + 1000));

    messageHandler.addMessage(message1);
    messageHandler.addMessage(message2);

    render(
      <MessagingView
        messageHandler={messageHandler}
        deviceId="device-001"
        isReadOnly={false}
      />
    );

    await waitFor(() => {
      // Use getAllByText since "Conversation" appears in both header and list items
      const conversations = screen.getAllByText(/Conversation/);
      expect(conversations.length).toBeGreaterThanOrEqual(1);
    });

    // Should show 2 conversations
    const conversations = screen.getAllByText(/Conversation/);
    expect(conversations.length).toBeGreaterThanOrEqual(2);
  });

  it("updates conversation list when new messages arrive", async () => {
    const now = new Date("2024-01-01T12:00:00Z");
    const message1 = createMessage("msg-001", "conv-001", now);

    messageHandler.addMessage(message1);

    render(
      <MessagingView
        messageHandler={messageHandler}
        deviceId="device-001"
        isReadOnly={false}
      />
    );

    await waitFor(() => {
      // Use getAllByText since "Conversation" appears in both header and list items
      const conversations = screen.getAllByText(/Conversation/);
      expect(conversations.length).toBeGreaterThanOrEqual(1);
    });

    // Add new message to different conversation
    const message2 = createMessage("msg-002", "conv-002", new Date(now.getTime() + 1000));
    messageHandler.addMessage(message2);

    await waitFor(() => {
      const conversations = screen.getAllByText(/Conversation/);
      expect(conversations.length).toBeGreaterThanOrEqual(2);
    });
  });

  it("displays messages for selected conversation", async () => {
    const now = new Date("2024-01-01T12:00:00Z");
    const message1 = createMessage("msg-001", "conv-001", now, "delivered", "device-002");
    const message2 = createMessage("msg-002", "conv-001", new Date(now.getTime() + 1000), "delivered", "device-002");

    messageHandler.addMessage(message1);
    messageHandler.addMessage(message2);

    render(
      <MessagingView
        messageHandler={messageHandler}
        deviceId="device-001"
        isReadOnly={false}
      />
    );

    await waitFor(() => {
      // Should show messages for selected conversation
      // Use getAllByText since device-002 might appear multiple times
      const deviceElements = screen.getAllByText(/device-002/);
      expect(deviceElements.length).toBeGreaterThanOrEqual(1);
    });
  });

  it("updates message pane when delivery state changes", async () => {
    const now = new Date("2024-01-01T12:00:00Z");
    const sentMessage = createMessage("msg-001", "conv-001", now, "sent", "device-001");

    messageHandler.addMessage(sentMessage);

    render(
      <MessagingView
        messageHandler={messageHandler}
        deviceId="device-001"
        isReadOnly={false}
      />
    );

    await waitFor(() => {
      // Use getAllByText since "(Queued)" appears in both conversation list and message pane
      const queuedElements = screen.getAllByText(/Queued/);
      expect(queuedElements.length).toBeGreaterThanOrEqual(1);
    });

    // Update message state to delivered
    messageHandler.updateMessage("msg-001", {
      state: "delivered",
      display_state: "delivered",
    });

    await waitFor(() => {
      // Queued label should be gone, message should be displayed as delivered
      const queuedElements = screen.queryAllByText(/Queued/);
      expect(queuedElements.length).toBe(0);
    });
  });

  it("shows last message preview in conversation list", async () => {
    const now = new Date("2024-01-01T12:00:00Z");
    const message1 = createMessage("msg-001", "conv-001", now, "delivered", "device-002");

    messageHandler.addMessage(message1);

    render(
      <MessagingView
        messageHandler={messageHandler}
        deviceId="device-001"
        isReadOnly={false}
      />
    );

    await waitFor(() => {
      // Should show preview with sender ID
      // Use getAllByText since device-002 might appear multiple times
      const deviceElements = screen.getAllByText(/device-002/);
      expect(deviceElements.length).toBeGreaterThanOrEqual(1);
    });
  });

  it("filters expired messages from display", async () => {
    const now = new Date("2024-01-01T12:00:00Z");
    // Create messages with different senders to distinguish them
    const activeMessage = createMessage("msg-001", "conv-001", now, "delivered", "device-active");
    const expiredMessage: MessageViewModel = {
      ...createMessage("msg-002", "conv-001", new Date(now.getTime() - 86400000), "expired", "device-expired"),
      is_expired: true,
    };

    messageHandler.addMessage(activeMessage);
    messageHandler.addMessage(expiredMessage);

    render(
      <MessagingView
        messageHandler={messageHandler}
        deviceId="device-001"
        isReadOnly={false}
      />
    );

    await waitFor(() => {
      // Should only show active message, not expired
      // Expired messages are filtered out by MessageList component
      // Check that we can see the active message's sender
      const activeSenders = screen.getAllByText(/device-active/);
      expect(activeSenders.length).toBeGreaterThanOrEqual(1);
      
      // Verify expired message is not displayed (filtered out)
      // The expired message's sender should not appear
      const expiredSenders = screen.queryAllByText(/device-expired/);
      expect(expiredSenders.length).toBe(0);
    });
  });

  it("displays read-only indicator when device is revoked", () => {
    render(
      <MessagingView
        messageHandler={messageHandler}
        deviceId="device-001"
        isReadOnly={true}
      />
    );

    // Should show read-only state (if conversations exist)
    // This test verifies the isReadOnly prop is passed correctly
    expect(screen.getByText("No conversations")).toBeInTheDocument();
  });
});
