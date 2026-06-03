# ADR-002: Memory OS Deep Topic Study Doctrine

Status: Accepted
Date: 2026-06-01
Owner: User directive, Codex implementation

## Problem

The workspace must not behave like a generic oracle. The durable product value is the ability to study one bounded topic for one customer deeply, then operate quickly over local evidence and computed signals.

Generic LLM reasoning is not enough for this. It is brittle, hard to verify, expensive, and poor at repeatable probability, correlation, anomaly, and evidence accounting.

## Decision

Adopt an OS-inspired Memory OS doctrine:

- Hierarchical memory: root map, module map, exact evidence, raw logs only on demand.
- Addressable memory: nodes, edges, events, symbols, and manifests instead of anonymous chunks.
- Process isolation: untrusted or bulky data is inspected by narrow workers/tools; main reasoning receives validated summaries.
- Journaling: durable memory changes need evidence pointers and lifecycle status.
- Scheduler policy: repeated deterministic analysis becomes scripts/tools.
- Verification pattern: code/data claims require deterministic checks before trusted memory status.

Adopt deep topic study as a core analytics primitive:

- Input: one customer, one topic, bounded corpus.
- Output: evidence rows, probability-like signals, correlations, anomalies, caveats, confidence.
- Default command: `python -m scripts.analytics topic-study --customer <name> --topic <query>`.

## Rationale

This matches the project category: a governed intelligence workspace, not passive BI and not an unbounded chatbot. It also keeps sensitive and bulky data out of prompt context by default.

Deterministic analysis should run in Python/SQLite/Numpy. LLMs should interpret verified outputs and produce briefs, not invent metrics.

## Impact

Positive:
- Faster topic-specific analysis for pilot customers.
- Lower hallucination risk through evidence and caveats.
- Better reuse of local SQLite data and analytics scripts.
- Clear route for scheduled watchers and analyst workflows.

Risks:
- Keyword scoring is only a first pass; entity linking and semantic retrieval are still needed.
- Probability-like signals are empirical corpus ratios, not causal probabilities.
- Correlations can be misleading on small samples; caveats remain mandatory.

## Implementation

- `scripts/analytics/topic_study.py`
- `python -m scripts.analytics topic-study`
- `scratch/test_topic_study.py`
- `strategy.md` Memory OS and Deep Topic Study sections.

## Related

- `strategy.md`
- `llms.txt`
- `knowledge_base/docs/METRIC_DICTIONARY.md`
- `scripts/analytics/INDEX.md`
