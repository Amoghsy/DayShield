export type Source = "live" | "simulated";
export type Mode = Source;
export type DisruptionType = "traffic" | "weather" | "closure";
export type AgentName = "commute" | "schedule" | "priority" | "recovery";
export type ActionKind =
  | "reroute"
  | "draft_email"
  | "move_event"
  | "join_online"
  | "escalate"
  | "no_op";
export type ActionStatus =
  | "proposed"
  | "approved"
  | "rejected"
  | "executed"
  | "failed";

export type CalendarEvent = {
  id: string;
  title: string;
  start: string;
  end: string;
  location?: string;
  isOnline: boolean;
  status: "normal" | "at_risk" | "protected" | "moved";
  minutesLate?: number;
  proposedStart?: string;
  proposedEnd?: string;
};

export type Disruption = {
  id: string;
  type: DisruptionType;
  delayMin: number;
  etaBefore: string;
  etaAfter: string;
  source: Source;
  detectedAt: string;
};

export type AgentState = {
  name: AgentName;
  status: "idle" | "running" | "done" | "error";
  summary?: string;
  output?: unknown;
};

export type Action = {
  id: string;
  kind: ActionKind;
  title: string;
  rationale: string;
  risk: "low" | "medium" | "high";
  status: ActionStatus;
  source: Source;
  params: Record<string, unknown>;
  error?: string;
};

export type LogEntry = {
  id: string;
  ts: string;
  actor: string;
  tool: string;
  inputSummary: string;
  outputSummary: string;
  source: Source;
  status: "ok" | "error";
};

export type EventUpdate = Partial<CalendarEvent> & { id: string };

export type StreamEvent =
  | { type: "disruption_detected"; disruption: Disruption }
  | { type: "agent_started"; name: AgentName }
  | { type: "agent_output"; name: AgentName; summary: string; output: unknown }
  | { type: "plan_ready"; actions: Action[] }
  | { type: "action_approved"; actionId: string }
  | { type: "action_rejected"; actionId: string; reason?: string }
  | { type: "action_executed"; actionId: string; eventUpdates?: EventUpdate[] }
  | { type: "action_failed"; actionId: string; error: string }
  | { type: "log_entry"; entry: LogEntry }
  | { type: "events_loaded"; events: CalendarEvent[] }
  | { type: "reset" };

export type ConnectionStatus =
  | "connecting"
  | "connected"
  | "reconnecting"
  | "error";