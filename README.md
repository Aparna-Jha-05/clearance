# CLEARANCE

**The decision layer above detection. Gate the action, not the answer.**

CLEARANCE is a drop-in, OpenAI-compatible gateway that decides not on *content
risk* alone but on `(risk, reversibility of the specific action)`. The same
fabricated sentence is **annotated** as a draft note and **blocked-and-escalated**
when it would drive a refund. Identical detection, two verdicts.

```
   one model response:  "You are entitled to a full refund of €200, and it will be credited to your card."
   ─────────────────────────────────────────────────────────────────────────────────────────────────────
   context A →  ticket.note   (reversible)    →  ANNOTATE   ·  action released, text flagged
   context B →  refund.issue  (irreversible)  →  ESCALATE   ·  action held, routed to a human
```

*The pitch: one response, two action contexts, two verdicts. Reproduce it live
with the commands below — no API key required. A 20-second screen capture of this
moment belongs at the top of the repo; the runsheet is in
[`docs/demo-runsheet.md`](docs/demo-runsheet.md).*

**▶ Live console:** `https://<your-app>.vercel.app` · **API:** `https://<your-app>.onrender.com`
(the deployed console shows committed sample data if the backend is cold, then
switches to live automatically — it never shows a blank screen). Deploy it
yourself in ~10 min: [`DEPLOY.md`](DEPLOY.md). Recording a demo video?
[`docs/demo-video-script.md`](docs/demo-video-script.md).

---

## Problem (three sentences)

The 2026 guardrail market detects risky content well but decides poorly: a
verdict is scoped by endpoint at best, so a hallucinated refund window is treated
the same whether it is shown in a brainstorm or used to move money. Sampling to
control cost trades away coverage, and the operating point that governs all of it
is an undocumented engineering default. CLEARANCE keeps 100% coverage, indexes
every verdict to the reversibility of the action it would drive, and turns the
operating point into a signed, auditable governance artifact.

## How this differs from Lakera / Patronus / Bedrock Guardrails

- **Reversibility-indexed verdicts.** Incumbents decide on content risk. CLEARANCE
  decides on `(risk, reversibility)`. Identical response text → two verdicts. Nobody
  ships this. It is the first thing the demo shows.
- **Cost-proportional coverage that improves.** 100% at L0 (no LLM call), escalate
  spend only in the uncertainty band, and the expensive tier trains the cheap one —
  paid-tier traffic falls **~9% → ~1%** with recall held.
- **The operating point as a signed artifact.** Chosen by a named risk owner, dated,
  rationalised, and SHA-256-hashed into every ledger row. Moving the tuning slider
  *is* re-signing the operating point.

Every detector sits behind one adapter interface, so Lakera / Presidio / Bedrock /
Patronus can *be the backend*. See
[`docs/competitive-landscape.md`](docs/competitive-landscape.md) and the working
seam in [`patronus_stub.py`](clearance/detectors/backends/patronus_stub.py).

---

