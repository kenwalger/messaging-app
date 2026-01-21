/**
 * Mock data fixtures for Storybook-style testing.
 * 
 * References:
 * - UI Domain Adapter Layer (latest)
 * - UX Behavior (#12)
 * - Copy Rules (#13)
 * 
 * Provides mock UI domain models for testing and development.
 * No network calls, no side effects.
 */

import {
  ConversationViewModel,
  DeviceStateViewModel,
  MessageViewModel,
} from "../types";

/**
 * Mock device state for active device.
 */
export const mockActiveDeviceState: DeviceStateViewModel = {
  device_id: "device-001",
  is_read_only: false,
  can_send: true,
  can_create_conversations: true,
  can_join_conversations: true,
  display_status: "Active Messaging",
};

/**
 * Mock device state for revoked device (read-only mode).
 */
export const mockRevokedDeviceState: DeviceStateViewModel = {
  device_id: "device-001",
  is_read_only: true,
  can_send: false,
  can_create_conversations: false,
  can_join_conversations: false,
  display_status: "Messaging Disabled",
};

/**
 * Mock conversations for testing.
 */
export const mockConversations: ConversationViewModel[] = [
  {
    conversation_id: "conv-001",
    state: "active",
    participant_count: 3,
    can_send: true,
    is_read_only: false,
    send_disabled: false,
    last_message_at: new Date().toISOString(),
    created_at: new Date(Date.now() - 86400000).toISOString(), // 1 day ago
    display_name: "Conversation (3 participants)",
  },
  {
    conversation_id: "conv-002",
    state: "active",
    participant_count: 2,
    can_send: true,
    is_read_only: false,
    send_disabled: false,
    last_message_at: new Date(Date.now() - 3600000).toISOString(), // 1 hour ago
    created_at: new Date(Date.now() - 172800000).toISOString(), // 2 days ago
    display_name: "Conversation (2 participants)",
  },
  {
    conversation_id: "conv-003",
    state: "active",
    participant_count: 1,
    can_send: false,
    is_read_only: true,
    send_disabled: true,
    last_message_at: new Date(Date.now() - 7200000).toISOString(), // 2 hours ago
    created_at: new Date(Date.now() - 259200000).toISOString(), // 3 days ago
    display_name: "Conversation",
  },
];

/**
 * Mock messages for testing.
 * Pre-sorted in reverse chronological order (newest first).
 */
export const mockMessages: Record<string, MessageViewModel[]> = {
  "conv-001": [
    {
      message_id: "msg-001",
      sender_id: "device-002",
      conversation_id: "conv-001",
      state: "delivered",
      created_at: new Date().toISOString(),
      expires_at: new Date(Date.now() + 604800000).toISOString(), // 7 days from now
      is_expired: false,
      is_failed: false,
      is_read_only: false,
      display_state: "delivered",
    },
    {
      message_id: "msg-002",
      sender_id: "device-001",
      conversation_id: "conv-001",
      state: "delivered",
      created_at: new Date(Date.now() - 3600000).toISOString(), // 1 hour ago
      expires_at: new Date(Date.now() + 604800000).toISOString(),
      is_expired: false,
      is_failed: false,
      is_read_only: false,
      display_state: "delivered",
    },
    {
      message_id: "msg-003",
      sender_id: "device-003",
      conversation_id: "conv-001",
      state: "failed",
      created_at: new Date(Date.now() - 7200000).toISOString(), // 2 hours ago
      expires_at: new Date(Date.now() + 604800000).toISOString(),
      is_expired: false,
      is_failed: true,
      is_read_only: false,
      display_state: "failed",
    },
  ],
  "conv-002": [
    {
      message_id: "msg-004",
      sender_id: "device-002",
      conversation_id: "conv-002",
      state: "delivered",
      created_at: new Date(Date.now() - 1800000).toISOString(), // 30 minutes ago
      expires_at: new Date(Date.now() + 604800000).toISOString(),
      is_expired: false,
      is_failed: false,
      is_read_only: false,
      display_state: "delivered",
    },
  ],
  "conv-003": [
    {
      message_id: "msg-005",
      sender_id: "device-001",
      conversation_id: "conv-003",
      state: "delivered",
      created_at: new Date(Date.now() - 10800000).toISOString(), // 3 hours ago
      expires_at: new Date(Date.now() + 604800000).toISOString(),
      is_expired: false,
      is_failed: false,
      is_read_only: true,
      display_state: "delivered",
    },
  ],
};

/**
 * Mock data with expired messages for testing expiration behavior.
 */
export const mockMessagesWithExpired: Record<string, MessageViewModel[]> = {
  "conv-001": [
    {
      message_id: "msg-001",
      sender_id: "device-002",
      conversation_id: "conv-001",
      state: "delivered",
      created_at: new Date().toISOString(),
      expires_at: new Date(Date.now() + 604800000).toISOString(),
      is_expired: false,
      is_failed: false,
      is_read_only: false,
      display_state: "delivered",
    },
    {
      message_id: "msg-expired",
      sender_id: "device-001",
      conversation_id: "conv-001",
      state: "expired",
      created_at: new Date(Date.now() - 86400000).toISOString(), // 1 day ago
      expires_at: new Date(Date.now() - 3600000).toISOString(), // Expired 1 hour ago
      is_expired: true,
      is_failed: false,
      is_read_only: false,
      display_state: "expired",
    },
  ],
};
