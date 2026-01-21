/**
 * Unit tests for StatusIndicator component.
 * 
 * References:
 * - UX Behavior (#12), Section 3.1 and 3.5
 * - Copy Rules (#13), Section 4
 * 
 * Tests validate:
 * - Correct rendering by state
 * - Neutral mode visual enforcement
 */

import React from "react";
import { render, screen } from "@testing-library/react";
import { StatusIndicator } from "../components/StatusIndicator";

describe("StatusIndicator", () => {
  it("renders active messaging status correctly", () => {
    render(
      <StatusIndicator
        status="Active Messaging"
        isReadOnly={false}
      />
    );

    expect(screen.getByText("Active Messaging")).toBeInTheDocument();
    expect(screen.queryByText("(Read-only)")).not.toBeInTheDocument();
  });

  it("renders messaging disabled status correctly", () => {
    render(
      <StatusIndicator
        status="Messaging Disabled"
        isReadOnly={true}
      />
    );

    expect(screen.getByText("Messaging Disabled")).toBeInTheDocument();
    expect(screen.getByText("(Read-only)")).toBeInTheDocument();
  });

  it("applies correct styling for active state", () => {
    const { container } = render(
      <StatusIndicator
        status="Active Messaging"
        isReadOnly={false}
      />
    );

    const statusElement = container.querySelector(".text-gray-900");
    expect(statusElement).toBeInTheDocument();
  });

  it("applies correct styling for read-only state", () => {
    const { container } = render(
      <StatusIndicator
        status="Messaging Disabled"
        isReadOnly={true}
      />
    );

    const statusElement = container.querySelector(".text-gray-600");
    expect(statusElement).toBeInTheDocument();
  });
});
