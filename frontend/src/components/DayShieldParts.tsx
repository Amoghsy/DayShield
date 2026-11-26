import { useEffect, useRef, useState } from "react";
import {
  Activity,
  AlertTriangle,
  ArrowDownRight,
  ArrowRight,
  CalendarDays,
  Check,
  CheckCircle2,
  ChevronDown,
  Circle,
  Clock3,
  CloudLightning,
  Compass,
  FileText,
  MapPin,
  MoveRight,
  RefreshCw,
  Route,
  Shield,
  ShieldCheck,
  Sparkles,
  Video,
  Wifi,
  X,
  Zap,
} from "lucide-react";

import type {
  Action,
  AgentName,
  AgentState,
  CalendarEvent,
  ConnectionStatus,
  Disruption,
  LogEntry,
  Mode,
} from "../types";

const agentTitles: Record<AgentName, string> = {
  commute: "Commute",
  schedule: "Schedule",
  priority: "Priority",
  recovery: "Recovery",
};

const agentIcons = {
  commute: Compass,
  schedule: CalendarDays,
  priority: ShieldCheck,
  recovery: Sparkles,
} satisfies Record<AgentName, typeof Compass>;

const actionIcons = {
  reroute: Route,
  draft_email: FileText,
  move_event: MoveRight,
  join_online: Video,
  escalate: AlertTriangle,
  no_op: ShieldCheck,
} satisfies Record<Action["kind"], typeof Route>;

const connectionLabels: Record<ConnectionStatus, string> = {
  connecting: "Connecting",
  connected: "Connected",
  reconnecting: "Reconnecting",
  error: "Connection issue",
};

export function SourceBadge({ source }: { source: "live" | "simulated" }) {
  const isLive = source === "live";
  return (
    <span className={`source-badge ${isLive ? "source-badge-live" : "source-badge-simulated"}`}>
      <span className="source-dot" aria-hidden="true" />
      {isLive ? "LIVE" : "SIMULATED"}
    </span>
  );
}

type TopBarProps = {
  mode: Mode;
  connection: ConnectionStatus;
  onModeChange: (mode: Mode) => void;
  onTrigger: () => void;
  onNoSafeFix: () => void;
  onReset: () => void;
};

export function TopBar({
  mode,
  connection,
  onModeChange,
  onTrigger,
  onNoSafeFix,
  onReset,
}: TopBarProps) {
  return (
    <header className="topbar">
      <div className="topbar-brand">
        <span className="brand-mark" aria-hidden="true"><ShieldCheck size={19} /></span>
        <span className="brand-word">DayShield</span>
        <span className="brand-divider" aria-hidden="true" />
        <span className="brand-context">PERSONAL RESPONSE DESK</span>
      </div>

      <div className="topbar-controls">
        <div className="mode-switch" aria-label="Stream mode" role="group">
          <button
            type="button"
            aria-pressed={mode === "live"}
            className={mode === "live" ? "mode-option mode-option-active" : "mode-option"}
            onClick={() => onModeChange("live")}
          >
            <span className="mode-dot mode-dot-live" /> Live
          </button>
          <button
            type="button"
            aria-pressed={mode === "simulated"}
            className={mode === "simulated" ? "mode-option mode-option-active" : "mode-option"}
            onClick={() => onModeChange("simulated")}
          >
            <span className="mode-dot mode-dot-simulated" /> Simulated
          </button>
        </div>

        <div className={`connection-indicator connection-${connection}`} role="status" aria-label={connectionLabels[connection]}>
          <span className="connection-led" aria-hidden="true" />
          <span>{connectionLabels[connection]}</span>
        </div>

        <div className="topbar-actions">
          <div className="scenario-control">
            <button type="button" className="button button-primary" onClick={onTrigger}>
              <Zap size={15} aria-hidden="true" />
              Trigger disruption
            </button>
            <details className="scenario-menu">
              <summary aria-label="Choose a disruption scenario" title="Choose a disruption scenario">
                <ChevronDown size={15} aria-hidden="true" />
              </summary>
              <div className="scenario-popover">
                <span className="popover-label">SIMULATION SCENARIOS</span>
                <button type="button" onClick={onTrigger}>
                  <CloudLightning size={15} aria-hidden="true" /> Traffic slowdown
                </button>
                <button type="button" onClick={onNoSafeFix}>
                  <AlertTriangle size={15} aria-hidden="true" /> No safe fix available
                </button>
              </div>
            </details>
          </div>
          <button type="button" className="button button-quiet" onClick={onReset}>
            <RefreshCw size={14} aria-hidden="true" />
            Reset demo
          </button>
        </div>
      </div>
    </header>
  );
}