## Quickstart (offline, zero keys)

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python scripts\seed_corpus.py
python scripts\seed_fixtures.py
python scripts\run_replay.py --offline
```

`run_replay.py --offline` runs the whole system on committed corpus + fixtures and
reproduces every number below. Optional: `python -m spacy download en_core_web_sm`
and `pip install sentence-transformers` upgrade the local detectors from the
deterministic fallbacks to their full backends (the repo runs fine without them).

**Run the gateway + console:**

```
uvicorn clearance.app:app --reload
```
```
cd console && npm install && npm run dev
```
Console at http://localhost:3000 (Live / Tuning / Ledger). Gateway at
http://localhost:8000/v1 — point any OpenAI client at it.

---

## Demo moments (each with the command to reproduce it)

**1 — The paired verdict (same text, two verdicts), against the live gateway:**
```
curl -s http://localhost:8000/v1/chat/completions -H "Content-Type: application/json" -d "{\"model\":\"gpt-4o-mini\",\"messages\":[{\"role\":\"user\",\"content\":\"Can I get a refund for my delayed order?\"}],\"clearance\":{\"policy\":\"support-assistant.eu\",\"retrieved\":[\"Returns must be initiated within 14 days for unused items in original packaging.\"],\"action\":{\"tool\":\"ticket.note\"}}}"
```
Swap `ticket.note` → `refund.issue`: identical text, `annotate` becomes `escalate`
and the action is **not released**.

**2 — Agentic compounding:** `python scripts\run_replay.py --offline` prints turn 6
issuing a refund on a premise planted at turn 3. CLEARANCE blocks it; a naive
per-response checker passes it (it is grounded in the conversation).

**3 — Tuning:** open **Tuning** — two use cases at deliberately different operating
points; drag a slider, all metrics recompute against the corpus in < 300ms.

**4 — Overlap:** a fabricated named-person detail emerges tagged
`{hallucination, privacy}` — one event, two categories, never forced into one.

**5 — Ledger integrity:** open **Ledger**, click *verify chain* (green), *tamper a
row* (red). Or `python scripts\verify_ledger.py`.

**6 — Jurisdiction swap:** the same refund text yields `escalate` under
`support-assistant.eu` and `hold` under `support-assistant.in` — two packs, two
policy hashes, no restart.

---

## Results

Offline replay, default (signed) operating point. Corpus: 160 synthetic,
single-annotator records, **base rate 21% risky** (see
[`corpus/README.md`](corpus/README.md)). These are **relative measures for
comparing operating points**, not absolute accuracy.

| use case | precision | recall | F2 | FP rate | added p95 | $ / 1k |
|---|---|---|---|---|---|---|
| support-assistant (EU) | 1.00 | 0.87 | 0.89 | 0.00 | ~1.5 ms | 0.195 |
| internal-copilot (IN)  | 1.00 | 0.91 | 0.93 | 0.00 | ~1.5 ms | 0.149 |
| decision-support (EU)  | 1.00 | 0.90 | 0.92 | 0.00 | ~1.5 ms | 0.152 |

L0 throughput ~1,900 req/s single core, **p95 1.5 ms** (`python scripts\bench.py`).
Four-week learning curve: paid tier **9.4% → 1.2%**, recall held
(`python scripts\train_l1.py`).

---

## What is real vs simulated

- **Real:** the gateway, hash-chained ledger, all five L0 detectors, the CEG, the
  policy engine + action gate + latch, the reversibility-indexed paired verdict, the
  conversation accumulator, the tuning recompute, jurisdiction swap, and the L1
  learning loop (a calibrated classifier retrained on accumulated labels).
- **Simplified / simulated:** L1 is a logistic model over L0 features, not a distilled
  LLM. The four-week curve uses a documented label-accrual schedule. The local detector
  backends are deliberately thin — CLEARANCE claims the decision layer, not detection
  SOTA. Offline, the L2 jury abstains (no fixtures) and the CEG entropy term falls back
  to 0 unless a resample/`self_consistency` signal is present.

Full honesty pass: [`docs/limitations.md`](docs/limitations.md).

---

## Tests

```
python tests\test_clearance.py
```
The six required behaviors: paired verdict, category overlap, latch fail-closed,
ledger tamper detection, policy swap, agentic accumulator block.

## Deploy (console on Vercel, gateway on Render/Railway)

The console is a Next.js app in `console/`; the gateway is a stateful FastAPI
process (hash-chained ledger) that needs a real host, not the edge. Deploy the
backend first, then set `NEXT_PUBLIC_API_BASE` on Vercel to its URL. Full steps:
[`DEPLOY.md`](DEPLOY.md).

## Docs
- [`docs/architecture.md`](docs/architecture.md)
- [`docs/competitive-landscape.md`](docs/competitive-landscape.md)
- [`docs/limitations.md`](docs/limitations.md)
- [`docs/threat-model.md`](docs/threat-model.md)

## Team & licence
Accenture Innovation Challenge 2026 · Round 2 · Track 1 (ControlPlane.ai).
MIT licensed ([`LICENSE`](LICENSE)).
