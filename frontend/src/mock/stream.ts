import { createDayEvents, createDisruption, createPlan, type ScenarioName } from "./scenarios";
import type { Action, AgentName, LogEntry, StreamEvent } from "../types";

type EventHandler = (event: StreamEvent) => void;
type StatusHandler = (status: "connected" | "reconnecting") => void;

export type MockStreamController = {
  close: () => void;
  trigger: (scenario: ScenarioName) => void;
  reset: () => void;
  approveAction: (actionId: string) => void;
  rejectAction: (actionId: string) => void;
};

const allAgents: AgentName[] = ["commute", "schedule", "priority", "recovery"];

function makeLog(
  actor: string,
  tool: string,
  inputSummary: string,
  outputSummary: string,
  status: LogEntry["status"] = "ok",
): LogEntry {
  return {
    id: `${tool}-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
    ts: new Date().toLocaleTimeString([], { hour: "numeric", minute: "2-digit" }),
    actor,
    tool,
    inputSummary,
    outputSummary,
    source: "simulated",
    status,
  };
}

export function createMockEventSource(
  onEvent: EventHandler,
  onStatus: StatusHandler,
): MockStreamController {
  let closed = false;
  let timers: ReturnType<typeof setTimeout>[] = [];
  let currentScenario: ScenarioName = "commute";

  const emit = (event: StreamEvent) => {
    if (!closed) onEvent(event);
  };
  const schedule = (delay: number, callback: () => void) => {
    const timer = setTimeout(() => {
      timers = timers.filter((queued) => queued !== timer);
      if (!closed) callback();
    }, delay);
    timers.push(timer);
  };
  const clearTimers = () => {
    timers.forEach(clearTimeout);
    timers = [];
  };
  const log = (...args: Parameters<typeof makeLog>) =>
    emit({ type: "log_entry", entry: makeLog(...args) });

  const runAgents = (scenario: ScenarioName) => {
    const hasSafeRoute = scenario === "commute";
    const summaries: Record<AgentName, { summary: string; output: unknown; tool: string }> = {
      commute: {
        summary: hasSafeRoute
          ? "Riverside Drive clears the slowdown and recovers 17 minutes."
          : "No safe route clears the closure before the client sync.",
        output: {
          bestRoute: hasSafeRoute ? "Riverside Drive" : null,
          delayMinutes: hasSafeRoute ? 25 : 48,
          alternativesChecked: 3,
          safe: hasSafeRoute,
        },
        tool: "maps.find_route",
      },
      schedule: {
        summary: hasSafeRoute
          ? "A 5:00 PM opening can absorb the follow-up task."
          : "The 4:00 PM task has room to move; the morning has no buffer.",
        output: { openSlot: "5:00 PM", conflicts: hasSafeRoute ? 0 : 1 },
        tool: "calendar.find_open_slot",
      },
      priority: {
        summary: "The 1:00 PM review is protected; the client sync needs a heads-up.",
        output: { protectedEvents: ["event-review"], atRiskEvents: ["event-client-sync"] },
        tool: "calendar.rank_events",
      },
      recovery: {
        summary: hasSafeRoute
          ? "Four low-impact options are ready for your review."
          : "A safe recovery is not available. Your decision is needed.",
        output: {
          safePlanAvailable: hasSafeRoute,
          proposedActions: hasSafeRoute ? 4 : 1,
        },
        tool: "planner.build_recovery",
      },
    };

    schedule(220, () => {
      emit({ type: "agent_started", name: "commute" });
      emit({ type: "agent_started", name: "schedule" });
      schedule(1450, () => {
        const result = summaries.commute;
        emit({ type: "agent_output", name: "commute", summary: result.summary, output: result.output });
        log("Commute", result.tool, "Check alternate routes", result.summary);
      });
      schedule(2900, () => {
        const result = summaries.schedule;
        emit({ type: "agent_output", name: "schedule", summary: result.summary, output: result.output });
        log("Schedule", result.tool, "Find open calendar slots", result.summary);
        emit({ type: "agent_started", name: "priority" });
      });
      schedule(4350, () => {
        const result = summaries.priority;
        emit({ type: "agent_output", name: "priority", summary: result.summary, output: result.output });
        log("Priority", result.tool, "Rank today's calendar events", result.summary);
        emit({ type: "agent_started", name: "recovery" });
      });
      schedule(5800, () => {
        const result = summaries.recovery;
        emit({ type: "agent_output", name: "recovery", summary: result.summary, output: result.output });
        log("Recovery", result.tool, "Build options from agent findings", result.summary);
        emit({ type: "plan_ready", actions: createPlan(scenario) });
      });
    });
  };

  const beginScenario = (scenario: ScenarioName, initialDelay = 0) => {
    currentScenario = scenario;
    clearTimers();
    emit({ type: "reset" });
    emit({ type: "events_loaded", events: createDayEvents() });
    onStatus("connected");
    schedule(initialDelay, () => {
      emit({ type: "disruption_detected", disruption: createDisruption(scenario) });
      log(
        "Commute",
        "traffic.detect_disruption",
        scenario === "commute" ? "Morning commute" : "Riverside interchange",
        scenario === "commute" ? "Traffic slowdown · 25 min" : "Road closure · 48 min",
      );
      runAgents(scenario);
    });
  };

  const controller: MockStreamController = {
    close: () => {
      closed = true;
      clearTimers();
    },
    trigger: (scenario) => beginScenario(scenario, 250),
    reset: () => {
      clearTimers();
      emit({ type: "reset" });
      emit({ type: "events_loaded", events: createDayEvents() });
      onStatus("connected");
      currentScenario = "commute";
    },
    approveAction: (actionId) => {
      const action = createPlan(currentScenario).find((candidate) => candidate.id === actionId);
      schedule(180, () => {
        emit({ type: "action_approved", actionId });
        log("You", "actions.approve", actionId, "Approval recorded");
      });
      schedule(1080, () => {
        const eventUpdates =
          action?.kind === "move_event"
            ? [
                {
                  id: "event-follow-up",
                  status: "moved" as const,
                  proposedStart: "5:00 PM",
                  proposedEnd: "5:30 PM",
                },
              ]
            : action?.id === "action-protect"
              ? [{ id: "event-review", status: "protected" as const }]
              : undefined;
        emit({ type: "action_executed", actionId, ...(eventUpdates ? { eventUpdates } : {}) });
        log("Recovery", action?.kind ?? "actions.execute", actionId, "Action completed");
        if (action?.kind === "draft_email") {
          log("Recovery", "email.create_draft", "Northstar client sync", "Draft created · not sent");
        }
      });
    },
    rejectAction: (actionId) => {
      schedule(180, () => {
        emit({ type: "action_rejected", actionId, reason: "Rejected by user" });
        log("You", "actions.reject", actionId, "Proposal rejected");
      });
    },
  };

  onStatus("connected");
  beginScenario("commute", 2000);
  return controller;
}