# Architecture

```
  application
      |  POST /v1/chat/completions          (drop-in OpenAI-compatible)
      v
+-------------------------------------------------------------+
|  CLEARANCE GATEWAY (FastAPI)                                 |
|  input guard -> upstream model -> response                   |
|                                    |                         |
|            ANSWER PATH             |      ACTION PATH         |
|      tokens stream immediately     |   tool_calls held        |
|      (zero added latency)          |   at the LATCH           |
|                                    v                         |
|            L0 TRIPWIRE  (100%, no LLM call, adapter-backed)  |
|                     -> uncertainty band? ->                  |
|            L1 DISTILLED JUDGE  (~8%, local classifier)       |
|                     -> still uncertain? ->                   |
|            L2 JURY  (~1%, model panel + human, async)        |
|                                    |                         |
|            POLICY ENGINE + ACTION GATE                       |
|            verdict -> allow / annotate / redact /            |
|                       hold / block / escalate                |
|                                    |                         |
|            LEDGER (append-only, hash-chained)               |
|                     -> FEEDBACK -> retrain L1               |
+-------------------------------------------------------------+
```

**Text is never held. Only side effects wait.**

## The path of one request

1. **Gateway** ([`app.py`](../clearance/app.py)) receives an OpenAI-shaped request.
   The `clearance` extension carries the policy pack, retrieved context, declared
   action, and conversation id. The upstream model is called through
   [`llm.py`](../clearance/llm.py) — the only module that touches the network,
   fixture-cache-first so offline replay is deterministic.

2. **L0 tripwire** ([`tiers/l0.py`](../clearance/tiers/l0.py)) runs all five
   detectors behind the `DetectorBackend` adapter
   ([`detectors/base.py`](../clearance/detectors/base.py)): groundedness,
   assertiveness, PII, patterns, injection. It computes the **confidence-evidence
   gap** and fuses everything, using the policy detector weights, into one scalar.
   100% of traffic, no LLM call, p95 ~1.5 ms.

3. **Escalation only when uncertain.** If the fused score lands in the policy
   uncertainty band `[l0_low, l0_high)`, L1 ([`tiers/l1.py`](../clearance/tiers/l1.py))
   — a calibrated classifier over L0 features — resolves it. Still uncertain and the
   L2 jury ([`tiers/l2.py`](../clearance/tiers/l2.py)) plus human queue take it, async.

4. **Accumulator** ([`agent/accumulator.py`](../clearance/agent/accumulator.py))
   carries conversation-level premise risk forward, so an action can inherit risk
   from an earlier unsupported claim.

5. **Gate** ([`policy/gate.py`](../clearance/policy/gate.py)) resolves
   `verdict = gate[band(fused, accumulated)][action.reversibility]`. This one line is
   the thesis: identical content risk, different verdict by reversibility.

6. **Latch** ([`latch.py`](../clearance/latch.py)) releases, rewrites, or drops the
   action; on timeout it applies the policy `fail_mode` (irreversible → fail-closed).

7. **Ledger** ([`ledger.py`](../clearance/ledger.py)) appends a hash-chained,
   policy-hash-stamped row. Escalations enter the feedback queue
   ([`feedback.py`](../clearance/feedback.py)), whose human labels retrain L1.

## Why the adapter seam is the whole point
Detection is a commodity with excellent vendors. CLEARANCE's contribution is the
decision layer, so every detector is swappable
([`detectors/registry.py`](../clearance/detectors/registry.py)) and one real vendor
stub ([`patronus_stub.py`](../clearance/detectors/backends/patronus_stub.py)) proves
it. Point groundedness at Patronus and nothing downstream changes.

## Offline determinism
`CLEARANCE_OFFLINE=1` (the default) forbids network calls. Corpus responses are
stored in the records themselves, so replay needs no model at all; the gateway
demos use committed fixtures in `corpus/fixtures/`. A genuine cache miss offline
raises a clear error instead of silently degrading.
