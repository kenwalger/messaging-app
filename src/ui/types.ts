/**
 * TypeScript types for UI domain models.
 * 
 * References:
 * - UI Domain Adapter Layer (latest)
 * - UX Behavior (#12)
 * - Copy Rules (#13)
 * - Resolved Specs & Clarifications
 * 
 * These types mirror the Python UI domain models for React consumption.
 */

/**
 * Client-visible message states per UX Behavior (#12), Section 4.
 */
export type ClientMessageState = 
  | "sent"      // Maps to PendingDelivery (internal)
  | "delivered" // Maps to Delivered (internal)
  | "failed"    // Maps to Failed (internal)
  | "expired";  // Maps to Expired (internal)

/**
 * Client-visible conversation states per UX Behavior (#12), Section 3.2.
 */
export type ClientConversationState = 
  | "active"  // Active conversation
  | "closed"; // Closed conversation

/**
 * Message view model per UI Domain Adapter Layer.
 * 
 * Stateless view model deterministically derived from ClientMessageDTO.
 * Provides derived UX flags for expiration, failure, and read-only states.
 */
export interface MessageViewModel {
  message_id: string;
  sender_id: string;
  conversation_id: string;
  state: ClientMessageState;
  created_at: string; // ISO datetime string
  expires_at: string; // ISO datetime string
  is_expired: boolean;
  is_failed: boolean;
  is_read_only: boolean;
  display_state: "expired" | "failed" | "queued" | "delivered" | "unknown";
  payload?: string; // Encrypted payload (hex-encoded) - optional for backward compatibility
}

/**
 * Conversation view model per UI Domain Adapter Layer.
 * 
 * Stateless view model deterministically derived from ClientConversationDTO.
 * Provides derived UX flags for sending, read-only mode, and closure.
 */
export interface ConversationViewModel {
  conversation_id: string;
  state: ClientConversationState;
  participant_count: number;
  can_send: boolean;
  is_read_only: boolean;
  send_disabled: boolean;
  last_message_at: string | null; // ISO datetime string or null
  created_at: string; // ISO datetime string
  display_name: string;
  last_message_preview?: string; // Optional preview of last message
}

/**
 * Device state view model per UI Domain Adapter Layer.
 * 
 * Provides derived UX flags for neutral enterprise mode (revoked devices).
 */
export interface DeviceStateViewModel {
  device_id: string;
  is_read_only: boolean;
  can_send: boolean;
  can_create_conversations: boolean;
  can_join_conversations: boolean;
  display_status: "Active Messaging" | "Messaging Disabled";
}
