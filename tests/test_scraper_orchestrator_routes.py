import os
import sys
import tempfile
import unittest
from pathlib import Path

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)


class TestScraperOrchestratorRoutes(unittest.TestCase):
    def setUp(self):
        os.environ["NEWS_RESEARCH_DISABLE_BACKGROUND_DAEMONS"] = "1"
        self.old_token = os.environ.get("NEWS_RESEARCH_ADMIN_TOKEN")
        os.environ["NEWS_RESEARCH_ADMIN_TOKEN"] = "secret-token"
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "data").mkdir()

    def tearDown(self):
        self.tmp.cleanup()
        if self.old_token is None:
            os.environ.pop("NEWS_RESEARCH_ADMIN_TOKEN", None)
        else:
            os.environ["NEWS_RESEARCH_ADMIN_TOKEN"] = self.old_token

    def _client_with_root(self):
        from app import create_app
        import app.routes.scraper as scraper_route

        old_root = scraper_route.root_dir
        scraper_route.root_dir = str(self.root)
        self.addCleanup(lambda: setattr(scraper_route, "root_dir", old_root))
        return create_app().test_client()

    def test_scraper_proposals_and_tasks_routes_do_not_500(self):
        client = self._client_with_root()
        headers = {"X-Admin-Token": "secret-token"}

        proposals = client.get("/api/scraper/proposals", headers=headers)
        self.assertEqual(proposals.status_code, 200)
        self.assertEqual(proposals.get_json()["proposals"], [])

        tasks = client.get("/api/scraper/tasks", headers=headers)
        self.assertEqual(tasks.status_code, 200)
        self.assertEqual(tasks.get_json()["tasks"], [])

    def test_orchestrator_accepts_db_path_keyword_contract(self):
        from app.services.scraper_orchestrator import ScraperOrchestrator

        db_path = str(self.root / "data" / "memory_os.db")
        orchestrator = ScraperOrchestrator(db_path=db_path, root_dir=str(self.root))
        self.assertEqual(orchestrator.get_proposals(), [])
        self.assertEqual(orchestrator.get_active_tasks(), [])


if __name__ == "__main__":
    unittest.main()
