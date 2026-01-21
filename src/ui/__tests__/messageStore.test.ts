/**
 * Unit tests for message store (deduplication and ordering).
 * 
 * References:
 * - Message Delivery & Reliability docs
 * - State Machines (#7)
 * - UX Behavior (#12)
 * 
 * Tests validate:
 * - Message deduplication by message ID
 * - Reverse chronological ordering
 * - State reconciliation (merge without overwriting incorrectly)
 */

import { InMemoryMessageStore } from "../services/messageStore";
import { MessageViewModel } from "../types";

describe("InMemoryMessageStore", () => {
  let store: InMemoryMessageStore;

  beforeEach(() => {
    store = new InMemoryMessageStore();
  });

  const createMessage = (
    id: string,
    conversationId: string,
    createdAt: Date,
    state: "sent" | "delivered" | "failed" = "delivered"
  ): MessageViewModel => ({
    message_id: id,
    sender_id: "device-001",
    conversation_id: conversationId,
    state,
    created_at: createdAt.toISOString(),
    expires_at: new Date(createdAt.getTime() + 604800000).toISOString(),
    is_expired: false,
    is_failed: state === "failed",
    is_read_only: false,
    display_state: state === "failed" ? "failed" : "delivered",
  });

  it("adds new messages correctly", () => {
    const now = new Date();
    const message = createMessage("msg-001", "conv-001", now);

    const isNew = store.addMessage(message);

    expect(isNew).toBe(true);
    expect(store.getMessages("conv-001")).toHaveLength(1);
    expect(store.getMessages("conv-001")[0].message_id).toBe("msg-001");
  });

  it("deduplicates messages by message ID", () => {
    const now = new Date();
    const message1 = createMessage("msg-001", "conv-001", now);
    const message2 = createMessage("msg-001", "conv-001", now); // Same ID

    const isNew1 = store.addMessage(message1);
    const isNew2 = store.addMessage(message2);

    expect(isNew1).toBe(true);
    expect(isNew2).toBe(false); // Duplicate
    expect(store.getMessages("conv-001")).toHaveLength(1);
  });

  it("maintains reverse chronological order (newest first)", () => {
    const now = new Date();
    const message1 = createMessage("msg-001", "conv-001", new Date(now.getTime() - 7200000)); // 2 hours ago
    const message2 = createMessage("msg-002", "conv-001", now); // Now
    const message3 = createMessage("msg-003", "conv-001", new Date(now.getTime() - 3600000)); // 1 hour ago

    store.addMessage(message1);
    store.addMessage(message2);
    store.addMessage(message3);

    const messages = store.getMessages("conv-001");

    expect(messages).toHaveLength(3);
    expect(messages[0].message_id).toBe("msg-002"); // Newest first
    expect(messages[1].message_id).toBe("msg-003");
    expect(messages[2].message_id).toBe("msg-001");
  });

  it("does not overwrite delivered state with pending state", () => {
    const now = new Date();
    const deliveredMessage = createMessage("msg-001", "conv-001", now, "delivered");
    const pendingMessage = createMessage("msg-001", "conv-001", now, "sent"); // Same ID, pending state

    store.addMessage(deliveredMessage);
    store.addMessage(pendingMessage);

    const messages = store.getMessages("conv-001");
    expect(messages).toHaveLength(1);
    expect(messages[0].state).toBe("delivered"); // Should not be overwritten with "sent"
  });

  it("updates pending state to delivered state", () => {
    const now = new Date();
    const pendingMessage = createMessage("msg-001", "conv-001", now, "sent");
    const deliveredMessage = createMessage("msg-001", "conv-001", now, "delivered"); // Same ID, delivered state

    store.addMessage(pendingMessage);
    store.addMessage(deliveredMessage);

    const messages = store.getMessages("conv-001");
    expect(messages).toHaveLength(1);
    expect(messages[0].state).toBe("delivered"); // Should be updated to delivered
  });

  it("updates message state correctly", () => {
    const now = new Date();
    const message = createMessage("msg-001", "conv-001", now, "sent");

    store.addMessage(message);
    const updated = store.updateMessage("msg-001", {
      state: "delivered",
      display_state: "delivered",
    });

    expect(updated).toBe(true);
    const messages = store.getMessages("conv-001");
    expect(messages[0].state).toBe("delivered");
    expect(messages[0].display_state).toBe("delivered");
  });

  it("returns false when updating non-existent message", () => {
    const updated = store.updateMessage("msg-nonexistent", {
      state: "delivered",
    });

    expect(updated).toBe(false);
  });

  it("removes expired messages", () => {
    const now = new Date();
    const expiredMessage = createMessage(
      "msg-expired",
      "conv-001",
      new Date(now.getTime() - 86400000), // 1 day ago
      "delivered"
    );
    expiredMessage.expires_at = new Date(now.getTime() - 3600000).toISOString(); // Expired 1 hour ago

    const activeMessage = createMessage("msg-active", "conv-001", now, "delivered");

    store.addMessage(expiredMessage);
    store.addMessage(activeMessage);

    const removed = store.removeExpiredMessages(now);

    expect(removed).toBe(1);
    const messages = store.getMessages("conv-001");
    expect(messages).toHaveLength(1);
    expect(messages[0].message_id).toBe("msg-active");
  });

  it("handles messages from different conversations separately", () => {
    const now = new Date();
    const message1 = createMessage("msg-001", "conv-001", now);
    const message2 = createMessage("msg-002", "conv-002", now);

    store.addMessage(message1);
    store.addMessage(message2);

    expect(store.getMessages("conv-001")).toHaveLength(1);
    expect(store.getMessages("conv-002")).toHaveLength(1);
    expect(store.getMessages("conv-001")[0].message_id).toBe("msg-001");
    expect(store.getMessages("conv-002")[0].message_id).toBe("msg-002");
  });

  it("clears all messages", () => {
    const now = new Date();
    store.addMessage(createMessage("msg-001", "conv-001", now));
    store.addMessage(createMessage("msg-002", "conv-002", now));

    store.clear();

    expect(store.getMessages("conv-001")).toHaveLength(0);
    expect(store.getMessages("conv-002")).toHaveLength(0);
  });
});
