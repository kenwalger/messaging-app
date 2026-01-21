/**
 * Unit tests for message handler service.
 * 
 * References:
 * - Message Delivery & Reliability docs
 * - State Machines (#7)
 * - Resolved Clarifications (#51)
 * 
 * Tests validate:
 * - Incoming message handling
 * - Deduplication
 * - State reconciliation
 * - Reconnection reconciliation
 */

import { MessageHandlerService } from "../services/messageHandler";
import { MessageTransport, ConnectionStatus } from "../services/messageTransport";
import { MessageViewModel } from "../types";

describe("MessageHandlerService", () => {
  let mockTransport: jest.Mocked<MessageTransport>;
  let handler: MessageHandlerService;
  let onMessageHandler: ((message: MessageViewModel) => void) | null = null;
  let onStatusChangeHandler: ((status: ConnectionStatus) => void) | null = null;

  beforeEach(() => {
    // Create mock transport
    mockTransport = {
      connect: jest.fn(async (deviceId, onMessage, onStatusChange) => {
        onMessageHandler = onMessage;
        onStatusChangeHandler = onStatusChange;
      }),
      disconnect: jest.fn(),
      getStatus: jest.fn(() => "connected"),
      isConnected: jest.fn(() => true),
    } as unknown as jest.Mocked<MessageTransport>;

    handler = new MessageHandlerService(mockTransport, "device-001");
  });

  const createMessage = (
    id: string,
    conversationId: string,
    state: "sent" | "delivered" | "failed" = "delivered"
  ): MessageViewModel => {
    const now = new Date();
    return {
      message_id: id,
      sender_id: "device-002",
      conversation_id: conversationId,
      state,
      created_at: now.toISOString(),
      expires_at: new Date(now.getTime() + 604800000).toISOString(),
      is_expired: false,
      is_failed: state === "failed",
      is_read_only: false,
      display_state: state === "failed" ? "failed" : "delivered",
    };
  };

  it("connects to transport on start", async () => {
    await handler.start();

    expect(mockTransport.connect).toHaveBeenCalledWith(
      "device-001",
      expect.any(Function),
      expect.any(Function)
    );
  });

  it("handles incoming messages and deduplicates", async () => {
    const onUpdate = jest.fn();
    handler.setOnMessagesUpdate(onUpdate);

    await handler.start();

    const message1 = createMessage("msg-001", "conv-001");
    const message2 = createMessage("msg-001", "conv-001"); // Duplicate

    // Simulate incoming messages
    if (onMessageHandler) {
      onMessageHandler(message1);
      onMessageHandler(message2);
    }

    const messages = handler.getMessages("conv-001");

    expect(messages).toHaveLength(1); // Deduplicated
    expect(messages[0].message_id).toBe("msg-001");
    expect(onUpdate).toHaveBeenCalledTimes(1); // Only called once for new message
  });

  it("notifies UI when new messages arrive", async () => {
    const onUpdate = jest.fn();
    handler.setOnMessagesUpdate(onUpdate);

    await handler.start();

    const message = createMessage("msg-001", "conv-001");

    if (onMessageHandler) {
      onMessageHandler(message);
    }

    expect(onUpdate).toHaveBeenCalledWith("conv-001", [message]);
  });

  it("handles state reconciliation correctly", async () => {
    await handler.start();

    // Add pending message
    const pendingMessage = createMessage("msg-001", "conv-001", "sent");
    handler.addMessage(pendingMessage);

    // Update to delivered
    handler.updateMessage("msg-001", {
      state: "delivered",
      display_state: "delivered",
    });

    const messages = handler.getMessages("conv-001");
    expect(messages[0].state).toBe("delivered");
  });

  it("handles reconnection reconciliation", async () => {
    const onUpdate = jest.fn();
    handler.setOnMessagesUpdate(onUpdate);

    await handler.start();

    // Simulate disconnect
    if (onStatusChangeHandler) {
      onStatusChangeHandler("disconnected");
    }

    // Simulate reconnect
    if (onStatusChangeHandler) {
      onStatusChangeHandler("connected");
    }

    // On reconnect, transport should fetch missed messages
    // (This is handled by the transport layer - polling will fetch, WebSocket will receive)
    const message1 = createMessage("msg-001", "conv-001");
    const message2 = createMessage("msg-002", "conv-001");

    if (onMessageHandler) {
      onMessageHandler(message1);
      onMessageHandler(message2);
    }

    const messages = handler.getMessages("conv-001");
    expect(messages).toHaveLength(2);
  });

  it("removes expired messages", () => {
    const now = new Date();
    const expiredMessage: MessageViewModel = {
      message_id: "msg-expired",
      sender_id: "device-002",
      conversation_id: "conv-001",
      state: "delivered",
      created_at: new Date(now.getTime() - 86400000).toISOString(),
      expires_at: new Date(now.getTime() - 3600000).toISOString(), // Expired 1 hour ago
      is_expired: true,
      is_failed: false,
      is_read_only: false,
      display_state: "delivered",
    };

    handler.addMessage(expiredMessage);
    const removed = handler.removeExpiredMessages(now);

    expect(removed).toBe(1);
    expect(handler.getMessages("conv-001")).toHaveLength(0);
  });

  it("disconnects from transport on stop", async () => {
    await handler.start();
    await handler.stop();

    expect(mockTransport.disconnect).toHaveBeenCalled();
  });

  it("preserves ordering when adding messages", async () => {
    await handler.start();

    const now = new Date();
    const message1 = createMessage("msg-001", "conv-001");
    message1.created_at = new Date(now.getTime() - 7200000).toISOString(); // 2 hours ago

    const message2 = createMessage("msg-002", "conv-001");
    message2.created_at = now.toISOString(); // Now

    const message3 = createMessage("msg-003", "conv-001");
    message3.created_at = new Date(now.getTime() - 3600000).toISOString(); // 1 hour ago

    handler.addMessage(message1);
    handler.addMessage(message2);
    handler.addMessage(message3);

    const messages = handler.getMessages("conv-001");

    expect(messages[0].message_id).toBe("msg-002"); // Newest first
    expect(messages[1].message_id).toBe("msg-003");
    expect(messages[2].message_id).toBe("msg-001");
  });
});
