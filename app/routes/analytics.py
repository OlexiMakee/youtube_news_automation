from flask import Blueprint, jsonify, request
from dataclasses import asdict
from app.services.data_method_review import review_data_methods, write_data_method_review_snapshot
from app.services.rbac import require_admin as _admin_required
from app.state import root_dir

analytics_bp = Blueprint('analytics', __name__)

@analytics_bp.route('/api/analytics/anomalies', methods=['GET'])
@_admin_required
def get_anomalies():
    """Detect anomalous videos using Z-score analysis."""
    channel = request.args.get("channel", "").strip()
    if not channel:
        return jsonify({"error": "channel parameter is required."}), 400
    
    try:
        threshold = float(request.args.get("threshold", 2.5))
    except ValueError:
        return jsonify({"error": "threshold must be a float number."}), 400

    output_format = request.args.get("output", "json").strip().lower()

    try:
        from scripts.analytics.anomaly_detector import detect_anomalies, to_json, to_markdown
        anomalies_list, summary = detect_anomalies(channel, threshold=threshold, verbose=False)
        
        if output_format == "markdown":
            return to_markdown(anomalies_list, summary), 200, {"Content-Type": "text/markdown; charset=utf-8"}
        elif output_format == "both":
            return jsonify({
                "markdown": to_markdown(anomalies_list, summary),
                "anomalies": [asdict(a) for a in anomalies_list],
                "summary": summary
            })
        else:
            return to_json(anomalies_list, summary), 200, {"Content-Type": "application/json; charset=utf-8"}
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@analytics_bp.route('/api/analytics/data-methods', methods=['GET'])
@_admin_required
def get_data_method_review():
    """Rank data-access methods from file-backed experiment logs."""
    try:
        min_runs = int(request.args.get("min_runs", 1))
    except ValueError:
        return jsonify({"error": "min_runs must be an integer."}), 400

    try:
        return jsonify({
            "ok": True,
            "review": review_data_methods(root_dir, min_runs=min_runs),
        })
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@analytics_bp.route('/api/analytics/data-methods/review', methods=['POST'])
@_admin_required
def post_data_method_review():
    """Write a file-backed data-access method review snapshot."""
    payload = request.get_json(silent=True) or {}
    try:
        min_runs = int(payload.get("min_runs", request.args.get("min_runs", 1)))
    except ValueError:
        return jsonify({"error": "min_runs must be an integer."}), 400

    try:
        return jsonify({
            "ok": True,
            "review": write_data_method_review_snapshot(root_dir, min_runs=min_runs),
        })
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@analytics_bp.route('/api/analytics/data-methods/proposals', methods=['POST'])
@_admin_required
def post_data_method_proposals():
    """Run method proposals generation and write back new active proposals."""
    from scripts.analytics.method_review_proposals import generate_method_review_proposals
    import os

    snapshot_path = os.path.join(root_dir, "data", "data_access_method_review.json")
    proposals_path = os.path.join(root_dir, "agent_proposals", "admin_proposals.jsonl")
    events_path = os.path.join(root_dir, "memory", "events.jsonl")

    try:
        result = generate_method_review_proposals(
            snapshot_path=snapshot_path,
            proposals_path=proposals_path,
            events_path=events_path,
            write=True,
            lifecycle_event=True
        )
        return jsonify({"ok": True, **result})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
