# Corpus: labelling protocol, base rate, provenance

**Read this before trusting any number computed against the corpus.**

## What this is
A **synthetic, single-annotator** corpus of ~150 records across three use cases,
generated deterministically by [`scripts/seed_corpus.py`](../scripts/seed_corpus.py)
(seed `20260901`). Declaring it synthetic is a strength, not a hedge: the FP and
FN rates it yields are **relative measures for comparing operating points**, not
absolute accuracy claims about production traffic.

## Base rate
**~20% risky / ~80% benign** (21.2% exactly, including the borderline stress
set). A 50/50 corpus flatters a guardrail system and any experienced reviewer
notices. The exact split is printed when you run the seed script and by
`scripts/run_replay.py`.

| file | records | risky | use case |
|---|---|---|---|
| `support.jsonl`     | 45 | 9  | support-assistant |
| `copilot.jsonl`     | 45 | 9  | internal-copilot |
| `decision.jsonl`    | 45 | 9  | decision-support |
| `adversarial.jsonl` | 15 | 3  | injection + assertive-but-grounded |
| `borderline.jsonl`  | 10 | 4  | **the transition band** the tuning slider trades across |
| `paired.jsonl`      | 2  | 2  | **the crown jewel** (one text, two actions) |
| `agentic.jsonl`     | 6 turns | — | multi-turn compounding |

`borderline.jsonl` is what makes the tuning-console PR curve a real curve rather
than a step: confident-but-benign records (a false-positive risk if you chase
recall) and subtle, hedged fabrications (a false-negative risk if you tighten
too far). At the default operating point precision is 1.00 and recall ~0.9; the
slider trades one for the other.

## Annotation model
Each record carries a `gold` block:

```json
"gold": { "risky": true, "categories": ["hallucination","privacy"],
          "expected_verdict": "block_escalate", "note": "why" }
```

- `categories` is a **list that maps to a set** in code and is **overlapping,
  never exclusive**. A fabricated salary about a named colleague is labelled
  BOTH `hallucination` and `privacy` — the brief is explicit that these risks
  co-occur, and the system is built to surface them together.
- `expected_verdict` is the verdict under the record's **default** policy pack
  and default action. Paired records add `gold_b` for the second action.

## How ambiguity is handled
The generator only labels a record `risky` when it deliberately plants a signal
the shipped local detectors can see (ungrounded claim, fabricated PII, a policy
pattern, or an injected instruction). Benign records are grounded in their
`retrieved` context and hedged. Genuinely ambiguous cases are **not** included,
because a single annotator cannot adjudicate them credibly — this is a stated
limitation, not an oversight (see [`docs/limitations.md`](../docs/limitations.md)).

## The `self_consistency` field
Optional, `0..1`. Stands in for the resample-based entropy term of the CEG when
token logprobs are unavailable. Where present it is a **simulated** signal; the
shipped detectors do not require it, and the default corpus leaves it unset so
the CEG runs on groundedness × assertiveness alone. Documented in limitations.

## Regenerating
```
python scripts/seed_corpus.py
```
Deterministic: the same seed reproduces byte-identical files.
