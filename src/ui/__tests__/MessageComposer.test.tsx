/**
 * Unit tests for MessageComposer component.
 * 
 * References:
 * - UX Behavior (#12), Section 3.3
 * - Copy Rules (#13), Section 3
 * - State Machines (#7)
 * 
 * Tests validate:
 * - Disabled send conditions
 * - Optimistic updates
 * - Failure handling
 * - Message content handling
 */

import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MessageComposer } from "../components/MessageComposer";
import { MessageViewModel } from "../types";

describe("MessageComposer", () => {
  const mockOnSendMessage = jest.fn();
  const mockOnDeliveryUpdate = jest.fn();

  const createMockMessage = (state: "sent" | "delivered" | "failed"): MessageViewModel => ({
    message_id: "msg-001",
    sender_id: "device-001",
    conversation_id: "conv-001",
    state,
    created_at: new Date().toISOString(),
    expires_at: new Date(Date.now() + 604800000).toISOString(),
    is_expired: false,
    is_failed: state === "failed",
    is_read_only: false,
    display_state: state === "sent" ? "queued" : state === "failed" ? "failed" : "delivered",
  });

  beforeEach(() => {
    mockOnSendMessage.mockClear();
    mockOnDeliveryUpdate.mockClear();
  });

  it("renders message composer correctly", () => {
    render(
      <MessageComposer
        conversationId="conv-001"
        senderId="device-001"
        sendDisabled={false}
        onSendMessage={mockOnSendMessage}
      />
    );

    expect(screen.getByPlaceholderText("Type your message")).toBeInTheDocument();
    expect(screen.getByText("Send")).toBeInTheDocument();
  });

  it("disables input when sendDisabled is true", () => {
    render(
      <MessageComposer
        conversationId="conv-001"
        senderId="device-001"
        sendDisabled={true}
        onSendMessage={mockOnSendMessage}
      />
    );

    const textarea = screen.getByPlaceholderText("Type your message");
    expect(textarea).toBeDisabled();
    expect(textarea).toHaveClass("cursor-not-allowed");
  });

  it("sends message when send button is clicked", async () => {
    const mockMessage = createMockMessage("sent");
    mockOnSendMessage.mockResolvedValue(mockMessage);

    render(
      <MessageComposer
        conversationId="conv-001"
        senderId="device-001"
        sendDisabled={false}
        onSendMessage={mockOnSendMessage}
      />
    );

    const textarea = screen.getByPlaceholderText("Type your message");
    const sendButton = screen.getByText("Send");

    fireEvent.change(textarea, { target: { value: "Test message" } });
    fireEvent.click(sendButton);

    await waitFor(() => {
      expect(mockOnSendMessage).toHaveBeenCalledWith(
        "conv-001",
        "device-001",
        "Test message"
      );
    });

    // Message content should be cleared after sending
    expect(textarea).toHaveValue("");
  });

  it("sends message when Enter key is pressed", async () => {
    const mockMessage = createMockMessage("sent");
    mockOnSendMessage.mockResolvedValue(mockMessage);

    render(
      <MessageComposer
        conversationId="conv-001"
        senderId="device-001"
        sendDisabled={false}
        onSendMessage={mockOnSendMessage}
      />
    );

    const textarea = screen.getByPlaceholderText("Type your message");

    fireEvent.change(textarea, { target: { value: "Test message" } });
    fireEvent.keyPress(textarea, { key: "Enter", code: "Enter", charCode: 13 });

    await waitFor(() => {
      expect(mockOnSendMessage).toHaveBeenCalledWith(
        "conv-001",
        "device-001",
        "Test message"
      );
    });
  });

  it("does not send message when Shift+Enter is pressed", () => {
    render(
      <MessageComposer
        conversationId="conv-001"
        senderId="device-001"
        sendDisabled={false}
        onSendMessage={mockOnSendMessage}
      />
    );

    const textarea = screen.getByPlaceholderText("Type your message");

    fireEvent.change(textarea, { target: { value: "Test message" } });
    fireEvent.keyPress(textarea, {
      key: "Enter",
      code: "Enter",
      charCode: 13,
      shiftKey: true,
    });

    expect(mockOnSendMessage).not.toHaveBeenCalled();
  });

  it("does not send empty message", () => {
    render(
      <MessageComposer
        conversationId="conv-001"
        senderId="device-001"
        sendDisabled={false}
        onSendMessage={mockOnSendMessage}
      />
    );

    const sendButton = screen.getByText("Send");
    fireEvent.click(sendButton);

    expect(mockOnSendMessage).not.toHaveBeenCalled();
  });

  it("does not send message when disabled", () => {
    render(
      <MessageComposer
        conversationId="conv-001"
        senderId="device-001"
        sendDisabled={true}
        onSendMessage={mockOnSendMessage}
      />
    );

    const textarea = screen.getByPlaceholderText("Type your message");
    const sendButton = screen.getByText("Send");

    fireEvent.change(textarea, { target: { value: "Test message" } });
    fireEvent.click(sendButton);

    expect(mockOnSendMessage).not.toHaveBeenCalled();
  });

  it("handles send failure gracefully", async () => {
    const error = new Error("Failed to send message");
    mockOnSendMessage.mockRejectedValue(error);

    const consoleErrorSpy = jest.spyOn(console, "error").mockImplementation();

    render(
      <MessageComposer
        conversationId="conv-001"
        senderId="device-001"
        sendDisabled={false}
        onSendMessage={mockOnSendMessage}
      />
    );

    const textarea = screen.getByPlaceholderText("Type your message");
    const sendButton = screen.getByText("Send");

    fireEvent.change(textarea, { target: { value: "Test message" } });
    fireEvent.click(sendButton);

    await waitFor(() => {
      expect(mockOnSendMessage).toHaveBeenCalled();
    });

    expect(consoleErrorSpy).toHaveBeenCalledWith(
      "Failed to send message:",
      error
    );

    consoleErrorSpy.mockRestore();
  });

  it("trims message content before sending", async () => {
    const mockMessage = createMockMessage("sent");
    mockOnSendMessage.mockResolvedValue(mockMessage);

    render(
      <MessageComposer
        conversationId="conv-001"
        senderId="device-001"
        sendDisabled={false}
        onSendMessage={mockOnSendMessage}
      />
    );

    const textarea = screen.getByPlaceholderText("Type your message");
    const sendButton = screen.getByText("Send");

    fireEvent.change(textarea, { target: { value: "  Test message  " } });
    fireEvent.click(sendButton);

    await waitFor(() => {
      expect(mockOnSendMessage).toHaveBeenCalledWith(
        "conv-001",
        "device-001",
        "Test message"
      );
    });
  });
});
