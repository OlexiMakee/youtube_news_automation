import os
import sys
import json
import unittest
from unittest.mock import patch, MagicMock

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from scraper.connectors.polite_engine import PoliteScraperEngine
from app.services.memory_os.scraper_orchestrator import ScraperOrchestrator
from app import create_app


class TestScraperWorkflows(unittest.TestCase):
    def setUp(self):
        os.environ["NEWS_RESEARCH_DISABLE_BACKGROUND_DAEMONS"] = "1"
        self.old_token = os.environ.get("NEWS_RESEARCH_ADMIN_TOKEN")
        os.environ["NEWS_RESEARCH_ADMIN_TOKEN"] = "secret-token"
        
        self.test_db_path = os.path.join(root_dir, "scratch", "test_workflows_memory_os.db")
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)
            
        ScraperOrchestrator._instance = None

    def tearDown(self):
        if self.old_token is None:
            os.environ.pop("NEWS_RESEARCH_ADMIN_TOKEN", None)
        else:
            os.environ["NEWS_RESEARCH_ADMIN_TOKEN"] = self.old_token
            
        if os.path.exists(self.test_db_path):
            try:
                os.remove(self.test_db_path)
            except OSError:
                pass

    def test_polite_scraper_workflows_generation(self):
        engine = PoliteScraperEngine()
        
        # Test reddit connector options
        reddit_opts = engine.get_workflow_options("reddit", estimated_records=100)
        self.assertEqual(len(reddit_opts), 5)
        
        # Verify workflow modes are correct
        modes = [opt["workflow"] for opt in reddit_opts]
        self.assertEqual(modes, ["super_economical", "moderately_economical", "medium", "fast", "ultra_fast"])
        
        # Verify costs exist and vary
        ultra_fast_opt = next(opt for opt in reddit_opts if opt["workflow"] == "ultra_fast")
        super_econ_opt = next(opt for opt in reddit_opts if opt["workflow"] == "super_economical")
        self.assertEqual(super_econ_opt["cost_estimate"], 0.0)
        self.assertGreater(ultra_fast_opt["cost_estimate"], 0.0)

    def test_calculate_optimal_workflow_budget(self):
        engine = PoliteScraperEngine()
        
        # For reddit at 100 estimated records, ultra_fast cost = 4 * 0.00024 = 0.00096, fast cost = 0.00048
        # Let's verify we get different options based on different budgets
        opt_zero = engine.calculate_optimal_workflow("reddit", budget=0.0, estimated_records=100)
        self.assertEqual(opt_zero["workflow"], "medium") # Fastest free option
        
        opt_fast = engine.calculate_optimal_workflow("reddit", budget=0.0006, estimated_records=100)
        self.assertEqual(opt_fast["workflow"], "fast")
        
        opt_high = engine.calculate_optimal_workflow("reddit", budget=0.001, estimated_records=100)
        self.assertEqual(opt_high["workflow"], "ultra_fast")

    @patch("app.routes.scraper.ScraperOrchestrator")
    def test_workflows_api_endpoint(self, mock_orchestrator_cls):
        client = create_app().test_client()
        headers = {"X-Admin-Token": "secret-token"}
        
        # Query without source_type -> 400
        res = client.get("/api/scraper/workflows", headers=headers)
        self.assertEqual(res.status_code, 400)
        
        # Query with valid source_type
        res = client.get("/api/scraper/workflows?source_type=github", headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["ok"])
        self.assertEqual(len(data["workflows"]), 5)
        self.assertIsNone(data["optimal_workflow"])
        
        # Query with budget constraint
        res = client.get("/api/scraper/workflows?source_type=reddit&budget=0.0&records=100", headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["optimal_workflow"]["workflow"], "medium")


    @patch("app.services.memory_os.scraper_orchestrator.run_source_ingestion")
    @patch("app.services.memory_os.scraper_orchestrator.create_source")
    @patch("app.services.memory_os.scraper_orchestrator.list_sources")
    def test_approve_proposal_passes_custom_config(self, mock_list, mock_create, mock_ingest):
        mock_list.return_value = {"sources": []}
        mock_create.return_value = {"id": 200}
        mock_ingest.return_value = {"summary": {"records_created": 3}}
        
        orchestrator = ScraperOrchestrator(db_path=self.test_db_path, root_dir=root_dir)
        
        # Create a sample proposal
        prop_id = orchestrator.create_proposal(
            source_type="scientific",
            external_id="physics",
            name="ArXiv Physics",
            query_input={"query": "quantum"}
        )
        
        # Approve proposal with custom configs (e.g. customized delay and workflow mode)
        custom_config = {
            "delay_sec": 4.5,
            "workflow_mode": "moderately_economical",
            "custom_param": "test-value"
        }
        
        task_id = orchestrator.approve_proposal(prop_id, custom_config=custom_config)
        self.assertTrue(task_id.startswith("task.scrape."))
        
        # Give background thread a tiny moment to spin up and read mock configs
        import time
        time.sleep(0.15)
        
        # Verify the proposal memory was updated with merged configs
        proposals = orchestrator.get_proposals()
        approved_prop = next(p for p in proposals if p["id"] == prop_id)
        self.assertEqual(approved_prop["status"], "approved")
        self.assertEqual(approved_prop["query_input"]["delay_sec"], 4.5)
        self.assertEqual(approved_prop["query_input"]["workflow_mode"], "moderately_economical")
        self.assertEqual(approved_prop["query_input"]["custom_param"], "test-value")
        self.assertEqual(approved_prop["query_input"]["query"], "quantum")  # original key preserved


if __name__ == "__main__":
    unittest.main()
