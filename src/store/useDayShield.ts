import { create } from "zustand";

import type {
  Action,
  AgentName,
  AgentState,
  CalendarEvent,
  ConnectionStatus,
  Disruption,
  LogEntry,
  Mode,
  StreamEvent,
} from "../types";

export type DayShieldState = {
  mode: Mode;
  connection: ConnectionStatus;
  connectionMessage: string | null;
  events: CalendarEvent[];
  disruption: Disruption | null;
  agents: Record<AgentName, AgentState>;
  actions: Action[];
  logs: LogEntry[];
  pendingActions: Record<string, "approve" | "reject">;
};

type DayShieldStore = DayShieldState & {
  applyEvent: (event: StreamEvent) => void;
  setMode: (mode: Mode) => void;
  setConnection: (connection: ConnectionStatus, message?: string | null) => void;
  setPendingAction: (id: string, kind: "approve" | "reject") => void;
};

const agentNames: AgentName[] = ["commute", "schedule", "priority", "recovery"];

function makeIdleAgents(): Record<AgentName, AgentState> {
  return Object.fromEntries(
    agentNames.map((name) => [name, { name, status: "idle" }]),
  ) as Record<AgentName, AgentState>;
}

const initialMode: Mode =
  import.meta.env.VITE_USE_MOCK === "false" ? "live" : "simulated";

export function createInitialState(mode: Mode = initialMode): DayShieldState {
  return {
    mode,
    connection: "connecting",
    connectionMessage: null,
    events: [],
    disruption: null,
    agents: makeIdleAgents(),
    actions: [],
    logs: [],
    pendingActions: {},
  };
}

function updateAction(
  actions: Action[],
  actionId: string,
  update: Partial<Action>,
): Action[] {
  return actions.map((action) =>
    action.id === actionId ? { ...action, ...update } : action,
  );
}

export function reduceStreamEvent(
  state: DayShieldState,
  event: StreamEvent,
): DayShieldState {
  switch (event.type) {
    case "events_loaded":
      return { ...state, events: event.events };
    case "disruption_detected": {
      const firstEventId = state.events[0]?.id;
      return {
        ...state,
        disruption: event.disruption,
        events: state.events.map((dayEvent) =>
          dayEvent.id === firstEventId
            ? {
                ...dayEvent,
                status: "at_risk",
                minutesLate: event.disruption.delayMin,
              }
            : dayEvent,
        ),
      };
    }
    case "agent_started":
      return {
        ...state,
        agents: {
          ...state.agents,
          [event.name]: { ...state.agents[event.name], status: "running" },
        },
      };
    case "agent_output":
      return {
        ...state,
        agents: {
          ...state.agents,
          [event.name]: {
            name: event.name,
            status: "done",
            summary: event.summary,
            output: event.output,
          },
        },
      };
    case "plan_ready":
      return { ...state, actions: event.actions };
    case "action_approved":
      return {
        ...state,
        actions: updateAction(state.actions, event.actionId, { status: "approved" }),
      };
    case "action_rejected": {
      const pendingActions = { ...state.pendingActions };
      delete pendingActions[event.actionId];
      return {
        ...state,
        actions: updateAction(state.actions, event.actionId, {
          status: "rejected",
          error: undefined,
        }),
        pendingActions,
      };
    }
    case "action_executed": {
      const pendingActions = { ...state.pendingActions };
      delete pendingActions[event.actionId];
      return {
        ...state,
        actions: updateAction(state.actions, event.actionId, {
          status: "executed",
          error: undefined,
        }),
        events: event.eventUpdates
          ? state.events.map((dayEvent) => {
              const update = event.eventUpdates?.find((item) => item.id === dayEvent.id);
              return update ? { ...dayEvent, ...update } : dayEvent;
            })
          : state.events,
        pendingActions,
      };
    }
    case "action_failed": {
      const pendingActions = { ...state.pendingActions };
      delete pendingActions[event.actionId];
      return {
        ...state,
        actions: updateAction(state.actions, event.actionId, {
          status: "failed",
          error: event.error,
        }),
        pendingActions,
      };
    }
    case "log_entry":
      return { ...state, logs: [...state.logs, event.entry] };
    case "reset":
      return {
        ...state,
        events: [],
        disruption: null,
        agents: makeIdleAgents(),
        actions: [],
        logs: [],
        pendingActions: {},
      };
  }
}

export const useDayShield = create<DayShieldStore>((set) => ({
  ...createInitialState(),
  applyEvent: (event) => set((state) => reduceStreamEvent(state, event)),
  setMode: (mode) => set({ mode }),
  setConnection: (connection, message = null) =>
    set({ connection, connectionMessage: message }),
  setPendingAction: (id, kind) =>
    set((state) => ({ pendingActions: { ...state.pendingActions, [id]: kind } })),
}));