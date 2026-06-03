# ADR-003: Data Access Experiment Loop

Status: Accepted
Date: 2026-06-01
Owner: User directive, Codex implementation

## Problem

The workspace needs to learn how to read many allowed data shapes over time. A single hardcoded ingestion path is too brittle. Some useful methods will be slow, partial, or experimental at first, but they can become reusable infrastructure if outcomes are measured.

This must stay governed. "Any data" means permitted, user-provided, licensed, official, or explicitly approved sources inside the source policy tiers. It does not mean bypassing access controls, collecting prohibited data, or handling secrets unsafely.

## Decision

Adopt a Data Access Experiment Loop:

1. Try multiple permitted data-access methods.
2. Accept slow or partial methods during exploration.
3. Log every method run as structured JSONL.
4. Rank methods by success rate, throughput, cost, errors, and sample count.
5. Promote reliable methods into reusable functions/connectors.
6. Periodically analyze experiment logs with local analytics tools.
7. Turn recurring insights into proposals, roadmap updates, or implementation tasks.

Default commands:

```bash
python -m scripts.analytics method-log --method-id rss_stdlib --source-type rss --dataset feed --policy-tier C --status success
python -m scripts.analytics method-rank --output markdown
python -m scripts.analytics method-review --output-path data/data_access_method_review.json
```

## Rationale

The system should improve its own data-reading capability empirically. Logs create the feedback needed for later schedulers, watchers, and connector selection.

The loop also prevents architectural guesswork. New complex systems can reference ranked existing methods instead of inventing one-off readers.

## Impact

Positive:
- Creates a reusable performance ledger for data-access methods.
- Gives future schedulers a quantitative basis for method selection.
- Enables periodic self-analysis and improvement proposals.
- Keeps experiments file-backed and migration-safe.

Risks:
- Poor logs produce misleading rankings.
- Method scores are empirical and context-specific.
- Slow or low-quality methods can consume time unless bounded by scheduler policy.

## Implementation

- `scripts/analytics/data_method_evaluator.py`
- `python -m scripts.analytics method-log`
- `python -m scripts.analytics method-rank`
- `python -m scripts.analytics method-review`
- `scratch/test_data_method_evaluator.py`

## Related

- `strategy.md`
- `scripts/analytics/topic_study.py`
- `news_scraper/connectors/`
- `agent_context/GLOBAL_ROADMAP.md`
