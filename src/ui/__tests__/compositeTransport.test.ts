/**
 * Tests for composite transport with WebSocket and REST polling fallback.
 * 
 * References:
 * - Message Delivery & Reliability docs
 * - Resolved Clarifications (#51)
 * 
 * Tests validate:
 * - WebSocket as primary transport
 * - REST polling fallback after 15s disconnect
 * - REST polling stops when WebSocket reconnects
 * - Message forwarding from both transports
 * - Transport switching behavior
 * - Timer reset prevention
 */

import { CompositeTransport } from "../services/compositeTransport";
import { MessageViewModel } from "../types";

describe("CompositeTransport", () => {
  const wsUrl = "ws://localhost:8000/ws/messages";
  const apiUrl = "http://localhost:8000";
  const deviceId = "test-device-001";

  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it("should create composite transport with both WebSocket and polling", () => {
    const transport = new CompositeTransport(wsUrl, apiUrl);
    expect(transport).toBeDefined();
    expect(transport.getStatus()).toBe("disconnected");
  });

  it("should forward messages from WebSocket transport", async () => {
    const transport = new CompositeTransport(wsUrl, apiUrl);
    const onMessage = jest.fn();
    const onStatusChange = jest.fn();

    await transport.connect(deviceId, onMessage, onStatusChange);

    // Simulate message from WebSocket (accessing internal transport)
    const wsTransport = (transport as any).wsTransport;
    const mockMessage: MessageViewModel = {
      message_id: "msg-001",
      sender_id: "sender-001",
      conversation_id: "conv-001",
      state: "delivered",
      created_at: new Date().toISOString(),
      expires_at: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
      is_expired: false,
      is_failed: false,
      is_read_only: false,
      display_state: "delivered",
    };

    // Trigger message handler if it exists
    if ((wsTransport as any).onMessageHandler) {
      (wsTransport as any).onMessageHandler(mockMessage);
      expect(onMessage).toHaveBeenCalledWith(mockMessage);
    }

    await transport.disconnect();
  });

  it("should activate REST polling fallback after 15s WebSocket disconnect", async () => {
    const transport = new CompositeTransport(wsUrl, apiUrl);
    const onMessage = jest.fn();
    const onStatusChange = jest.fn();

    await transport.connect(deviceId, onMessage, onStatusChange);

    // Simulate WebSocket disconnect
    const wsTransport = (transport as any).wsTransport;
    // Mock WebSocket as disconnected
    jest.spyOn(wsTransport, "isConnected").mockReturnValue(false);

    // Trigger disconnect status
    const statusHandler = (wsTransport as any).onStatusChangeHandler;
    if (statusHandler) {
      statusHandler("disconnected");
    }

    // Fast-forward 15 seconds
    jest.advanceTimersByTime(15000);

    // Wait for async operations
    await Promise.resolve();

    // Verify polling transport is active
    const pollingTransport = (transport as any).pollingTransport;
    expect((transport as any).activeTransport).toBe("polling");
    expect(pollingTransport).toBeDefined();

    await transport.disconnect();
  });

  it("should stop REST polling when WebSocket reconnects", async () => {
    const transport = new CompositeTransport(wsUrl, apiUrl);
    const onMessage = jest.fn();
    const onStatusChange = jest.fn();

    await transport.connect(deviceId, onMessage, onStatusChange);

    const wsTransport = (transport as any).wsTransport;
    const pollingTransport = (transport as any).pollingTransport;

    // Mock WebSocket as disconnected initially
    jest.spyOn(wsTransport, "isConnected").mockReturnValue(false);

    // Trigger disconnect to start fallback timer
    const statusHandler = (wsTransport as any).onStatusChangeHandler;
    if (statusHandler) {
      statusHandler("disconnected");
    }

    // Fast-forward 15 seconds to activate fallback
    jest.advanceTimersByTime(15000);
    await Promise.resolve();

    // Verify polling is active
    expect((transport as any).activeTransport).toBe("polling");

    // Mock WebSocket reconnection
    jest.spyOn(wsTransport, "isConnected").mockReturnValue(true);
    jest.spyOn(pollingTransport, "disconnect").mockResolvedValue(undefined);

    // Trigger WebSocket connected status
    if (statusHandler) {
      statusHandler("connected");
    }

    await Promise.resolve();

    // Verify polling was stopped and WebSocket is active
    expect(pollingTransport.disconnect).toHaveBeenCalled();
    expect((transport as any).activeTransport).toBe("websocket");

    await transport.disconnect();
  });

  it("should not reset fallback timer on reconnection attempts", async () => {
    const transport = new CompositeTransport(wsUrl, apiUrl);
    const onMessage = jest.fn();
    const onStatusChange = jest.fn();

    await transport.connect(deviceId, onMessage, onStatusChange);

    const wsTransport = (transport as any).wsTransport;
    jest.spyOn(wsTransport, "isConnected").mockReturnValue(false);

    // Trigger disconnect to start fallback timer
    const statusHandler = (wsTransport as any).onStatusChangeHandler;
    if (statusHandler) {
      statusHandler("disconnected");
    }

    // Get initial timer
    const initialTimer = (transport as any).fallbackTimer;
    expect(initialTimer).toBeDefined();

    // Trigger reconnecting status (should not reset timer)
    if (statusHandler) {
      statusHandler("reconnecting");
    }

    // Verify timer was not reset
    expect((transport as any).fallbackTimer).toBe(initialTimer);

    await transport.disconnect();
  });

  it("should not schedule fallback timer if WebSocket connects immediately", async () => {
    const transport = new CompositeTransport(wsUrl, apiUrl);
    const onMessage = jest.fn();
    const onStatusChange = jest.fn();

    const wsTransport = (transport as any).wsTransport;
    // Mock WebSocket as connected immediately
    jest.spyOn(wsTransport, "isConnected").mockReturnValue(true);

    await transport.connect(deviceId, onMessage, onStatusChange);

    // Verify no fallback timer was scheduled
    expect((transport as any).fallbackTimer).toBeNull();

    await transport.disconnect();
  });

  it("should handle messages from REST polling transport", async () => {
    const transport = new CompositeTransport(wsUrl, apiUrl);
    const onMessage = jest.fn();
    const onStatusChange = jest.fn();

    await transport.connect(deviceId, onMessage, onStatusChange);

    // Activate polling fallback
    const wsTransport = (transport as any).wsTransport;
    jest.spyOn(wsTransport, "isConnected").mockReturnValue(false);

    const statusHandler = (wsTransport as any).onStatusChangeHandler;
    if (statusHandler) {
      statusHandler("disconnected");
    }

    jest.advanceTimersByTime(15000);
    await Promise.resolve();

    // Simulate message from polling
    const pollingTransport = (transport as any).pollingTransport;
    const mockMessage: MessageViewModel = {
      message_id: "msg-002",
      sender_id: "sender-002",
      conversation_id: "conv-002",
      state: "delivered",
      created_at: new Date().toISOString(),
      expires_at: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
      is_expired: false,
      is_failed: false,
      is_read_only: false,
      display_state: "delivered",
    };

    // Trigger message handler if it exists
    if ((pollingTransport as any).onMessageHandler) {
      (pollingTransport as any).onMessageHandler(mockMessage);
      expect(onMessage).toHaveBeenCalledWith(mockMessage);
    }

    await transport.disconnect();
  });

  it("should disconnect both transports", async () => {
    const transport = new CompositeTransport(wsUrl, apiUrl);
    const onMessage = jest.fn();
    const onStatusChange = jest.fn();

    await transport.connect(deviceId, onMessage, onStatusChange);
    await transport.disconnect();

    expect(transport.getStatus()).toBe("disconnected");
    expect(transport.isConnected()).toBe(false);
  });
});
