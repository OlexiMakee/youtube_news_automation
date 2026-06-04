"""Background scraping task runner and proposal orchestrator.
Flask-app concern: orchestrates governance DB calls.
Separated from the portable memory_os package.
"""

from __future__ import annotations

import json
import time
import uuid
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from memory_os.core import MemoryOS
from app.services.governance import run_source_ingestion, create_source, list_sources


class ScraperOrchestrator:
    """Thread-safe Singleton orchestrator for background scraping tasks and proposals."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, db_path: str | None = None, root_dir: str | None = None):
        if self._initialized:
            return
        self.memory_os = MemoryOS(db_path)
        self.root_dir = root_dir or str(Path(__file__).resolve().parents[2])
        self.active_tasks: Dict[str, Dict[str, Any]] = {}
        self.tasks_lock = threading.Lock()
        self._initialized = True

    def get_proposals(self) -> List[Dict[str, Any]]:
        """Retrieve all active scraping proposals from memories."""
        memories = self.memory_os.get_memories(limit=100)
        proposals = []
        for mem in memories:
            if mem["type"] == "scraping_proposal":
                try:
                    content = json.loads(mem["content"])
                    proposals.append({
                        "id": mem["id"],
                        "summary": mem["summary"],
                        "importance": mem["importance"],
                        "timestamp": mem["timestamp"],
                        **content
                    })
                except json.JSONDecodeError:
                    continue
        return proposals

    def create_proposal(self, source_type: str, external_id: str, name: str, query_input: Dict[str, Any], importance: float = 0.8) -> str:
        """Create a new scraping proposal."""
        proposal_id = f"proposal.scrape.{uuid.uuid4().hex[:8]}"
        content = {
            "source_type": source_type,
            "external_id": external_id,
            "name": name,
            "query_input": query_input,
            "status": "pending",
        }
        self.memory_os.add_or_update_memory(
            memory_id=proposal_id,
            mem_type="scraping_proposal",
            content=json.dumps(content),
            summary=f"Scrape {name} ({source_type})",
            importance=importance
        )
        return proposal_id

    def approve_proposal(self, proposal_id: str, custom_config: dict[str, Any] | None = None) -> Optional[str]:
        """Approve a proposal and launch it in the background."""
        proposals = self.get_proposals()
        target = None
        for prop in proposals:
            if prop["id"] == proposal_id:
                target = prop
                break
                
        if not target or target["status"] != "pending":
            return None

        # Merge custom configs into query_input
        query_input = dict(target.get("query_input") or {})
        if custom_config:
            for k, v in custom_config.items():
                if v is not None:
                    query_input[k] = v

        # Update status to approved
        target["status"] = "approved"
        content_update = {
            "source_type": target["source_type"],
            "external_id": target["external_id"],
            "name": target["name"],
            "query_input": query_input,
            "status": "approved"
        }
        self.memory_os.add_or_update_memory(
            memory_id=proposal_id,
            mem_type="scraping_proposal",
            content=json.dumps(content_update),
            summary=target["summary"],
            importance=target["importance"]
        )

        run_target = dict(target)
        run_target["query_input"] = query_input

        # Start background task
        task_id = f"task.scrape.{uuid.uuid4().hex[:8]}"
        t = threading.Thread(target=self._run_scraping_task, args=(task_id, run_target))
        t.daemon = True
        
        with self.tasks_lock:
            self.active_tasks[task_id] = {
                "task_id": task_id,
                "source_type": target["source_type"],
                "name": target["name"],
                "query_input": query_input,
                "status": "running",
                "records_fetched": 0,
                "started_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "elapsed_sec": 0,
                "error": None
            }
            
        t.start()
        return task_id


    def get_active_tasks(self) -> List[Dict[str, Any]]:
        """List status of all background scraping tasks."""
        with self.tasks_lock:
            now = time.time()
            for task_id, task in self.active_tasks.items():
                if task["status"] == "running":
                    started_struct = time.strptime(task["started_at"], "%Y-%m-%d %H:%M:%S")
                    started_epoch = time.mktime(started_struct)
                    task["elapsed_sec"] = int(now - started_epoch)
            return list(self.active_tasks.values())

    def _run_scraping_task(self, task_id: str, proposal: Dict[str, Any]):
        """Target for background scraping thread."""
        started_time = time.time()
        
        try:
            # 1. Register the source in the governance db if not exists
            sources_dict = list_sources(self.root_dir)
            source_id = None
            for s in sources_dict.get("sources", []):
                if s["type"] == proposal["source_type"] and s["external_id"] == proposal["external_id"]:
                    source_id = s["id"]
                    break
            
            if source_id is None:
                tier_map = {"scientific": "A", "github": "C", "reddit": "E", "youtube": "E", "rss": "C"}
                policy_tier = tier_map.get(proposal["source_type"], "C")
                new_source = create_source(self.root_dir, {
                    "type": proposal["source_type"],
                    "name": proposal["name"],
                    "policy_tier": policy_tier,
                    "status": "active",
                    "external_id": proposal["external_id"]
                })
                source_id = new_source["id"]

            # 2. Run Ingestion with persist=True
            payload = {
                "source_id": source_id,
                "persist": True,
                "allow_tier_e": True,
                "input": proposal["query_input"]
            }
            
            res = run_source_ingestion(self.root_dir, payload)
            records_count = res.get("summary", {}).get("records_created", 0)
            
            with self.tasks_lock:
                task = self.active_tasks[task_id]
                task["status"] = "completed"
                task["records_fetched"] = records_count
                task["elapsed_sec"] = int(time.time() - started_time)
                
        except Exception as exc:
            import traceback
            traceback.print_exc()
            with self.tasks_lock:
                task = self.active_tasks[task_id]
                task["status"] = "failed"
                task["error"] = str(exc)
                task["elapsed_sec"] = int(time.time() - started_time)
