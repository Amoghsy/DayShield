import type { Mode } from "../types";

const apiBase = import.meta.env.VITE_API_BASE_URL ?? "";

export async function requestApi<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${apiBase}${path}`, {
    ...init,
    headers: {
      ...(init.body ? { "content-type": "application/json" } : {}),
      ...init.headers,
    },
  });
  if (!response.ok) {
    throw new Error(`Request failed (${response.status})`);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export function setRemoteMode(mode: Mode): Promise<void> {
  return requestApi<void>("/api/mode", {
    method: "PUT",
    body: JSON.stringify({ mode }),
  });
}

export function triggerRemoteScenario(scenario: string): Promise<void> {
  return requestApi<void>("/api/sim/trigger", {
    method: "POST",
    body: JSON.stringify({ scenario }),
  });
}

export function resetRemoteDemo(): Promise<void> {
  return requestApi<void>("/api/sim/reset", { method: "POST" });
}

export function submitRemoteAction(actionId: string, decision: "approve" | "reject"): Promise<void> {
  return requestApi<void>(`/api/actions/${encodeURIComponent(actionId)}/${decision}`, {
    method: decision === "approve" ? "POST" : "POST",
  });
}