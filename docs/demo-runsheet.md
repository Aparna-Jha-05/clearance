# Demo video runsheet (3 minutes)

Record with the gateway on `:8000` and the console on `:3000`, both offline.

- **0:00–0:15 — One line changes.** Show a diff of the application's `base_url`
  pointing at `http://localhost:8000/v1`. It is now governed. Nothing else changes.

- **0:15–0:50 — The paired verdict (lead with this, not architecture).** On the
  **Live** page, the hero: one model response, two action contexts. `ticket.note`
  → ANNOTATE, action released. `refund.issue` → ESCALATE, action held. Same text.
  Cut to the two ledger rows side by side. Reproduce live with the curl in the
  README if you want to show it is not staged.

- **0:50–1:20 — The agentic case.** The agentic timeline: turn 3 plants an
  unsupported 30-day goodwill window (allowed, text only). Turn 6 issues the refund
  citing its own claim. CLEARANCE blocks it; the per-response column shows `allow`.
  Explain why a per-response checker passes it: it is grounded in the conversation.

- **1:20–1:55 — The tuning slider.** On **Tuning**, two use cases at deliberately
  different operating points. Drag `l0_low` on support-assistant: watch recall rise,
  precision fall, escalations and reviewer-hours move — all recomputing in < 300ms.
  Point at decision-support sitting tighter: same engine, different appetite.

- **1:55–2:25 — Overlap, then ledger integrity.** Click a copilot decision: one
  fabricated named-person detail, tagged BOTH `hallucination` and `privacy`. Then on
  **Ledger**, click *verify chain* (green), *tamper a row* (red).

- **2:25–3:00 — Jurisdiction swap.** Same refund text under `support-assistant.eu`
  (escalate) vs `support-assistant.in` (hold) — two policy hashes, no restart. Close
  on: **gate the action, not the answer.**
