/**
 * Unit tests for SendButton component.
 * 
 * References:
 * - UX Behavior (#12), Section 3.3
 * - Copy Rules (#13), Section 3
 * - Resolved Clarifications (#38)
 * 
 * Tests validate:
 * - Disabled send conditions
 * - Sending state display
 * - Click handling
 */

import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { SendButton } from "../components/SendButton";

describe("SendButton", () => {
  it("renders send button correctly", () => {
    const handleClick = jest.fn();
    render(<SendButton disabled={false} onClick={handleClick} />);

    expect(screen.getByText("Send")).toBeInTheDocument();
  });

  it("disables button when disabled prop is true", () => {
    const handleClick = jest.fn();
    render(<SendButton disabled={true} onClick={handleClick} />);

    const button = screen.getByText("Send");
    expect(button).toBeDisabled();
    expect(button).toHaveClass("cursor-not-allowed");
  });

  it("disables button when sending", () => {
    const handleClick = jest.fn();
    render(<SendButton disabled={false} isSending={true} onClick={handleClick} />);

    const button = screen.getByText("Sending...");
    expect(button).toBeDisabled();
    expect(button).toHaveClass("cursor-not-allowed");
  });

  it("shows sending state text", () => {
    const handleClick = jest.fn();
    render(<SendButton disabled={false} isSending={true} onClick={handleClick} />);

    expect(screen.getByText("Sending...")).toBeInTheDocument();
  });

  it("calls onClick when clicked and not disabled", () => {
    const handleClick = jest.fn();
    render(<SendButton disabled={false} onClick={handleClick} />);

    const button = screen.getByText("Send");
    fireEvent.click(button);

    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it("does not call onClick when disabled", () => {
    const handleClick = jest.fn();
    render(<SendButton disabled={true} onClick={handleClick} />);

    const button = screen.getByText("Send");
    fireEvent.click(button);

    expect(handleClick).not.toHaveBeenCalled();
  });

  it("does not call onClick when sending", () => {
    const handleClick = jest.fn();
    render(<SendButton disabled={false} isSending={true} onClick={handleClick} />);

    const button = screen.getByText("Sending...");
    fireEvent.click(button);

    expect(handleClick).not.toHaveBeenCalled();
  });
});
