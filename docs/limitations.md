# Limitations

Written down deliberately. Each item defuses a question the panel would otherwise
ask, and none of them is softened.

- **Entropy term of the CEG.** Token logprobs are unavailable on most commercial
  APIs, so the CEG's entropy term falls back to semantic self-consistency over a
  small resample (n=3). Because resampling costs money it runs **only inside the
  uncertainty band**, never on all traffic. Offline it reads resample fixtures or a
  simulated `self_consistency` field, and defaults to 0 on a miss — so the shipped
  CEG runs on `assertiveness × ungroundedness` alone unless that signal is present.

- **L1 is a classifier, not a distilled LLM.** L1 is a calibrated logistic model
  over L0 feature vectors. The learning loop is real (L2/human labels retrain it and
  the paid-tier fraction genuinely shrinks); the tier is simplified. The four-week
  curve uses a documented label-accrual schedule, not a live month of traffic.

- **Local detector backends are deliberately thin.** CLEARANCE does not claim
  detection accuracy competitive with Patronus or Lakera. It claims the decision
  layer above them; the adapter interface exists so those tools can be the backend.
  Offline, embeddings fall back to a hashed bag-of-words vector and NER to regex —
  functional and deterministic, but weaker than `all-MiniLM-L6-v2` / spaCy.

- **The corpus is synthetic and single-annotator.** FP and FN rates are **relative
  measures for comparing operating points**, not absolute accuracy. Genuinely
  ambiguous cases are excluded because one annotator cannot adjudicate them credibly.
  Perfect precision at the default point reflects engineered separability, not a
  claim about production traffic.

- **Groundedness requires retrieval.** For open-ended generation with no retrievable
  source, the CEG degrades to assertiveness plus self-consistency and is materially
  weaker. It measures support against the *retrieved context*, not truth.

- **The conversation accumulator does not do causal tracing.** It carries a decaying
  scalar of unsupported-premise risk forward. It shows *that* prior risk contaminated
  a later action, not a proof of *which* earlier claim did.

- **The L2 judge is itself an LLM and is attackable.** Mitigation is delimiter-fenced,
  data-only input (see [`threat-model.md`](threat-model.md)), not a proof.

- **Counterfactual / bias replay (Tier C, not shipped here) detects outcome divergence
  under attribute substitution. It is not a fairness certification** and will miss
  proxy discrimination through correlated features.

- **Latency figures are single-machine, local measurements**, not production load
  numbers. p95 ~1.5 ms is L0 on one core with the fallback embedding backend.

- **Fail-mode is a policy choice with real consequences.** Irreversible actions
  fail-closed on a latch timeout; a checker outage therefore blocks refunds until it
  recovers. That is the intended trade for high-blast-radius actions, stated loudly
  rather than hidden.
