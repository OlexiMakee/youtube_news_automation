from flask import Blueprint, request, jsonify, current_app
from app.services.rbac import require_admin
from app.services.briefs import BriefsService
from app.services.governance import GovernanceMigrationRequired, add_audit_event
from app.state import root_dir
import traceback

briefs_bp = Blueprint("briefs", __name__, url_prefix="/api/briefs")

@briefs_bp.route("/generate", methods=["POST"])
@require_admin
def generate_brief():
    date_str = request.args.get("date")
    if not date_str:
        return jsonify({"error": "date parameter required (YYYY-MM-DD)"}), 400
    sources_param = request.args.get("sources")
    source_ids = None
    if sources_param:
        try:
            source_ids = [int(s) for s in sources_param.split(",")]
        except ValueError:
            return jsonify({"error": "sources parameter must be comma-separated integers"}), 400

    try:
        result = BriefsService.generate_daily_brief(root_dir, date_str, source_ids)
        return jsonify({"ok": True, "brief": BriefsService.redact_brief(result)}), 201
    except GovernanceMigrationRequired as e:
        return jsonify({"error": str(e)}), 409
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@briefs_bp.route("", methods=["GET"])
@require_admin
def list_briefs():
    limit = request.args.get("limit", default=10, type=int)
    try:
        result = BriefsService.list_briefs(root_dir, limit)
        result["ok"] = True
        return jsonify(result)
    except GovernanceMigrationRequired as e:
        return jsonify({"error": str(e)}), 409
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@briefs_bp.route("/<int:brief_id>", methods=["GET"])
@require_admin
def get_brief(brief_id):
    try:
        brief = BriefsService.get_brief_by_id(root_dir, brief_id)
        return jsonify({"ok": True, "brief": BriefsService.redact_brief(brief)})
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except GovernanceMigrationRequired as e:
        return jsonify({"error": str(e)}), 409
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@briefs_bp.route("/<int:brief_id>/export", methods=["POST"])
@require_admin
def export_brief(brief_id):
    format_type = request.args.get("format", "markdown")
    try:
        content = BriefsService.export_brief(root_dir, brief_id, format_type)
        add_audit_event(
            root_dir=root_dir,
            action="brief.exported",
            object_type="brief",
            object_id=str(brief_id),
            actor_id=1,
            metadata={"format": format_type}
        )
        return jsonify({"ok": True, "format": format_type, "content": content})
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except GovernanceMigrationRequired as e:
        return jsonify({"error": str(e)}), 409
    except Exception as e:
        return jsonify({"error": str(e)}), 500
