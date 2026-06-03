"""
Analytics Suite — CLI-First Anomaly Detection & Metrics Engine

This package implements the analytics layer for YouTube News Automation.
All modules follow Decision-First, Local-First, CLI-First philosophy.

Architecture:
    cli.py                    → Click-based entry point (--help)
    anomaly_detector.py       → Z-score detection + caveat injection
    trend_analyzer.py         → Polynomial regression + forecasting
    metrics_engine.py         → KPI aggregation (median, Q1/Q3)
    topic_study.py            → Customer-scoped deep topic study
    phrase_performance.py     → Generic n-gram performance scoring
    data_method_evaluator.py  → Data-access method experiment logging/ranking
    brief_generator.py        → Markdown brief for newsroom

Usage:
    python -m scripts.analytics anomalies --channel <name> --output json
    python -m scripts.analytics trend --video <id> --forecast 7d
    python -m scripts.analytics kpi --channel <name>
    python -m scripts.analytics topic-study --customer <name> --topic <query>
    python -m scripts.analytics phrase-performance --channel <name>
    python -m scripts.analytics method-rank --output markdown
    python -m scripts.analytics method-review

For detailed usage, see:
    - README.md              → Full specification + examples
    - knowledge_base/docs/METRIC_DICTIONARY.md → Metric definitions + caveats
    - knowledge_base/docs/BEST_PRACTICES.md    → CLI patterns + testing

Author: Copilot Agent
Last Updated: 2026-05-30
Status: Scaffold ready for implementation
"""

__version__ = "0.1.0"
__all__ = [
    "anomaly_detector",
    "trend_analyzer",
    "metrics_engine",
    "topic_study",
    "phrase_performance",
    "data_method_evaluator",
    "brief_generator",
    "cli",
]
