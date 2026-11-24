import { useEffect, useRef } from "react";

import { connectLiveStream } from "../api/stream";
import {
  resetRemoteDemo,
  setRemoteMode,
  submitRemoteAction,
  triggerRemoteScenario,
} from "../api/client";
import {
  createMockEventSource,
  type MockStreamController,
} from "../mock/stream";
import { useDayShield } from "../store/useDayShield";
import type { Action, Mode } from "../types";
import {
  AgentLane,
  DayTimeline,
  DisruptionBanner,
  ReconnectingBanner,
  RecoveryPlan,
  ToolLog,
  TopBar,
} from "./DayShieldParts";

type StreamController = MockStreamController | { close: () => void };

export function DayShieldDashboard() {
  const mode = useDayShield((state) => state.mode);
  const connection = useDayShield((state) => state.connection);
  const connectionMessage = useDayShield((state) => state.connectionMessage);
  const events = useDayShield((state) => state.events);
  const disruption = useDayShield((state) => state.disruption);
  const agents = useDayShield((state) => state.agents);
  const actions = useDayShield((state) => state.actions);
  const logs = useDayShield((state) => state.logs);
  const pendingActions = useDayShield((state) => state.pendingActions);
  const controllerRef = useRef<StreamController | null>(null);

  useEffect(() => {
    const onEvent = useDayShield.getState().applyEvent;
    const setConnection = useDayShield.getState().setConnection;
    const controller = mode === "simulated"
      ? createMockEventSource(onEvent, (status) => setConnection(status))
      : connectLiveStream(onEvent, setConnection);
    controllerRef.current = controller;
    return () => {
      controller.close();
      if (controllerRef.current === controller) controllerRef.current = null;
    };
  }, [mode]);

  const changeMode = (nextMode: Mode) => {
    if (nextMode === mode) return;
    useDayShield.getState().setMode(nextMode);
    useDayShield.getState().setConnection("connecting");
    if (nextMode === "live" || mode === "live") {
      void setRemoteMode(nextMode).catch(() => {
        useDayShield.getState().setConnection(
          "reconnecting",
          "Live service unavailable. Reconnecting while you stay in this mode.",
        );
      });
    }
  };

  const triggerScenario = (scenario: "commute" | "no-safe-fix") => {
    if (mode === "simulated") {
      const controller = controllerRef.current;
      if (controller && "trigger" in controller) controller.trigger(scenario);
      return;
    }
    void triggerRemoteScenario(scenario).catch(() => {
      useDayShield.getState().setConnection("reconnecting", "The disruption request could not reach the live service.");
    });
  };

  const resetDemo = () => {
    if (mode === "simulated") {
      const controller = controllerRef.current;
      if (controller && "reset" in controller) controller.reset();
      return;
    }
    void resetRemoteDemo().catch(() => {
      useDayShield.getState().setConnection("reconnecting", "The reset request could not reach the live service.");
    });
  };

  const submitDecision = (action: Action, decision: "approve" | "reject") => {
    const store = useDayShield.getState();
    if (store.pendingActions[action.id]) return;
    store.setPendingAction(action.id, decision);
    if (mode === "simulated") {
      const controller = controllerRef.current;
      if (controller && "approveAction" in controller) {
        if (decision === "approve") controller.approveAction(action.id);
        else controller.rejectAction(action.id);
      } else {
        store.applyEvent({ type: "action_failed", actionId: action.id, error: "The simulation stream is not connected." });
      }
      return;
    }
    void submitRemoteAction(action.id, decision).catch((error: unknown) => {
      const message = error instanceof Error ? error.message : "The request could not be completed.";
      useDayShield.getState().applyEvent({ type: "action_failed", actionId: action.id, error: message });
    });
  };

  const agentOrder = [agents.commute, agents.schedule, agents.priority, agents.recovery];

  return (
    <div className="dashboard-shell">
      <TopBar
        mode={mode}
        connection={connection}
        onModeChange={changeMode}
        onTrigger={() => triggerScenario("commute")}
        onNoSafeFix={() => triggerScenario("no-safe-fix")}
        onReset={resetDemo}
      />

      {connectionMessage && <ReconnectingBanner message={connectionMessage} />}
      {disruption && <DisruptionBanner disruption={disruption} />}

      <main className="dashboard-main">
        <div className="page-intro">
          <div>
            <span className="eyebrow">PERSONAL OPERATIONS · MORNING BRIEF</span>
            <h1>Your day, in good hands.</h1>
          </div>
          <div className="page-clock"><span className="clock-led" /> RESPONSE SYSTEM <span className="clock-divider">/</span> ACTIVE</div>
        </div>

        <div className="overview-grid">
          <DayTimeline events={events} />
          <section className="agents-section" aria-labelledby="agents-title">
            <div className="section-heading">
              <div>
                <div className="eyebrow">COORDINATED RESPONSE</div>
                <h2 id="agents-title">Agent activity</h2>
              </div>
              <span className="agent-count"><span className="count-led" /> 04 AGENTS</span>
            </div>
            <div className="agent-lanes">{agentOrder.map((agent) => <AgentLane key={agent.name} agent={agent} />)}</div>
          </section>
        </div>

        <RecoveryPlan
          actions={actions}
          pendingActions={pendingActions}
          hasDisruption={disruption !== null}
          onApprove={(action) => submitDecision(action, "approve")}
          onReject={(action) => submitDecision(action, "reject")}
        />

        <ToolLog logs={logs} />
      </main>

      <footer className="dashboard-footer">
        <span>DAYSHIELD <span className="footer-divider">·</span> NOTHING CHANGES WITHOUT YOUR APPROVAL</span>
        <span>PERSONAL RESPONSE DESK <span className="footer-divider">/</span> V1.0</span>
      </footer>
    </div>
  );
}