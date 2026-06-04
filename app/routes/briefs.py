"""Brief routes for Phase 1 Editorial MVP.

Endpoints for brief listing, generation, and formatting exports.
"""

from flask import Blueprint, jsonify, request, Response
from app.services.briefs import BriefsService
from app.services.governance import GovernanceMigrationRequired
from app.services.rbac import require_admin as _admin_required
from app.state import root_dir

briefs_bp = Blueprint("briefs", __name__)


@briefs_bp.route("/api/briefs/generate", methods=["POST"])
@_admin_required
def generate_brief():
    date = request.args.get("date")
    if not date:
        return jsonify({"error": "date parameter YYYY-MM-DD is required."}), 400

    sources_raw = request.args.get("sources")
    source_ids = None
    if sources_raw:
        try:
            source_ids = [int(s.strip()) for s in sources_raw.split(",") if s.strip()]
        except ValueError:
            return jsonify({"error": "sources parameter must be a comma-separated list of integers."}), 400

    try:
        brief = BriefsService.generate_daily_brief(root_dir, date, source_ids)
        redacted = BriefsService.redact_brief(brief)
        return jsonify({"ok": True, "brief": redacted}), 201
    except GovernanceMigrationRequired as exc:
        return jsonify({"error": str(exc), "registry_ready": False}), 409
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@briefs_bp.route("/api/briefs", methods=["GET"])
@_admin_required
def get_briefs():
    try:
        limit = request.args.get("limit", 20)
        data = BriefsService.list_briefs(root_dir, limit=int(limit))
        return jsonify({"ok": True, **data})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@briefs_bp.route("/api/briefs/<int:brief_id>", methods=["GET"])
@_admin_required
def get_brief(brief_id):
    try:
        brief = BriefsService.get_brief_by_id(root_dir, brief_id)
        redacted = BriefsService.redact_brief(brief)
        return jsonify({"ok": True, "brief": redacted})
    except GovernanceMigrationRequired as exc:
        return jsonify({"error": str(exc), "registry_ready": False}), 409
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@briefs_bp.route("/api/briefs/<int:brief_id>/export", methods=["POST"])
@_admin_required
def export_brief(brief_id):
    data = request.get_json(silent=True) or {}
    export_format = data.get("format") or request.args.get("format") or "markdown"
    if export_format not in {"markdown", "html", "pdf"}:
        return jsonify({"error": "Unsupported format. Must be markdown, html, or pdf."}), 400

    try:
        exported_content = BriefsService.export_brief(root_dir, brief_id, export_format)

        from app.services.governance import add_audit_event
        add_audit_event(
            root_dir=root_dir,
            action="brief.exported",
            object_type="brief",
            object_id=brief_id,
            metadata={"format": export_format}
        )

        mimetype = "text/plain"
        if export_format == "html":
            mimetype = "text/html"
        elif export_format == "pdf":
            mimetype = "application/pdf"

        return Response(exported_content, mimetype=mimetype)
    except GovernanceMigrationRequired as exc:
        return jsonify({"error": str(exc), "registry_ready": False}), 409
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@briefs_bp.route("/api/briefs/<int:brief_id>/evidence-bundle", methods=["GET"])
@_admin_required
def get_brief_evidence_bundle(brief_id):
    import io
    import json
    import zipfile
    from pathlib import Path
    from flask import send_file
    from app.services.governance import add_audit_event

    try:
        brief = BriefsService.get_brief_by_id(root_dir, brief_id)
        
        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, "w", zipfile.ZIP_DEFLATED) as zip_file:
            # 1. Add brief.md
            brief_markdown = BriefsService.format_brief_markdown(brief)
            zip_file.writestr("brief.md", brief_markdown)
            
            # 2. Add verification_seal.json
            seal = brief.get("verification_seal") or {}
            zip_file.writestr("verification_seal.json", json.dumps(seal, ensure_ascii=False, indent=2))
            
            # 3. Add evidence files
            evidence_dir = Path(root_dir) / "data" / "evidence_cache"
            for claim in brief.get("claims") or []:
                for src in claim.get("sources") or []:
                    record_id = src.get("id")
                    if not record_id:
                        continue
                    
                    # Meta
                    meta_path = evidence_dir / f"source_record_{record_id}_metadata.json"
                    if meta_path.exists():
                        zip_file.write(str(meta_path), f"evidence/source_record_{record_id}_metadata.json")
                        
                    # Transcript
                    trans_path = evidence_dir / f"source_record_{record_id}_transcript.txt"
                    if trans_path.exists():
                        zip_file.write(str(trans_path), f"evidence/source_record_{record_id}_transcript.txt")
                        
                    # Thumbnail
                    thumb_path = evidence_dir / f"source_record_{record_id}_thumbnail.jpg"
                    if thumb_path.exists():
                        zip_file.write(str(thumb_path), f"evidence/source_record_{record_id}_thumbnail.jpg")
                        
        memory_file.seek(0)
        
        add_audit_event(
            root_dir=root_dir,
            action="brief.evidence_bundle.exported",
            object_type="brief",
            object_id=brief_id,
            metadata={}
        )
        
        return send_file(
            memory_file,
            mimetype="application/zip",
            as_attachment=True,
            download_name=f"evidence_bundle_brief_{brief_id}.zip"
        )
    except GovernanceMigrationRequired as exc:
        return jsonify({"error": str(exc), "registry_ready": False}), 409
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

