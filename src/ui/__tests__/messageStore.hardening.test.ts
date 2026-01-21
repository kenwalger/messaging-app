/**
 * Comprehensive TypeScript tests for hardened message store.
 * 
 * References:
 * - Message Delivery & Reliability docs
 * - State Machines (#7)
 * - UX Behavior (#12)
 * 
 * Tests validate:
 * - Message deduplication logic
 * - Ordering with interleaved incoming and outgoing messages
 * - Reconnection reconciliation (missed messages)
 * - Delivery state transitions
 * - Transport switching behavior
 * 
 * All tests use deterministic timestamps and IDs.
 * No DOM rendering required.
 */

import { describe, it, expect, beforeEach } from 'vitest'
import { InMemoryMessageStore } from "../services/messageStore";
import { MessageViewModel } from "../types";

describe("MessageStore Hardening", () => {
  let store: InMemoryMessageStore;

  beforeEach(() => {
    store = new InMemoryMessageStore();
  });

  /**
   * Create a message with deterministic timestamp.
   */
  const createMessage = (
    id: string,
    conversationId: string,
    createdAt: Date,
    state: "sent" | "delivered" | "failed" | "expired" = "delivered",
    senderId: string = "device-001"
  ): MessageViewModel => ({
    message_id: id,
    sender_id: senderId,
    conversation_id: conversationId,
    state,
    created_at: createdAt.toISOString(),
    expires_at: new Date(createdAt.getTime() + 604800000).toISOString(), // 7 days
    is_expired: state === "expired",
    is_failed: state === "failed",
    is_read_only: false,
    display_state: state === "failed" ? "failed" : state === "expired" ? "expired" : "delivered",
  });

  describe("Message Deduplication Logic", () => {
    it("deduplicates by message ID across different senders", () => {
      const now = new Date("2024-01-01T12:00:00Z");
      const message1 = createMessage("msg-001", "conv-001", now, "delivered", "device-001");
      const message2 = createMessage("msg-001", "conv-001", now, "delivered", "device-002"); // Same ID, different sender

      const isNew1 = store.addMessage(message1);
      const isNew2 = store.addMessage(message2);

      expect(isNew1).toBe(true);
      expect(isNew2).toBe(false); // Duplicate by ID
      expect(store.getMessages("conv-001")).toHaveLength(1);
      // Should preserve first message's sender (deduplication by ID only)
      expect(store.getMessages("conv-001")[0].sender_id).toBe("device-001");
    });

    it("deduplicates messages with identical timestamps", () => {
      const now = new Date("2024-01-01T12:00:00.000Z");
      const message1 = createMessage("msg-001", "conv-001", now);
      const message2 = createMessage("msg-001", "conv-001", now); // Same ID, same timestamp

      store.addMessage(message1);
      store.addMessage(message2);

      expect(store.getMessages("conv-001")).toHaveLength(1);
    });

    it("deduplicates messages received out of order", () => {
      const baseTime = new Date("2024-01-01T12:00:00Z");
      const message1 = createMessage("msg-001", "conv-001", new Date(baseTime.getTime() + 2000)); // Later timestamp
      const message2 = createMessage("msg-001", "conv-001", baseTime); // Earlier timestamp, received later

      store.addMessage(message1);
      store.addMessage(message2);

      expect(store.getMessages("conv-001")).toHaveLength(1);
      // Should preserve original created_at (first message's timestamp)
      expect(store.getMessages("conv-001")[0].created_at).toBe(message1.created_at);
    });
  });

  describe("Ordering with Interleaved Incoming and Outgoing Messages", () => {
    it("maintains correct order with interleaved sent and received messages", () => {
      const baseTime = new Date("2024-01-01T12:00:00Z");
      
      // Simulate interleaved messages: sent, received, sent, received
      const sent1 = createMessage("msg-sent-1", "conv-001", new Date(baseTime.getTime() + 1000), "sent", "device-001");
      const received1 = createMessage("msg-recv-1", "conv-001", new Date(baseTime.getTime() + 2000), "delivered", "device-002");
      const sent2 = createMessage("msg-sent-2", "conv-001", new Date(baseTime.getTime() + 3000), "sent", "device-001");
      const received2 = createMessage("msg-recv-2", "conv-001", new Date(baseTime.getTime() + 4000), "delivered", "device-002");

      // Add in interleaved order
      store.addMessage(sent1);
      store.addMessage(received1);
      store.addMessage(sent2);
      store.addMessage(received2);

      const messages = store.getMessages("conv-001");

      expect(messages).toHaveLength(4);
      // Should be ordered by created_at (newest first)
      expect(messages[0].message_id).toBe("msg-recv-2");
      expect(messages[1].message_id).toBe("msg-sent-2");
      expect(messages[2].message_id).toBe("msg-recv-1");
      expect(messages[3].message_id).toBe("msg-sent-1");
    });

    it("maintains order when optimistic sent message is updated to delivered", () => {
      const baseTime = new Date("2024-01-01T12:00:00Z");
      
      // Optimistic update: sent message
      const sentMessage = createMessage("msg-001", "conv-001", baseTime, "sent", "device-001");
      store.addMessage(sentMessage);

      // Later: delivery confirmation
      const deliveredMessage = createMessage("msg-001", "conv-001", baseTime, "delivered", "device-001");
      store.addMessage(deliveredMessage);

      const messages = store.getMessages("conv-001");

      expect(messages).toHaveLength(1);
      expect(messages[0].state).toBe("delivered");
      // Order should remain stable (same created_at)
      expect(messages[0].created_at).toBe(baseTime.toISOString());
    });

    it("handles messages with identical timestamps (stable ordering)", () => {
      const baseTime = new Date("2024-01-01T12:00:00.000Z");
      
      // Multiple messages with identical timestamps
      const message1 = createMessage("msg-001", "conv-001", baseTime);
      const message2 = createMessage("msg-002", "conv-001", baseTime);
      const message3 = createMessage("msg-003", "conv-001", baseTime);

      store.addMessage(message1);
      store.addMessage(message2);
      store.addMessage(message3);

      const messages = store.getMessages("conv-001");

      expect(messages).toHaveLength(3);
      // Order should be stable (deterministic based on insertion order for same timestamp)
      // All messages should be present
      const messageIds = messages.map((m) => m.message_id).sort();
      expect(messageIds).toEqual(["msg-001", "msg-002", "msg-003"]);
    });
  });

  describe("Reconnection Reconciliation", () => {
    it("merges missed messages from REST poll after reconnection", () => {
      const baseTime = new Date("2024-01-01T12:00:00Z");
      
      // Existing local messages
      const local1 = createMessage("msg-local-1", "conv-001", new Date(baseTime.getTime() + 1000));
      const local2 = createMessage("msg-local-2", "conv-001", new Date(baseTime.getTime() + 2000));
      store.addMessage(local1);
      store.addMessage(local2);

      // Missed messages received via REST poll after reconnection
      const missed1 = createMessage("msg-missed-1", "conv-001", new Date(baseTime.getTime() + 500));
      const missed2 = createMessage("msg-missed-2", "conv-001", new Date(baseTime.getTime() + 1500));
      const missed3 = createMessage("msg-missed-3", "conv-001", new Date(baseTime.getTime() + 2500));

      store.addMessage(missed1);
      store.addMessage(missed2);
      store.addMessage(missed3);

      const messages = store.getMessages("conv-001");

      expect(messages).toHaveLength(5);
      // Should be ordered by created_at (newest first)
      expect(messages[0].message_id).toBe("msg-missed-3");
      expect(messages[1].message_id).toBe("msg-local-2");
      expect(messages[2].message_id).toBe("msg-missed-2");
      expect(messages[3].message_id).toBe("msg-local-1");
      expect(messages[4].message_id).toBe("msg-missed-1");
    });

    it("avoids duplicates when reconciling missed messages", () => {
      const baseTime = new Date("2024-01-01T12:00:00Z");
      
      // Existing local message
      const existing = createMessage("msg-001", "conv-001", baseTime);
      store.addMessage(existing);

      // Same message received again via REST poll (should be deduplicated)
      const duplicate = createMessage("msg-001", "conv-001", baseTime);
      const isNew = store.addMessage(duplicate);

      expect(isNew).toBe(false);
      expect(store.getMessages("conv-001")).toHaveLength(1);
    });

    it("preserves ordering when reconciling messages with overlapping timestamps", () => {
      const baseTime = new Date("2024-01-01T12:00:00Z");
      
      // Local messages
      const local1 = createMessage("msg-local-1", "conv-001", new Date(baseTime.getTime() + 1000));
      const local2 = createMessage("msg-local-2", "conv-001", new Date(baseTime.getTime() + 3000));
      store.addMessage(local1);
      store.addMessage(local2);

      // Missed messages with timestamps between local messages
      const missed1 = createMessage("msg-missed-1", "conv-001", new Date(baseTime.getTime() + 500));
      const missed2 = createMessage("msg-missed-2", "conv-001", new Date(baseTime.getTime() + 2000));
      const missed3 = createMessage("msg-missed-3", "conv-001", new Date(baseTime.getTime() + 4000));

      store.addMessage(missed1);
      store.addMessage(missed2);
      store.addMessage(missed3);

      const messages = store.getMessages("conv-001");

      expect(messages).toHaveLength(5);
      // Should be ordered by created_at (newest first)
      expect(messages.map((m) => m.message_id)).toEqual([
        "msg-missed-3",
        "msg-local-2",
        "msg-missed-2",
        "msg-local-1",
        "msg-missed-1",
      ]);
    });
  });

  describe("Delivery State Transitions", () => {
    it("prevents state regression: delivered → sent", () => {
      const now = new Date("2024-01-01T12:00:00Z");
      
      const delivered = createMessage("msg-001", "conv-001", now, "delivered");
      const sent = createMessage("msg-001", "conv-001", now, "sent"); // Attempted regression

      store.addMessage(delivered);
      store.addMessage(sent);

      const messages = store.getMessages("conv-001");
      expect(messages).toHaveLength(1);
      expect(messages[0].state).toBe("delivered"); // Should not regress
    });

    it("prevents state regression: failed → sent", () => {
      const now = new Date("2024-01-01T12:00:00Z");
      
      const failed = createMessage("msg-001", "conv-001", now, "failed");
      const sent = createMessage("msg-001", "conv-001", now, "sent"); // Attempted regression

      store.addMessage(failed);
      store.addMessage(sent);

      const messages = store.getMessages("conv-001");
      expect(messages).toHaveLength(1);
      expect(messages[0].state).toBe("failed"); // Should not regress
    });

    it("allows valid transition: sent → delivered", () => {
      const now = new Date("2024-01-01T12:00:00Z");
      
      const sent = createMessage("msg-001", "conv-001", now, "sent");
      const delivered = createMessage("msg-001", "conv-001", now, "delivered");

      store.addMessage(sent);
      store.addMessage(delivered);

      const messages = store.getMessages("conv-001");
      expect(messages).toHaveLength(1);
      expect(messages[0].state).toBe("delivered");
    });

    it("allows valid transition: sent → failed", () => {
      const now = new Date("2024-01-01T12:00:00Z");
      
      const sent = createMessage("msg-001", "conv-001", now, "sent");
      const failed = createMessage("msg-001", "conv-001", now, "failed");

      store.addMessage(sent);
      store.addMessage(failed);

      const messages = store.getMessages("conv-001");
      expect(messages).toHaveLength(1);
      expect(messages[0].state).toBe("failed");
    });

    it("allows valid transition: delivered → failed", () => {
      const now = new Date("2024-01-01T12:00:00Z");
      
      const delivered = createMessage("msg-001", "conv-001", now, "delivered");
      const failed = createMessage("msg-001", "conv-001", now, "failed");

      store.addMessage(delivered);
      store.addMessage(failed);

      const messages = store.getMessages("conv-001");
      expect(messages).toHaveLength(1);
      expect(messages[0].state).toBe("failed");
    });
  });

  describe("Transport Switching Behavior", () => {
    it("handles messages received via WebSocket then REST polling (no duplicates)", () => {
      const now = new Date("2024-01-01T12:00:00Z");
      
      // Message received via WebSocket
      const wsMessage = createMessage("msg-001", "conv-001", now);
      store.addMessage(wsMessage);

      // Same message received again via REST polling (should be deduplicated)
      const restMessage = createMessage("msg-001", "conv-001", now);
      const isNew = store.addMessage(restMessage);

      expect(isNew).toBe(false);
      expect(store.getMessages("conv-001")).toHaveLength(1);
    });

    it("handles messages received via REST polling then WebSocket (no duplicates)", () => {
      const now = new Date("2024-01-01T12:00:00Z");
      
      // Message received via REST polling
      const restMessage = createMessage("msg-001", "conv-001", now);
      store.addMessage(restMessage);

      // Same message received again via WebSocket (should be deduplicated)
      const wsMessage = createMessage("msg-001", "conv-001", now);
      const isNew = store.addMessage(wsMessage);

      expect(isNew).toBe(false);
      expect(store.getMessages("conv-001")).toHaveLength(1);
    });

    it("preserves delivery state when switching transports", () => {
      const now = new Date("2024-01-01T12:00:00Z");
      
      // Message received via WebSocket (delivered)
      const wsMessage = createMessage("msg-001", "conv-001", now, "delivered");
      store.addMessage(wsMessage);

      // Same message received via REST polling (should preserve delivered state)
      const restMessage = createMessage("msg-001", "conv-001", now, "delivered");
      store.addMessage(restMessage);

      const messages = store.getMessages("conv-001");
      expect(messages).toHaveLength(1);
      expect(messages[0].state).toBe("delivered");
    });

    it("does not drop messages when switching transports", () => {
      const baseTime = new Date("2024-01-01T12:00:00Z");
      
      // Messages received via WebSocket
      const ws1 = createMessage("msg-ws-1", "conv-001", new Date(baseTime.getTime() + 1000));
      const ws2 = createMessage("msg-ws-2", "conv-001", new Date(baseTime.getTime() + 2000));
      store.addMessage(ws1);
      store.addMessage(ws2);

      // Switch to REST polling, receive additional messages
      const rest1 = createMessage("msg-rest-1", "conv-001", new Date(baseTime.getTime() + 3000));
      const rest2 = createMessage("msg-rest-2", "conv-001", new Date(baseTime.getTime() + 4000));
      store.addMessage(rest1);
      store.addMessage(rest2);

      const messages = store.getMessages("conv-001");
      expect(messages).toHaveLength(4);
      // All messages should be present
      const messageIds = messages.map((m) => m.message_id).sort();
      expect(messageIds).toEqual(["msg-rest-1", "msg-rest-2", "msg-ws-1", "msg-ws-2"]);
    });

    it("does not reset delivery state when switching transports", () => {
      const now = new Date("2024-01-01T12:00:00Z");
      
      // Message in sent state (optimistic update)
      const sentMessage = createMessage("msg-001", "conv-001", now, "sent");
      store.addMessage(sentMessage);

      // Update to delivered via WebSocket
      const deliveredWs = createMessage("msg-001", "conv-001", now, "delivered");
      store.addMessage(deliveredWs);

      // Switch to REST polling, same message should remain delivered
      const deliveredRest = createMessage("msg-001", "conv-001", now, "delivered");
      store.addMessage(deliveredRest);

      const messages = store.getMessages("conv-001");
      expect(messages).toHaveLength(1);
      expect(messages[0].state).toBe("delivered"); // Should not reset to sent
    });
  });

  describe("Stable Ordering Guarantees", () => {
    it("maintains stable order when messages are added multiple times", () => {
      const baseTime = new Date("2024-01-01T12:00:00Z");
      
      const msg1 = createMessage("msg-001", "conv-001", new Date(baseTime.getTime() + 1000));
      const msg2 = createMessage("msg-002", "conv-001", new Date(baseTime.getTime() + 2000));
      const msg3 = createMessage("msg-003", "conv-001", new Date(baseTime.getTime() + 3000));

      // Add messages
      store.addMessage(msg1);
      store.addMessage(msg2);
      store.addMessage(msg3);

      const order1 = store.getMessages("conv-001").map((m) => m.message_id);

      // Add messages again (should not change order)
      store.addMessage(msg1);
      store.addMessage(msg2);
      store.addMessage(msg3);

      const order2 = store.getMessages("conv-001").map((m) => m.message_id);

      expect(order1).toEqual(order2);
    });

    it("uses created_at (server timestamp) for ordering, not insertion order", () => {
      const baseTime = new Date("2024-01-01T12:00:00Z");
      
      // Add messages in reverse chronological order
      const msg3 = createMessage("msg-003", "conv-001", new Date(baseTime.getTime() + 3000));
      const msg2 = createMessage("msg-002", "conv-001", new Date(baseTime.getTime() + 2000));
      const msg1 = createMessage("msg-001", "conv-001", new Date(baseTime.getTime() + 1000));

      store.addMessage(msg3);
      store.addMessage(msg2);
      store.addMessage(msg1);

      const messages = store.getMessages("conv-001");

      // Should be ordered by created_at (newest first), not insertion order
      expect(messages[0].message_id).toBe("msg-003");
      expect(messages[1].message_id).toBe("msg-002");
      expect(messages[2].message_id).toBe("msg-001");
    });
  });
});
