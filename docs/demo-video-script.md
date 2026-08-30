# Demo video script — recording from the deployed Vercel app

Target length **3:00**. Everything is driven from the **deployed console**
(`https://<your-app>.vercel.app`); no terminal on screen. Narration is in quotes,
actions in **bold**, timing on the left.

---

## Pre-flight (do this 5 minutes before you hit record)

1. **Deploy both halves** ([`DEPLOY.md`](DEPLOY.md)): backend on Render, console on
   Vercel with `NEXT_PUBLIC_API_BASE` set to the backend URL.
2. **Warm the backend** so it is not cold mid-demo: open
   `https://<your-app>.onrender.com/health` in a tab and refresh until you see
   `{"ok": true, ...}`. Keep that tab; revisit it if you pause between takes
   (Render free tier sleeps after ~15 min idle).
   - Safety net: even if it is cold, the console shows an amber *"committed sample
     data"* banner and still works — but for a clean recording, warm it.
3. **Open the console** at `https://<your-app>.vercel.app`. Let the Live page load
   fully (paired hero populated, decision feed filled).
4. **Set the look:** pick **light or dark** with the toggle (top-right). Dark reads
   better on a screen recording; light reads better if projected. Zoom the browser
   to ~110–125% so text is legible in the video. Hide the bookmarks bar.
5. **Pre-click nothing.** Start on the Live page, Example 1 selected.

Recording tips: 1080p, cursor-highlight on if your tool has it, close other tabs,
mute notifications.

---

## The script

### 0:00–0:15 — Framing
- **Stay on the Live page.** Point at the header.
- *"Every AI guardrail on the market decides whether the text is risky. Clearance
  decides whether to let the action happen — and it turns out those are different
  questions."*

### 0:15–0:55 — The paired verdict (the whole pitch)
- **Point at the paired hero.** Read the one response aloud.
- *"Here's one model response — a made-up €200 refund. On the left, it's going into
  a draft note: reversible. Clearance annotates it and lets it through."*
- **Point at Context A → ANNOTATE**, then **Context B → ESCALATE**.
- *"On the right, the exact same sentence is about to trigger a real refund:
  irreversible. Clearance blocks it and routes it to a human. Same text, same
  detection — the decision flips on the reversibility of the action."*
- **Click the "Copilot · fabricated salary" tab.**
- *"It's not one hard-coded example. Here's a fabricated salary about a named
  colleague — same rule: fine as an internal draft, blocked when it's about to be
  emailed out."*

### 0:55–1:30 — Agentic compounding
- **Point at the "Agentic compounding" panel** (left of the feed).
- *"Now the case everyone's worried about in 2026 — agents. Watch the risk bar
  build across a conversation."*
- **Trace turns 3 → 6 with the cursor.**
- *"At turn 3 the agent invents a 'goodwill refund window' — it's just text, so it's
  allowed. By turn 6 it tries to issue the refund, citing its own earlier claim."*
- **Point at the two verdict columns on turn 6.**
- *"A normal per-response checker passes turn 6 — it's grounded in the conversation.
  Clearance carries forward that the premise was never externally supported, and
  blocks it. That's the difference between checking answers and governing actions."*

### 1:30–2:05 — The operating point (Tuning)
- **Click "Tuning" in the nav.**
- *"Coverage isn't the trade-off — the operating point is, and here it's an explicit,
  signed artifact."*
- **Drag the `l0_low` slider on the left panel** slowly.
- *"As I move it, precision, recall, escalations per thousand, and weekly reviewer
  hours all recompute against the labelled corpus in real time — under 300
  milliseconds."*
- **Gesture across to the second panel.**
- *"And two use cases sit at deliberately different points: decision-support runs
  tighter than support. Same engine, different risk appetite — chosen by a named
  owner, not buried in code."*

### 2:05–2:35 — Integrity (Ledger)
- **Click "Ledger".**
- **Click "verify chain"** → green banner.
- *"Every decision is written to an append-only, hash-chained ledger. Right now the
  chain verifies clean."*
- **Click "⚠ tamper a row"** → red banner.
- *"If anyone edits a past decision — even one row — the chain breaks and the audit
  catches it. Governance you can prove, not just claim."*

### 2:35–3:00 — Close
- **Click back to "Live".**
- *"One line changed in the application — the base URL. Everything else is the same.
  It's now governed: 100% coverage, escalation only when uncertain, and every
  action indexed to whether it can be undone."*
- **Let the paired hero sit on screen.**
- *"Clearance. Gate the action, not the answer."*

---

## Contingencies
- **Backend cold / amber banner shows:** either wait ~30s and reload once (it goes
  live), or narrate it as a feature — *"even offline it serves committed sample data
  so it never breaks"* — then continue; the tamper→red still works in sample mode.
- **Slider feels laggy on Tuning:** the first recompute after a cold start warms it;
  do one throwaway drag before recording.
- **Want it shorter (90s):** keep beats 1 (paired) and 2 (agentic) only, then close.
