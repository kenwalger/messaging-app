/**
 * SendButton component for message sending.
 * 
 * References:
 * - UX Behavior (#12), Section 3.3
 * - Copy Rules (#13), Section 3
 * - Resolved Clarifications (#38)
 * 
 * Sending disabled when:
 * - Neutral enterprise mode is active
 * - Device is revoked
 * - Conversation is closed
 */

import React from "react";

export interface SendButtonProps {
  /**
   * True if sending is disabled.
   * Per deterministic rules: neutral enterprise mode, revoked device, or closed conversation.
   */
  disabled: boolean;
  
  /**
   * True if message is currently being sent.
   */
  isSending?: boolean;
  
  /**
   * Click handler for send action.
   */
  onClick: () => void;
}

/**
 * SendButton component per UX Behavior (#12), Section 3.3.
 * 
 * Displays "Send" button per Copy Rules (#13), Section 3.
 * Disabled when neutral enterprise mode, revoked device, or conversation is closed.
 * 
 * No animations beyond basic transitions per constraints.
 */
export const SendButton: React.FC<SendButtonProps> = ({
  disabled,
  isSending = false,
  onClick,
}) => {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled || isSending}
      className={`
        px-4 py-2 text-sm font-medium rounded
        transition-colors duration-150
        ${
          disabled || isSending
            ? "bg-gray-200 text-gray-400 cursor-not-allowed"
            : "bg-gray-700 text-white hover:bg-gray-800 active:bg-gray-900"
        }
      `}
    >
      {isSending ? "Sending..." : "Send"}
    </button>
  );
};
