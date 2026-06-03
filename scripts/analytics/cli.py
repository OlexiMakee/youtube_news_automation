"""
CLI Entry Point — Click-based Command Router

This module implements the command-line interface for analytics suite.
Every command supports --help and outputs structured results (JSON + Markdown).

Commands:
    anomalies   → Detect anomalous videos using Z-score
    trend       → Analyze trend using polynomial regression
    kpi         → Show KPI dashboard (medians, quartiles)
    topic-study → Deep customer-scoped topic study over local source data
    phrase-performance → Rank n-grams by metric performance
    method-log  → Append data-access method experiment result
    method-rank → Rank data-access methods from experiment logs
    method-review → Write latest data-access method ranking snapshot
    method-proposals → Convert repeated method-review insights into proposals
    brief       → Generate daily editorial brief

Implementation notes:
- All commands validate input via --help
- All commands output JSON + Markdown (Text-First DOM)
- All commands inject caveats automatically
- All commands support --verbose for debugging

Related:
    - scripts/analytics/README.md for full specification
    - knowledge_base/docs/BEST_PRACTICES.md for CLI patterns
    - knowledge_base/docs/METRIC_DICTIONARY.md for metrics

Author: Copilot Agent (scaffold) → Antigravity (implementation)
Status: Ready for implementation
"""

import click
import json
from pathlib import Path
from typing import Optional, Dict, Any


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """YouTube News Analytics Suite — Decision-First Metrics Engine.

    Use 'python -m scripts.analytics --help' for command list.
    Use 'python -m scripts.analytics <command> --help' for command help.
    """
    pass


@cli.command()
@click.option('--channel', required=True, help='Channel name (e.g., "uatv_english")')
@click.option('--output', type=click.Choice(['json', 'markdown', 'both']), 
              default='json', help='Output format')
@click.option('--threshold', type=float, default=2.5, 
              help='Z-score threshold for anomaly (default: 2.5)')
@click.option('--verbose', is_flag=True, help='Enable debug output')
def anomalies(channel: str, output: str, threshold: float, verbose: bool):
    """Detect anomalous videos using Z-score analysis.

    Returns a list of videos with |Z-score| > threshold, ranked by anomaly strength.
    Each anomaly includes caveats (data quality flags) and confidence score.

    Example:
        python -m scripts.analytics anomalies --channel uatv_english --output json
        python -m scripts.analytics anomalies --channel bbc_news --threshold 3.0 --verbose
    """
    try:
        from scripts.analytics.anomaly_detector import detect_anomalies, to_json, to_markdown
        anomalies_list, summary = detect_anomalies(channel, threshold=threshold, verbose=verbose)

        if output == 'json':
            click.echo(to_json(anomalies_list, summary))
        elif output == 'markdown':
            click.echo(to_markdown(anomalies_list, summary))
        elif output == 'both':
            click.echo(to_markdown(anomalies_list, summary))
            click.echo("\n---\n")
            click.echo(to_json(anomalies_list, summary))
    except Exception as e:
        if verbose:
            import traceback
            click.echo(traceback.format_exc(), err=True)
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.option('--video', required=True, help='Video ID')
@click.option('--forecast', type=click.Choice(['24h', '7d', '30d']),
              default='7d', help='Forecast period')
@click.option('--output', type=click.Choice(['json', 'markdown']),
              default='json', help='Output format')
@click.option('--db-path', default='data/youtube_news.db', help='Path to SQLite database')
@click.option('--verbose', is_flag=True, help='Enable debug output')
def trend(video: str, forecast: str, output: str, db_path: str, verbose: bool):
    """Analyze trend using polynomial regression + forecast.

    Fits 2nd-order polynomial to 7-day view history, extrapolates to future.
    Includes confidence intervals and error metrics (R²).

    Example:
        python -m scripts.analytics trend --video abc123 --forecast 7d
    """
    try:
        from scripts.analytics.trend_analyzer import analyze_trend, to_json, to_markdown
        trend_obj = analyze_trend(video, db_path=db_path, verbose=verbose)

        if output == 'json':
            click.echo(to_json(trend_obj))
        elif output == 'markdown':
            click.echo(to_markdown(trend_obj, forecast_period=forecast))
    except Exception as e:
        if verbose:
            import traceback
            click.echo(traceback.format_exc(), err=True)
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.option('--channel', required=True, help='Channel name')
@click.option('--output', type=click.Choice(['json', 'markdown']),
              default='json', help='Output format')
