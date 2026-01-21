/**
 * Unit tests for MessageRow component.
 * 
 * References:
 * - UX Behavior (#12), Section 3.3 and 3.4
 * - Copy Rules (#13), Section 3
 * 
 * Tests validate:
 * - Correct rendering by state (delivered, failed, expired)
 * - Neutral mode visual enforcement
 * - Expired message filtering (should not render)
 */

import { describe, it, expect } from 'vitest'
import React from "react";
import { render, screen } from "@testing-library/react";
import { MessageRow } from "../components/MessageRow";
import { MessageViewModel } from "../types";

describe("MessageRow", () => {
  const baseMessage: MessageViewModel = {
    message_id: "msg-001",
    sender_id: "device-001",
    conversation_id: "conv-001",
    state: "delivered",
    created_at: new Date().toISOString(),
    expires_at: new Date(Date.now() + 604800000).toISOString(),
    is_expired: false,
    is_failed: false,
    is_read_only: false,
    display_state: "delivered",
  };

  it("renders delivered message correctly", () => {
    render(
      <MessageRow
        message={baseMessage}
        isReadOnly={false}
      />
    );

    expect(screen.getByText("device-001")).toBeInTheDocument();
    expect(screen.queryByText("(Failed)")).not.toBeInTheDocument();
    expect(screen.queryByText("Read-only")).not.toBeInTheDocument();
  });

  it("renders failed message with distinction", () => {
    const failedMessage: MessageViewModel = {
      ...baseMessage,
      state: "failed",
      is_failed: true,
      display_state: "failed",
    };

    render(
      <MessageRow
        message={failedMessage}
        isReadOnly={false}
      />
    );

    expect(screen.getByText("device-001")).toBeInTheDocument();
    expect(screen.getByText("(Failed)")).toBeInTheDocument();
  });

  it("does not render expired messages", () => {
    const expiredMessage: MessageViewModel = {
      ...baseMessage,
      state: "expired",
      is_expired: true,
      display_state: "expired",
    };

    const { container } = render(
      <MessageRow
        message={expiredMessage}
        isReadOnly={false}
      />
    );

    // Expired messages should not render per UX Behavior (#12), Section 3.4
    expect(container.firstChild).toBeNull();
  });

  it("shows read-only indicator when in neutral enterprise mode", () => {
    render(
      <MessageRow
        message={baseMessage}
        isReadOnly={true}
      />
    );

    expect(screen.getByText("Read-only")).toBeInTheDocument();
  });

  it("applies correct styling for failed messages", () => {
    const failedMessage: MessageViewModel = {
      ...baseMessage,
      state: "failed",
      is_failed: true,
      display_state: "failed",
    };

    const { container } = render(
      <MessageRow
        message={failedMessage}
        isReadOnly={false}
      />
    );

    const messageElement = container.querySelector(".border-l-4.border-gray-400");
    expect(messageElement).toBeInTheDocument();
  });
});
