"""Scraper routes for managing scraping proposals and background tasks."""

import os
from flask import Blueprint, jsonify, request
from app.services.rbac import require_admin as _admin_required
from app.services.scraper_orchestrator import ScraperOrchestrator
from app.state import root_dir

scraper_bp = Blueprint("scraper", __name__)

@scraper_bp.route("/api/scraper/proposals", methods=["GET"])
@_admin_required
def get_scraper_proposals():
    """Retrieve all active scraping proposals."""
    db_path = os.path.join(root_dir, "data", "memory_os.db")
    orchestrator = ScraperOrchestrator(db_path=db_path, root_dir=root_dir)
    proposals = orchestrator.get_proposals()
    return jsonify({"ok": True, "proposals": proposals})

@scraper_bp.route("/api/scraper/proposals/<proposal_id>/approve", methods=["POST"])
@_admin_required
def approve_scraper_proposal(proposal_id):
    """Approve a scraping proposal and launch a background task."""
    db_path = os.path.join(root_dir, "data", "memory_os.db")
    body = request.get_json(silent=True)
    orchestrator = ScraperOrchestrator(db_path=db_path, root_dir=root_dir)
    if body is not None:
        task_id = orchestrator.approve_proposal(proposal_id, custom_config=body)
    else:
        task_id = orchestrator.approve_proposal(proposal_id)
    if task_id:
        from app.services.governance import add_audit_event
        add_audit_event(
            root_dir=root_dir,
            action="scraper_proposal.approved",
            object_type="scraper_proposal",
            object_id=proposal_id,
            metadata={"task_id": task_id, "custom_config": body is not None}
        )
        return jsonify({"ok": True, "task_id": task_id})
    return jsonify({"error": "Proposal not found or already approved/processed."}), 404

@scraper_bp.route("/api/scraper/workflows", methods=["GET"])
@_admin_required
def get_scraper_workflows():
    """Retrieve scraping workflows for a provider type and optional budget constraint."""
    source_type = request.args.get("source_type")
    if not source_type:
        return jsonify({"error": "source_type parameter is required."}), 400
        
    records = request.args.get("records", 100)
    try:
        records = int(records)
    except ValueError:
        records = 100
        
    budget = request.args.get("budget")
    
    from scraper.connectors.polite_engine import PoliteScraperEngine
    engine = PoliteScraperEngine()
    workflows = engine.get_workflow_options(source_type, estimated_records=records)
    
    optimal_workflow = None
    if budget not in (None, ""):
        try:
            budget_val = float(budget)
            optimal_workflow = engine.calculate_optimal_workflow(source_type, budget_val, estimated_records=records)
        except ValueError:
            pass
            
    return jsonify({
        "ok": True,
        "workflows": workflows,
        "optimal_workflow": optimal_workflow
    })

@scraper_bp.route("/api/scraper/tasks", methods=["GET"])
@_admin_required
def get_scraper_tasks():
    """Get active background scraping tasks."""
    db_path = os.path.join(root_dir, "data", "memory_os.db")
    orchestrator = ScraperOrchestrator(db_path=db_path, root_dir=root_dir)
    tasks = orchestrator.get_active_tasks()
    return jsonify({"ok": True, "tasks": tasks})

