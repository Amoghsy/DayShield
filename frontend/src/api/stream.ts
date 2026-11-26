import type { ConnectionStatus, StreamEvent } from "../types";

const apiBase = import.meta.env.VITE_API_BASE_URL ?? "";

const streamEventNames: StreamEvent["type"][] = [
  "disruption_detected",
  "agent_started",
  "agent_output",
  "plan_ready",
  "action_approved",
  "action_rejected",
  "action_executed",
  "action_failed",
  "log_entry",
  "events_loaded",
  "reset",
];

type StreamController = { close: () => void };
type StatusHandler = (status: ConnectionStatus, message?: string | null) => void;

export function connectLiveStream(
  onEvent: (event: StreamEvent) => void,
  onStatus: StatusHandler,
): StreamController {
  let source: EventSource | null = null;
  let retryTimer: ReturnType<typeof setTimeout> | null = null;
  let retryCount = 0;
  let closed = false;

  const connect = () => {
    if (closed) return;
    onStatus(retryCount === 0 ? "connecting" : "reconnecting");
    source = new EventSource(`${apiBase}/api/stream`);
    source.onopen = () => {
      retryCount = 0;
      onStatus("connected");
    };
    source.onerror = () => {
      source?.close();
      source = null;
      retryCount += 1;
      onStatus("reconnecting", "The live stream dropped. Reconnecting…");
      const wait = Math.min(800 * 2 ** Math.min(retryCount - 1, 5), 20_000);
      retryTimer = setTimeout(connect, wait);
    };
    for (const eventName of streamEventNames) {
      source.addEventListener(eventName, (message) => {
        try {
          const payload: unknown = JSON.parse((message as MessageEvent<string>).data);
          if (payload && typeof payload === "object" && "type" in payload) {
            onEvent(payload as StreamEvent);
          } else if (payload && typeof payload === "object") {
            onEvent({ type: eventName, ...payload } as StreamEvent);
          }
        } catch {
          onStatus("error", `The live stream sent an unreadable ${eventName} event.`);
        }
      });
    }
  };

  connect();
  return {
    close: () => {
      closed = true;
      source?.close();
      if (retryTimer) clearTimeout(retryTimer);
    },
  };
}