export function DisruptionBanner({ disruption }: { disruption: Disruption }) {
  const disruptionLabels = {
    traffic: "Traffic slowdown",
    weather: "Severe weather",
    closure: "Road closure",
  };
  return (
    <section className="disruption-banner" aria-live="polite" aria-atomic="true">
      <div className="disruption-icon" aria-hidden="true"><AlertTriangle size={19} /></div>
      <div className="disruption-main">
        <div className="disruption-heading">
          <span className="eyebrow">ACTIVE DISRUPTION</span>
          <SourceBadge source={disruption.source} />
        </div>
        <h2>{disruptionLabels[disruption.type]}</h2>
        <p>{disruption.delayMin} min added to the morning commute</p>
      </div>
      <div className="eta-block">
        <span className="eta-label">ARRIVAL WINDOW</span>
        <div className="eta-values">
          <span className="eta-before">{disruption.etaBefore}</span>
          <ArrowRight size={16} aria-hidden="true" />
          <span className="eta-after">{disruption.etaAfter}</span>
        </div>
      </div>
      <div className="disruption-status">
        <span className="status-halo" aria-hidden="true"><Activity size={15} /></span>
        <span>Assessing options</span>
      </div>
    </section>
  );
}

export function ReconnectingBanner({ message }: { message: string }) {
  return (
    <div className="reconnecting-banner" role="status" aria-live="polite">
      <RefreshCw size={15} className="animate-spin" aria-hidden="true" />
      <span>{message}</span>
    </div>
  );
}

export function DayTimeline({ events }: { events: CalendarEvent[] }) {
  return (
    <section className="timeline-section" aria-labelledby="timeline-title">
      <div className="section-heading">
        <div>
          <div className="eyebrow">YOUR CALENDAR</div>
          <h2 id="timeline-title">Today’s timeline</h2>
        </div>
        <span className="count-pill">{events.length} EVENTS</span>
      </div>

      {events.length === 0 ? (
        <div className="timeline-empty">
          <CalendarDays size={18} aria-hidden="true" />
          <p>Your calendar is loading.</p>
        </div>
      ) : (
        <ol className="timeline-list">
          {events.map((event) => {
            const moved = event.status === "moved";
            const atRisk = event.status === "at_risk";
            const protectedEvent = event.status === "protected";
            return (
              <li className={`timeline-item ${moved ? "timeline-item-moved" : ""}`} key={event.id}>
                <div className="timeline-time">
                  <span>{event.start}</span>
                  <span className="timeline-end">{event.end}</span>
                </div>
                <div className={`timeline-marker ${atRisk ? "marker-risk" : protectedEvent ? "marker-protected" : ""}`}>
                  {atRisk ? <AlertTriangle size={13} /> : protectedEvent ? <ShieldCheck size={13} /> : <Circle size={8} />}
                </div>
                <div className={`event-content ${atRisk ? "event-at-risk" : ""}`}>
                  <div className="event-title-row">
                    <h3>{event.title}</h3>
                    {atRisk && <span className="late-pill">{event.minutesLate ?? 0} MIN LATE</span>}
                    {protectedEvent && <span className="protected-label"><Shield size={12} /> Protected</span>}
                  </div>
                  <div className="event-meta">
                    <MapPin size={12} aria-hidden="true" />
                    <span>{event.location ?? "Location not set"}</span>
                    {event.isOnline && <span className="online-label"><Video size={12} /> Online</span>}
                  </div>
                  {moved && (
                    <div className="moved-indicator">
                      <ArrowDownRight size={14} aria-hidden="true" />
                      <span>Moved to {event.proposedStart ?? "a new slot"}</span>
                    </div>
                  )}
                </div>
              </li>
            );
          })}
        </ol>
      )}
    </section>
  );
}

