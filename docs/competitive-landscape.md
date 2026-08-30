# Competitive landscape

The 2026 guardrail market is crowded and good. CLEARANCE does not compete on
detection. It sits **above** detection as the decision layer, and it treats
every incumbent as a potential backend rather than a rival.

## Who does what today

| Vendor / project | Strength | Layer |
|---|---|---|
| **Lakera**, **OpenAI Guardrails**, **Future AGI Protect** | input rails, prompt-injection, sub-50ms | input |
| **Patronus**, **Galileo**, **Bedrock Guardrails**, **Azure Content Safety** | groundedness, hallucination & toxicity scoring | output content |
| **NeMo Guardrails** | dialogue/state control, programmable rails | conversation |
| **Bifrost**, **Future AGI Agent Command Center** | OpenAI-compatible gateway, policy-as-config, tool-call placement | gateway |

These are strong products. If the contribution were "a better hallucination
score," that argument is already lost.

## What CLEARANCE does differently — three bullets, above the fold

1. **Reversibility-indexed verdicts.** Incumbents decide on *content risk*,
   scoped by endpoint at best. CLEARANCE decides on
   `(risk, reversibility of the specific action class)`. **Identical response
   text produces two verdicts** — annotate as a draft note, block-and-escalate
   as a refund. Nobody ships the paired verdict. It is our M3 acceptance gate
   and the first thing the demo shows.

2. **Cost-proportional coverage that improves.** Incumbents sample to control
   cost, trading away coverage. CLEARANCE keeps **100% coverage at L0** (no LLM
   call) and *escalates spend only in the uncertainty band* — and the expensive
   tier trains the cheap one, so paid-tier traffic falls week over week
   (~12% → <2%) with recall held.

3. **The operating point as a signed governance artifact.** The threshold set is
   not an engineering default buried in code; it is chosen by a named risk owner,
   dated, rationalised, and hashed into every ledger row (`policy_hash`). Moving
   the slider in the tuning console *is* re-signing the operating point.

## The adapter seam (why "just use Lakera" misses the point)

Every detector implements one `DetectorBackend` Protocol
([`clearance/detectors/base.py`](../clearance/detectors/base.py)). The shipped
local detectors are deliberately thin so the repo runs offline with zero keys —
CLEARANCE makes **no claim** to out-detect Patronus or Lakera. The interface is
built so those tools *become the backend*:

```yaml
detectors:
  groundedness: { backend: patronus, enabled: true }   # one-line swap
```

[`clearance/detectors/backends/patronus_stub.py`](../clearance/detectors/backends/patronus_stub.py)
is a real, type-checking implementation of that Protocol (config-only, no key
required to read it). It proves the seam is not a slide: point groundedness at
Patronus and the tiers, policy engine, gate, latch and ledger are untouched.

**Positioning in one line:** the incumbents decide *whether the text is risky*;
CLEARANCE decides *whether to let the action happen* — and it will happily use
an incumbent to make the first call.
