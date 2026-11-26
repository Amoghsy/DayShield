import { describe, expect, it } from "vitest";

import { reduceStreamEvent, createInitialState } from "../store/useDayShield";
import type { Action } from "../types";

const moveAction: Action = {
  id: "move-4pm",
  kind: "move_event",
  title: "Move the follow-up",
  rationale: "An open slot is available.",
  risk: "low",
  status: "proposed",
  source: "simulated",
  params: {},
};

describe("DayShield stream-driven approvals", () => {
  it("keeps an approval pending until the execution event arrives", () => {
    const planned = reduceStreamEvent(createInitialState("simulated"), {
      type: "plan_ready",
      actions: [moveAction],
    });
    const pending = { ...planned, pendingActions: { [moveAction.id]: "approve" as const } };
    const acknowledged = reduceStreamEvent(pending, {
      type: "action_approved",
      actionId: moveAction.id,
    });

    expect(acknowledged.actions[0]?.status).toBe("approved");
    expect(acknowledged.pendingActions[moveAction.id]).toBe("approve");

    const executed = reduceStreamEvent(acknowledged, {
      type: "action_executed",
      actionId: moveAction.id,
    });
    expect(executed.actions[0]?.status).toBe("executed");
    expect(executed.pendingActions[moveAction.id]).toBeUndefined();
  });

  it("shows a failed status and releases the button so an action can be retried", () => {
    const planned = reduceStreamEvent(createInitialState("simulated"), {
      type: "plan_ready",
      actions: [moveAction],
    });
    const pending = { ...planned, pendingActions: { [moveAction.id]: "approve" as const } };
    const failed = reduceStreamEvent(pending, {
      type: "action_failed",
      actionId: moveAction.id,
      error: "Calendar is unavailable.",
    });

    expect(failed.actions[0]?.status).toBe("failed");
    expect(failed.actions[0]?.error).toBe("Calendar is unavailable.");
    expect(failed.pendingActions[moveAction.id]).toBeUndefined();
  });

  it("moves the 4:00 PM event only after an execution event confirms 5:00 PM", () => {
    const withEvents = reduceStreamEvent(createInitialState("simulated"), {
      type: "events_loaded",
      events: [
        {
          id: "follow-up",
          title: "Vendor follow-up",
          start: "4:00 PM",
          end: "4:30 PM",
          location: "Focus time",
          isOnline: false,
          status: "normal",
        },
      ],
    });
    const beforeConfirmation = reduceStreamEvent(withEvents, {
      type: "action_approved",
      actionId: moveAction.id,
    });
    expect(beforeConfirmation.events[0]?.start).toBe("4:00 PM");

    const executed = reduceStreamEvent(beforeConfirmation, {
      type: "action_executed",
      actionId: moveAction.id,
      eventUpdates: [{ id: "follow-up", status: "moved", proposedStart: "5:00 PM", proposedEnd: "5:30 PM" }],
    });
    expect(executed.events[0]?.status).toBe("moved");
    expect(executed.events[0]?.start).toBe("4:00 PM");
    expect(executed.events[0]?.proposedStart).toBe("5:00 PM");
  });
});