export function AgentLane({ agent }: { agent: AgentState }) {
  const Icon = agentIcons[agent.name];
  const running = agent.status === "running";
  const done = agent.status === "done";
  return (
    <article className={`agent-lane ${running ? "agent-running" : ""} ${done ? "agent-done" : ""}`}>
      <div className="agent-icon"><Icon size={17} aria-hidden="true" /></div>
      <div className="agent-content">
        <div className="agent-title-row">
          <h3>{agentTitles[agent.name]}</h3>
          <span className={`agent-state agent-state-${agent.status}`}>
            {running && <span className="agent-spinner" aria-hidden="true" />}
            {done && <CheckCircle2 size={13} aria-hidden="true" />}
            {!running && !done && <Circle size={9} aria-hidden="true" />}
            {agent.status}
          </span>
        </div>
        <p>{agent.summary ?? (running ? "Reviewing the latest conditions…" : "Waiting for a disruption")}</p>
        <details className="agent-details">
          <summary>View agent details <ChevronDown size={13} aria-hidden="true" /></summary>
          <pre>{agent.output === undefined ? "No output yet." : JSON.stringify(agent.output, null, 2)}</pre>
        </details>
      </div>
    </article>
  );
}

function getParam(action: Action, key: string): string {
  const value = action.params[key];
  return typeof value === "string" ? value : "—";
}

export function EmailDraftPreview({ action }: { action: Action }) {
  return (
    <div className="email-preview">
      <div className="email-preview-heading">
        <span><FileText size={13} /> EMAIL PREVIEW</span>
        {action.status === "executed" && <span className="draft-confirmation"><Check size={12} /> Draft created · not sent</span>}
      </div>
      <dl>
        <div><dt>To</dt><dd>{getParam(action, "to")}</dd></div>
        <div><dt>Subject</dt><dd>{getParam(action, "subject")}</dd></div>
        <div className="email-body"><dt>Message</dt><dd>{getParam(action, "body")}</dd></div>
      </dl>
    </div>
  );
}

export function MoveDiff({ action }: { action: Action }) {
  return (
    <div className="move-diff">
      <div className="move-slot move-slot-before">
        <span>BEFORE</span>
        <strong>{getParam(action, "beforeStart")}</strong>
        <small>{getParam(action, "beforeEnd")}</small>
      </div>
      <MoveRight size={17} aria-hidden="true" />
      <div className="move-slot move-slot-after">
        <span>PROPOSED</span>
        <strong>{getParam(action, "afterStart")}</strong>
        <small>{getParam(action, "afterEnd")}</small>
      </div>
    </div>
  );
}

type RecoveryPlanProps = {
  actions: Action[];
  pendingActions: Record<string, "approve" | "reject">;
  hasDisruption: boolean;
  onApprove: (action: Action) => void;
  onReject: (action: Action) => void;
};

export function RecoveryPlan({ actions, pendingActions, hasDisruption, onApprove, onReject }: RecoveryPlanProps) {
  return (
    <section className="recovery-section" aria-labelledby="recovery-title" aria-live="polite">
      <div className="section-heading recovery-heading">
        <div>
          <div className="eyebrow">HUMAN-IN-THE-LOOP</div>
          <h2 id="recovery-title">Recovery plan</h2>
        </div>
        {actions.length > 0 && <span className="count-pill">{actions.length} PROPOSALS</span>}
      </div>

      {actions.length > 0 ? (
        <ol className="action-list">
          {actions.map((action, index) => (
            <ActionCard
              key={action.id}
              action={action}
              order={index + 1}
              pending={pendingActions[action.id]}
              onApprove={() => onApprove(action)}
              onReject={() => onReject(action)}
            />
          ))}
        </ol>
      ) : (
        <div className="recovery-empty">
          {hasDisruption ? (
            <><span className="agent-spinner" aria-hidden="true" /><span>Agents are weighing recovery options…</span></>
          ) : (
            <><ShieldCheck size={17} aria-hidden="true" /><span>No active disruption. Your day is protected.</span></>
          )}
        </div>
      )}
    </section>
  );
}

