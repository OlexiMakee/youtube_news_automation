# YouTube News Automation — Governed Autonomous Media Intelligence Workspace

**Production-grade AI & Data Analytics platform built for international multilingual newsrooms (deployed across English, Hungarian/Magyar, French, German, Polish, Spanish, Arabic, and Ukrainian broadcast operations).**

Powered by **[Memory OS](https://github.com/OlexiMakee/memory_os_public)** for persistent multi-agent knowledge graphs, deterministic statistical analytics, and automated editorial briefing pipelines.

---

## 📊 Production Scale & Real-World Impact
- **59 International News Channels Monitored:** Automated multi-profile ingestion across global and regional broadcasters.
- **38,430+ Indexed Videos & Metadata Records:** Stored in local-first **SQLite WAL** (`data/youtube_news.db`) with cloud synchronization to **Neon PostgreSQL**.
- **7,051,171 Extracted N-Gram Phrases (`video_phrases`):** High-speed 1–4 word phrase lift and viral headline performance scoring.
- **5-Stage Automated Editorial Briefings:** Generates daily data-backed competitive analyses, viral anomaly alerts, title/hook recommendations, and broadcast scripts (`SKILL_uatv_english_daily_brief.md`, `SKILL_uatv_magyarul_daily_brief.md`).

---

## ⚙️ Core Architecture & Engineering Highlights

```text
[ Multi-Profile YouTube Scrapers & Governed Connectors (Tiers A–E) ]
                                │
                                ▼
       [ SQLite WAL (38.4k Videos / 7.05M Phrases) ⇄ Neon PostgreSQL ]
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
[ Deterministic CLI ]   [ Memory OS Engine ]    [ Flask + D3.js UI ]
- Z-Score Anomalies     - Dev Graph (JSONL/FTS5)- Tri-View D3 Graph
- Poly Trend Forecast   - Isolated User-OS DB   - Role RBAC (Reader/Analyst/Admin)
- N-Gram Lift Engine    - Multi-Agent Swarm     - Scheduled Watchers & Review Queue
- Topic Correlation     - Cloud LLM Rotation    - Embedded xterm.js Operator Shell
```

### 1. Deterministic-First Analytics Suite (`scripts/analytics/`)
To eliminate LLM hallucinations on numerical media data, all statistical computations run deterministically in Python/SQLite before AI synthesis:
- **`anomaly_detector.py`:** Rolling Z-score viral outlier detection (`|z| > 2.5`) with automatic injection of 16 statistical caveat classes (`ZERO_VARIANCE`, `SMALL_SAMPLE`, `DATA_VOLATILITY`) and calibrated `confidence_score`.
- **`phrase_performance.py`:** Evaluates 1/2/3/4-gram headline phrases by median, Q1/Q3 interquartile range, and lift over corpus median across 7M+ phrase occurrences.
- **`trend_analyzer.py` & `topic_study.py`:** Polynomial regression view forecasting, momentum ratios, and cross-channel topic correlation.
- **`data_method_evaluator.py`:** Self-optimizing telemetry loop ranking ingestion methods by throughput, error rate, and cost per record.

### 2. Dual-Layer Memory OS Integration (`memory_os_local/`)
- **Developer Control Plane:** Tracks architectural decisions, AST symbol graphs, task capsules, and multi-agent handoffs (`Antigravity`, `Claude Code`, `Codex`).
- **User-Facing Memory OS (`User-OS`):** Strictly isolated SQLite memory graph allowing editors and producers to teach the assistant narrative trends, guest backgrounds, and editorial rules with zero codebase leakage.

### 3. Governed Flask Web Application (`app/` & `static/js/`)
- **Blueprints:** Modular REST API (`actions`, `analytics`, `briefs`, `charts`, `entities`, `governance`, `scraper`, `stats`, `videos`).
- **Interactive Visualization:** **D3.js Tri-View Graph** (`graph-view.js`, `timeline-view.js`, `table-view.js`), Chart.js KPI dashboards, and live `Scheduled Watchers` + `Human Review Queue`.
- **Cloud LLM Rotation (`cloud_rotation.py`):** Automatic failover across Gemini, OpenRouter, Groq, and cloud Ollama endpoints with quota harvesting and rate-limit protection.

---

## 🚀 Quickstart

```bash
# 1. Run deterministic analytics CLI
python -m scripts.analytics kpi --channel uatv_english
python -m scripts.analytics anomalies --channel uatv_english --threshold 2.5 --output markdown
python -m scripts.analytics phrase-performance --channel "UATV English" --ngram-min 2 --ngram-max 4
python -m scripts.analytics topic-study --customer newsroom --topic "air defense" --output markdown

# 2. Launch the Governed Intelligence Dashboard
python web_app.py
# Open http://127.0.0.1:5001

# 3. Run the 40+ automated test suite
pytest tests/ -q
```