@click.option('--db-path', default='data/youtube_news.db', help='Path to SQLite database')
@click.option('--verbose', is_flag=True, help='Enable debug output')
def kpi(channel: str, output: str, db_path: str, verbose: bool):
    """Show KPI dashboard for channel.

    Displays:
    - Median views (last 7 days)
    - Q1/Q3 range (interquartile range)
    - Total videos
    - Engagement rate

    Example:
        python -m scripts.analytics kpi --channel uatv_english
    """
    try:
        from scripts.analytics.metrics_engine import calculate_kpi, to_json, to_markdown
        kpi_obj = calculate_kpi(channel, db_path=db_path, verbose=verbose)

        if output == 'json':
            click.echo(to_json(kpi_obj))
        elif output == 'markdown':
            click.echo(to_markdown(kpi_obj))
    except Exception as e:
        if verbose:
            import traceback
            click.echo(traceback.format_exc(), err=True)
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@cli.command("topic-study")
@click.option('--topic', required=True, help='Topic/query to study deeply')
@click.option('--customer', required=True, help='Customer or workspace label for the study')
@click.option('--channel', type=str, help='Optional channel name, handle, or ID')
@click.option('--days', type=int, default=90, help='Lookback window in days')
@click.option('--evidence-limit', type=int, default=12, help='Maximum evidence rows to return')
@click.option('--anomaly-threshold', type=float, default=2.0, help='Z-score threshold for topic anomalies')
@click.option('--output', type=click.Choice(['json', 'markdown', 'both']),
              default='json', help='Output format')
@click.option('--db-path', default='data/youtube_news.db', help='Path to SQLite database')
@click.option('--verbose', is_flag=True, help='Enable debug output')
def topic_study(
    topic: str,
    customer: str,
    channel: Optional[str],
    days: int,
    evidence_limit: int,
    anomaly_threshold: float,
    output: str,
    db_path: str,
    verbose: bool,
):
    """Study one topic deeply for one customer over a bounded local corpus.

    Computes relevance-weighted probabilities, attention share, correlations,
    anomalies, evidence rows, caveats, and a confidence score.
    """
    try:
        from scripts.analytics.topic_study import study_topic, to_json, to_markdown
        report = study_topic(
            topic=topic,
            customer=customer,
            channel=channel,
            days=days,
            db_path=db_path,
            evidence_limit=evidence_limit,
            anomaly_threshold=anomaly_threshold,
            verbose=verbose,
        )

        if output == 'json':
            click.echo(to_json(report))
        elif output == 'markdown':
            click.echo(to_markdown(report))
        elif output == 'both':
            click.echo(to_markdown(report))
            click.echo("\n---\n")
            click.echo(to_json(report))
    except Exception as e:
        if verbose:
            import traceback
            click.echo(traceback.format_exc(), err=True)
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@cli.command("phrase-performance")
@click.option('--channel', type=str, help='Optional YouTube channel name, handle, or ID')
@click.option('--days', type=int, help='Optional lookback window in days')
@click.option('--text-fields', default='title', help='Comma-separated text fields, e.g. title,thumbnail_text')
@click.option('--metrics', default='view_count,like_count,comment_count,views_7d,engagement_rate', help='Comma-separated metric fields')
@click.option('--ngram-min', type=int, default=1, help='Minimum n-gram size')
@click.option('--ngram-max', type=int, default=4, help='Maximum n-gram size')
@click.option('--min-count', type=int, default=3, help='Minimum records containing phrase')
@click.option('--limit', type=int, default=25, help='Maximum rows to return')
@click.option('--sort-metric', default='view_count', help='Metric to sort by')
@click.option('--sort-stat', type=click.Choice(['median', 'mean', 'total', 'lift', 'record_count']), default='median', help='Statistic to sort by')
@click.option('--direction', type=click.Choice(['best', 'worst']), default='best', help='Sort direction')
@click.option('--output', type=click.Choice(['json', 'markdown']), default='json', help='Output format')
@click.option('--db-path', default='data/youtube_news.db', help='Path to SQLite database')
def phrase_performance(
    channel: Optional[str],
    days: Optional[int],
    text_fields: str,
    metrics: str,
    ngram_min: int,
    ngram_max: int,
    min_count: int,
    limit: int,
    sort_metric: str,
    sort_stat: str,
    direction: str,
    output: str,
    db_path: str,
):
    """Rank 1/2/3/4-word phrases by views, likes, comments, growth, or engagement."""
    try:
        from scripts.analytics.phrase_performance import analyze_youtube_phrases, to_json, to_markdown
        report = analyze_youtube_phrases(
            db_path=db_path,
            channel=channel,
            days=days,
            text_fields=_csv_list(text_fields),
            metric_fields=_csv_list(metrics),
            ngram_min=ngram_min,
            ngram_max=ngram_max,
            min_count=min_count,
            limit=limit,
            sort_metric=sort_metric,
            sort_stat=sort_stat,
            direction=direction,
        )
        if output == 'json':
            click.echo(to_json(report))
        else:
            click.echo(to_markdown(report))
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@cli.command("method-log")
@click.option('--method-id', required=True, help='Stable method identifier')
@click.option('--source-type', required=True, help='Source type, e.g. rss, youtube, csv, html')
@click.option('--dataset', required=True, help='Dataset/source label without secrets')
@click.option('--policy-tier', required=True, help='Governance policy tier A-E; Tier X is blocked')
@click.option('--status', required=True, type=click.Choice(['success', 'partial', 'failed', 'blocked']), help='Experiment outcome')
@click.option('--records-seen', type=int, default=0, help='Records discovered')
@click.option('--records-read', type=int, default=0, help='Records successfully read')
@click.option('--duration-ms', type=int, default=0, help='Experiment duration in milliseconds')
@click.option('--error-count', type=int, default=0, help='Non-secret error count')
@click.option('--bytes-read', type=int, default=0, help='Bytes read')
@click.option('--cost-estimate', type=float, default=0.0, help='Estimated cost')
@click.option('--notes', default='', help='Short non-secret notes')
@click.option('--log-path', default='data/data_access_experiments.jsonl', help='JSONL log path')
def method_log(
    method_id: str,
    source_type: str,
    dataset: str,
    policy_tier: str,
    status: str,
    records_seen: int,
    records_read: int,
    duration_ms: int,
    error_count: int,
    bytes_read: int,
    cost_estimate: float,
    notes: str,
    log_path: str,
):
    """Append one governed data-access method experiment to the JSONL log."""
    try:
        from scripts.analytics.data_method_evaluator import append_experiment, make_experiment
        experiment = make_experiment(
            method_id=method_id,
            source_type=source_type,
            dataset=dataset,
            policy_tier=policy_tier,
            status=status,
            records_seen=records_seen,
            records_read=records_read,
            duration_ms=duration_ms,
            error_count=error_count,
            bytes_read=bytes_read,
            cost_estimate=cost_estimate,
            notes=notes,
        )
        append_experiment(experiment, log_path=log_path)
        click.echo("logged")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


