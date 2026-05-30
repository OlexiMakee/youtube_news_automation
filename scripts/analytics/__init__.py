"""
Analytics Suite — CLI-First Anomaly Detection & Metrics Engine

This package implements the analytics layer for YouTube News Automation.
All modules follow Decision-First, Local-First, CLI-First philosophy.

Architecture:
    cli.py                    → Click-based entry point (--help)
    anomaly_detector.py       → Z-score detection + caveat injection
    trend_analyzer.py         → Polynomial regression + forecasting
    metrics_engine.py         → KPI aggregation (median, Q1/Q3)
    brief_generator.py        → Markdown brief for newsroom

Usage:
    python -m scripts.analytics anomalies --channel <name> --output json
    python -m scripts.analytics trend --video <id> --forecast 7d
    python -m scripts.analytics kpi --channel <name>

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
    "brief_generator",
    "cli",
]
