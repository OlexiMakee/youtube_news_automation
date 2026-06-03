from flask import Blueprint, jsonify, request

from app.services.governance import (
    ConnectorValidationError,
    GovernanceMigrationRequired,
    connector_metadata,
    create_source,
    list_audit_events,
    list_connector_runs,
    list_evidence_links,
    list_source_records,
    list_source_credential_status,
    list_sources,
    policy_summary,
    registry_readiness,
    run_source_ingestion,
)
from app.services.rbac import require_admin as _admin_required
from app.state import get_entitlement_state, root_dir


governance_bp = Blueprint("governance", __name__)


@governance_bp.route("/api/governance/policy", methods=["GET"])
@_admin_required
def get_governance_policy():
    """Return non-secret source policy tiers and registry readiness."""
    return jsonify({"ok": True, **policy_summary(root_dir)})


@governance_bp.route("/api/governance/readiness", methods=["GET"])
@_admin_required
def get_governance_readiness():
    """Dry-run governance migration readiness without mutating the database."""
    return jsonify({"ok": True, **registry_readiness(root_dir)})


@governance_bp.route("/api/sources", methods=["GET"])
@_admin_required
def get_sources():
    """List registered governed sources when the migration is applied."""
    try:
        data = list_sources(root_dir)
        return jsonify({"ok": True, **data})
    except GovernanceMigrationRequired as exc:
        return jsonify({
            "ok": True,
            "registry_ready": False,
            "sources": [],
            "message": str(exc),
        })


@governance_bp.route("/api/connector-runs", methods=["GET"])
@_admin_required
def get_connector_runs():
    """List recent connector runs when the governance registry is available."""
    try:
        data = list_connector_runs(root_dir, request.args.get("limit"))
        return jsonify({"ok": True, **data})
    except GovernanceMigrationRequired as exc:
        return jsonify({
            "ok": True,
            "registry_ready": False,
            "connector_runs": [],
            "message": str(exc),
        })


@governance_bp.route("/api/source-records", methods=["GET"])
@_admin_required
def get_source_records():
    """List normalized source record previews without exposing raw metadata."""
    try:
        data = list_source_records(
            root_dir,
            request.args.get("limit"),
            request.args.get("source_id"),
        )
        return jsonify({"ok": True, **data})
    except GovernanceMigrationRequired as exc:
        return jsonify({
            "ok": True,
            "registry_ready": False,
            "source_records": [],
            "message": str(exc),
        })
    except ValueError:
        return jsonify({"error": "source_id must be an integer."}), 400


@governance_bp.route("/api/audit-events", methods=["GET"])
@_admin_required
def get_audit_events():
    """List recent audit events without exposing raw metadata payloads."""
    try:
        data = list_audit_events(root_dir, request.args.get("limit"))
        return jsonify({"ok": True, **data})
    except GovernanceMigrationRequired as exc:
        return jsonify({
            "ok": True,
            "registry_ready": False,
            "audit_events": [],
            "message": str(exc),
        })


@governance_bp.route("/api/evidence-links", methods=["GET"])
@_admin_required
def get_evidence_links():
    """List evidence link previews without exposing full generated output text."""
    try:
        data = list_evidence_links(root_dir, request.args.get("limit"))
        return jsonify({"ok": True, **data})
    except GovernanceMigrationRequired as exc:
        return jsonify({
            "ok": True,
            "registry_ready": False,
            "evidence_links": [],
            "message": str(exc),
        })


# TODO: Add credentials input/edit UI only after secret storage design is approved (PR link needed).
@governance_bp.route("/api/source-credentials/status", methods=["GET"])
@_admin_required
def get_source_credential_status():
    """List source credential status without exposing secret references."""
    try:
        data = list_source_credential_status(root_dir, request.args.get("limit"))
        return jsonify({"ok": True, **data})
    except GovernanceMigrationRequired as exc:
        return jsonify({
            "ok": True,
            "registry_ready": False,
            "source_credentials": [],
            "message": str(exc),
        })


@governance_bp.route("/api/sources", methods=["POST"])
@_admin_required
def post_source():
    """Create a governed source record after registry tables exist."""
    try:
        source = create_source(root_dir, request.get_json(silent=True) or {})
        return jsonify({"ok": True, "source": source}), 201
    except GovernanceMigrationRequired as exc:
        return jsonify({"error": str(exc), "registry_ready": False}), 409
    except (TypeError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400


@governance_bp.route("/api/sources/<int:source_id>", methods=["DELETE"])
@_admin_required
def delete_source_route(source_id):
    """Delete a governed source record."""
    try:
        from app.services.governance import delete_source
        success = delete_source(root_dir, source_id)
        if success:
            return jsonify({"ok": True, "message": "Source deleted successfully."})
        return jsonify({"error": "Source not found."}), 404
    except GovernanceMigrationRequired as exc:
        return jsonify({"error": str(exc), "registry_ready": False}), 409
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@governance_bp.route("/api/source-credentials", methods=["POST"])
@_admin_required
def post_source_credential():
    """Store encrypted secret for a source."""
    payload = request.get_json(silent=True) or {}
    source_id = payload.get("source_id")
    secret_value = payload.get("secret_value")
    
    if not source_id or not secret_value:
        return jsonify({"error": "source_id and secret_value are required."}), 400
        
    try:
        from app.services.credentials import store_credential
        # Check source exists
        from app.services.governance import _connect
        conn = _connect(root_dir)
        try:
            row = conn.execute("SELECT 1 FROM sources WHERE id = ?", (source_id,)).fetchone()
            if not row:
                return jsonify({"error": "Source not found."}), 404
        finally:
            conn.close()
            
        store_credential(int(source_id), secret_value, root_dir)
        return jsonify({"ok": True, "has_secret_ref": True}), 201
    except GovernanceMigrationRequired as exc:
        return jsonify({"error": str(exc), "registry_ready": False}), 409
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@governance_bp.route("/api/governance/entitlements", methods=["GET"])
@_admin_required
def get_governance_entitlements():
    """Return active progressive entitlement flags."""
    return jsonify({"ok": True, "entitlements": get_entitlement_state()})


@governance_bp.route("/api/source-connectors", methods=["GET"])
@_admin_required
def get_source_connectors():
    """Return safe connector metadata for ingestion UI."""
    return jsonify({"ok": True, **connector_metadata()})


@governance_bp.route("/api/sources/ingest", methods=["POST"])
@_admin_required
def post_source_ingest():
    """Run a governed connector preview, optionally persisting source records."""
    if not get_entitlement_state().get("operator_runtime", False):
        return jsonify({
            "error": "operator_runtime entitlement required.",
            "required_entitlement": "operator_runtime",
        }), 403

    payload = _ingest_payload_from_request()
    try:
        result = run_source_ingestion(root_dir, payload)
        return jsonify({"ok": True, **result})
    except GovernanceMigrationRequired as exc:
        return jsonify({"error": str(exc), "registry_ready": False}), 409
    except (ConnectorValidationError, TypeError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


def _ingest_payload_from_request():
    if request.files:
        payload = dict(request.form.items())
        upload = request.files.get("file")
        if upload is not None:
            text = upload.read().decode("utf-8", errors="replace")
            input_payload = payload.get("input")
            if isinstance(input_payload, dict):
                input_data = input_payload
            else:
                input_data = {}
            input_data["text"] = text
            if "fmt" not in input_data and upload.filename:
                input_data["fmt"] = upload.filename.rsplit(".", 1)[-1].lower()
            payload["input"] = input_data
        return payload
    return request.get_json(silent=True) or {}