def _csv_list(value: str):
    return [item.strip() for item in str(value or "").split(",") if item.strip()]


@cli.command("method-rank")
@click.option('--log-path', default='data/data_access_experiments.jsonl', help='JSONL log path')
@click.option('--min-runs', type=int, default=1, help='Minimum runs per method')
@click.option('--output', type=click.Choice(['json', 'markdown']), default='json', help='Output format')
def method_rank(log_path: str, min_runs: int, output: str):
    """Rank governed data-access methods from experiment logs."""
    try:
        from scripts.analytics.data_method_evaluator import analyze_log, to_json, to_markdown
        report = analyze_log(log_path=log_path, min_runs=min_runs)
        if output == 'json':
            click.echo(to_json(report))
        elif output == 'markdown':
            click.echo(to_markdown(report))
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@cli.command("method-review")
@click.option('--log-path', default='data/data_access_experiments.jsonl', help='JSONL log path')
@click.option('--output-path', default='data/data_access_method_review.json', help='Snapshot JSON output path')
@click.option('--min-runs', type=int, default=1, help='Minimum runs per method')
def method_review(log_path: str, output_path: str, min_runs: int):
    """Write the latest data-access method ranking snapshot for scheduled review."""
    try:
        from scripts.analytics.data_method_evaluator import analyze_log, write_review_snapshot
        report = analyze_log(log_path=log_path, min_runs=min_runs)
        write_review_snapshot(report, output_path=output_path)
        click.echo(output_path)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@cli.command("method-proposals")
@click.option('--snapshot-path', default='data/data_access_method_review.json', help='Method-review snapshot path')
@click.option('--proposals-path', default='agent_proposals/admin_proposals.jsonl', help='Admin proposals JSONL path')
@click.option('--events-path', default='memory/events.jsonl', help='Memory lifecycle events JSONL path')
@click.option('--min-runs-for-proposal', type=int, default=3, help='Minimum repeated runs before proposal generation')
@click.option('--write', is_flag=True, help='Append new proposals. Dry-run by default.')
@click.option('--lifecycle-event', is_flag=True, help='Append a Memory OS lifecycle event when writing.')
def method_proposals(
    snapshot_path: str,
    proposals_path: str,
    events_path: str,
    min_runs_for_proposal: int,
    write: bool,
    lifecycle_event: bool,
):
    """Convert repeated method-review insights into admin proposals."""
    try:
        from scripts.analytics.method_review_proposals import generate_method_review_proposals
        result = generate_method_review_proposals(
            snapshot_path=snapshot_path,
            proposals_path=proposals_path,
            events_path=events_path,
            min_runs_for_proposal=min_runs_for_proposal,
            write=write,
            lifecycle_event=lifecycle_event,
        )
        click.echo(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.option('--channel', type=str, help='Specific channel, or all if omitted')
@click.option('--output-file', type=click.Path(), help='Save to file (optional)')
def brief(channel: Optional[str], output_file: Optional[str]):
    """Generate daily editorial brief for newsroom.
    
    Creates Markdown brief with:
    - Top 3 viral videos (Z-score > 2.5)
    - Top 3 trending topics
    - Publishing recommendations
    - Data quality notes
    
    Example:
        python -m scripts.analytics brief --channel bbc_news > daily_brief.md
        python -m scripts.analytics brief > all_channels_brief.md
    """
    # Brief generator is scheduled for Sprint 3.
    click.echo("Brief generator is scheduled for Sprint 3.")


if __name__ == '__main__':
    cli()