function ActionCard({
  action,
  order,
  pending,
  onApprove,
  onReject,
}: {
  action: Action;
  order: number;
  pending: "approve" | "reject" | undefined;
  onApprove: () => void;
  onReject: () => void;
}) {
  const Icon = actionIcons[action.kind];
  const canRespond = action.status === "proposed" || action.status === "failed";
  const statusLabel = action.status === "executed" && action.kind === "draft_email" ? "draft created" : action.status;
  return (
    <li className={`action-card action-card-${action.status}`}>
      <div className="action-index" aria-hidden="true">{String(order).padStart(2, "0")}</div>
      <div className="action-icon"><Icon size={17} aria-hidden="true" /></div>
      <div className="action-body">
        <div className="action-title-row">
          <h3>{action.title}</h3>
          <SourceBadge source={action.source} />
        </div>
        <p className="action-rationale">{action.rationale}</p>
        {action.kind === "draft_email" && <EmailDraftPreview action={action} />}
        {action.kind === "move_event" && <MoveDiff action={action} />}
        {action.error && (
          <div className="action-error" role="alert">
            <AlertTriangle size={14} aria-hidden="true" />
            <span>{action.error}</span>
          </div>
        )}
      </div>
      <div className="action-controls">
        <span className={`risk-pill risk-${action.risk}`}>{action.risk} risk</span>
        <span className={`action-status action-status-${action.status}`}>
          {action.status === "executed" ? <CheckCircle2 size={13} /> : action.status === "rejected" ? <X size={13} /> : action.status === "failed" ? <AlertTriangle size={13} /> : action.status === "approved" ? <Check size={13} /> : <Circle size={9} />}
          {statusLabel}
        </span>
        {canRespond && (
          <div className="decision-buttons">
            <button type="button" className="button button-approve" onClick={onApprove} disabled={Boolean(pending)}>
              {pending === "approve" ? <span className="agent-spinner" aria-hidden="true" /> : <Check size={14} aria-hidden="true" />}
              {pending === "approve" ? "Approving…" : action.status === "failed" ? "Retry" : "Approve"}
            </button>
            <button type="button" className="button button-reject" onClick={onReject} disabled={Boolean(pending)}>
              {pending === "reject" ? <span className="agent-spinner" aria-hidden="true" /> : <X size={14} aria-hidden="true" />}
              {pending === "reject" ? "Rejecting…" : "Reject"}
            </button>
          </div>
        )}
        {pending && <span className="pending-note">Waiting for response</span>}
      </div>
    </li>
  );
}

export function ToolLog({ logs }: { logs: LogEntry[] }) {
  const [paused, setPaused] = useState(false);
  const listRef = useRef<HTMLTableSectionElement>(null);

  useEffect(() => {
    if (!paused && logs.length > 0) {
      listRef.current?.lastElementChild?.scrollIntoView({ block: "nearest", behavior: "smooth" });
    }
  }, [logs.length, paused]);

  return (
    <details className="tool-log" open>
      <summary className="tool-log-summary">
        <div className="tool-log-title">
          <span className="log-icon"><Activity size={16} aria-hidden="true" /></span>
          <div><span className="eyebrow">TRACE</span><h2>Tool-call log</h2></div>
          <span className="log-count">{logs.length.toString().padStart(2, "0")}</span>
        </div>
        <div className="tool-log-summary-right">
          <span className="auto-scroll-label"><Wifi size={13} /> {paused ? "Auto-scroll paused" : "Auto-scroll on"}</span>
          <ChevronDown size={16} aria-hidden="true" />
        </div>
      </summary>
      <div className="tool-log-content" onMouseEnter={() => setPaused(true)} onMouseLeave={() => setPaused(false)}>
        {logs.length === 0 ? (
          <div className="log-empty"><Clock3 size={15} /> Tool calls will appear here as the agents work.</div>
        ) : (
          <div className="log-table-wrap">
            <table>
              <thead>
                <tr><th>TIME</th><th>ACTOR</th><th>TOOL</th><th>INPUT</th><th>OUTPUT</th><th>SOURCE</th><th>STATUS</th></tr>
              </thead>
              <tbody ref={listRef}>
                {logs.map((entry) => <ToolLogRow key={entry.id} entry={entry} />)}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </details>
  );
}

function ToolLogRow({ entry }: { entry: LogEntry }) {
  return (
    <tr className="log-row-enter">
      <td className="log-time">{entry.ts}</td>
      <td>{entry.actor}</td>
      <td className="log-tool">{entry.tool}</td>
      <td className="log-summary-cell">{entry.inputSummary}</td>
      <td className="log-summary-cell">{entry.outputSummary}</td>
      <td><SourceBadge source={entry.source} /></td>
      <td><span className={`log-status ${entry.status === "ok" ? "log-status-ok" : "log-status-error"}`}>
        {entry.status === "ok" ? <CheckCircle2 size={12} /> : <AlertTriangle size={12} />}{entry.status}
      </span></td>
    </tr>
  );
}