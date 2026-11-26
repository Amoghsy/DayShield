import type { Action, CalendarEvent, Disruption } from "../types";

export type ScenarioName = "commute" | "no-safe-fix";

export function createDayEvents(): CalendarEvent[] {
  return [
    {
      id: "event-client-sync",
      title: "Northstar client sync",
      start: "9:00 AM",
      end: "10:00 AM",
      location: "Northstar HQ · 18 min walk",
      isOnline: true,
      status: "normal",
    },
    {
      id: "event-gym",
      title: "Strength training",
      start: "10:30 AM",
      end: "11:30 AM",
      location: "Fieldhouse",
      isOnline: false,
      status: "normal",
    },
    {
      id: "event-review",
      title: "Quarterly service review",
      start: "1:00 PM",
      end: "2:00 PM",
      location: "Video call · Meet",
      isOnline: true,
      status: "protected",
    },
    {
      id: "event-follow-up",
      title: "Vendor follow-up notes",
      start: "4:00 PM",
      end: "4:30 PM",
      location: "Focus time",
      isOnline: false,
      status: "normal",
    },
  ];
}

export function createDisruption(scenario: ScenarioName): Disruption {
  const isNoSafeFix = scenario === "no-safe-fix";
  return {
    id: isNoSafeFix ? "disruption-closure" : "disruption-traffic",
    type: isNoSafeFix ? "closure" : "traffic",
    delayMin: isNoSafeFix ? 48 : 25,
    etaBefore: "8:35 AM",
    etaAfter: isNoSafeFix ? "9:23 AM" : "9:00 AM",
    source: "simulated",
    detectedAt: new Date().toISOString(),
  };
}

export function createPlan(scenario: ScenarioName): Action[] {
  if (scenario === "no-safe-fix") {
    return [
      {
        id: "action-escalate",
        kind: "escalate",
        title: "Choose how to handle the client sync",
        rationale:
          "Every alternate route is blocked. The 9:00 AM start is at risk, so this needs your call.",
        risk: "high",
        status: "proposed",
        source: "simulated",
        params: { eventId: "event-client-sync", options: ["notify", "reschedule"] },
      },
    ];
  }

  return [
    {
      id: "action-reroute",
      kind: "reroute",
      title: "Take Riverside Drive",
      rationale:
        "It avoids the collision on I‑94 and keeps your arrival within the meeting buffer.",
      risk: "low",
      status: "proposed",
      source: "simulated",
      params: { route: "Riverside Drive", savesMin: 17 },
    },
    {
      id: "action-email",
      kind: "draft_email",
      title: "Prepare a note for the organizer",
      rationale:
        "A brief heads-up gives the client a clear arrival update without sending anything yet.",
      risk: "low",
      status: "proposed",
      source: "simulated",
      params: {
        to: "mira@northstar.example",
        subject: "Running a few minutes behind",
        body: "Hi Mira — traffic is moving slowly near the river interchange. I’m taking an alternate route and will keep you updated on my arrival. Thanks for your flexibility.",
      },
    },
    {
      id: "action-move",
      kind: "move_event",
      title: "Move vendor follow-up to 5:00 PM",
      rationale:
        "The afternoon has an open half-hour, so this focus block can move without affecting other meetings.",
      risk: "medium",
      status: "proposed",
      source: "simulated",
      params: {
        eventId: "event-follow-up",
        beforeStart: "4:00 PM",
        beforeEnd: "4:30 PM",
        afterStart: "5:00 PM",
        afterEnd: "5:30 PM",
      },
    },
    {
      id: "action-protect",
      kind: "no_op",
      title: "Keep the 1:00 PM review protected",
      rationale:
        "This review is time-sensitive and already online; no calendar change is needed.",
      risk: "low",
      status: "proposed",
      source: "simulated",
      params: { eventId: "event-review", protected: true },
    },
  ];
}