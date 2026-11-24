# DayShield

DayShield is a real-time disruption response desk. Its simulated stream demonstrates commute, schedule, priority, and recovery agents while keeping every proposed change behind an explicit approval.

## Run the dashboard

```sh
npm install
npm run dev
```

The dashboard starts in simulated mode and runs entirely in the browser. No calendar, email, or route change is sent from the simulation. Use **Trigger disruption** for the standard traffic scenario, or the adjacent scenario menu for a closure with no safe fix. **Reset demo** restores the sample day.

## Connect a live service

Set `VITE_USE_MOCK=false` before starting Vite to use the live API instead of the local mock stream. Optionally set `VITE_API_BASE_URL` to the API origin; an empty value uses the current origin. The live stream reconnects with backoff if the connection drops.

The browser expects these API contracts:

| Request | Expected behavior |
| --- | --- |
| `GET /api/events` | Returns an array of today's calendar events using the fields in `src/types.ts`. |
| `GET /api/stream` | Server-Sent Events, with named events `events_loaded`, `disruption_detected`, `agent_started`, `agent_output`, `plan_ready`, `action_approved`, `action_executed`, `action_failed`, `log_entry`, and `reset`. Each `data:` field is JSON. |
| `POST /api/sim/trigger` | Accepts `{ "scenario": "commute" | "no-safe-fix" }` and publishes resulting events on the stream. |
| `POST /api/sim/reset` | Resets the demo and publishes `reset` plus a refreshed `events_loaded` event. |
| `POST /api/actions/:id/approve` or `/reject` | Accepts a user's explicit decision; publishes `action_approved` then `action_executed` or `action_failed` for approval. Rejection should publish `action_rejected` (an extension used by this UI). |
| `PUT /api/mode` | Accepts `{ "mode": "live" | "simulated" }`. |

## API assumptions

- SSE event names carry the event payload; payloads may include a matching `type` field. Action acknowledgements and outcomes arrive on the stream, not as optimistic calendar updates.
- `action_rejected` is an additional stream event so the UI can distinguish rejection from a pending or failed action.
- A successful email approval creates a draft only; it must never send the email. Emit a `log_entry` for `email.create_draft` after the draft exists.
- The demo calendar has four sample events and uses plain text for titles, locations, and message previews.