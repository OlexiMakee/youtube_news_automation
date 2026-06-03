import os
import sys
import json
import time
import unittest
from unittest.mock import patch, MagicMock

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from scraper.connectors.reddit_connector import RedditConnector
from scraper.connectors.github_connector import GitHubConnector
from scraper.connectors.scientific_connector import ScientificConnector
from scraper.connectors.base import ConnectorContext
from app.services.memory_os.scraper_orchestrator import ScraperOrchestrator
from app import create_app


class TestScraperToolkit(unittest.TestCase):
    def setUp(self):
        os.environ["NEWS_RESEARCH_DISABLE_BACKGROUND_DAEMONS"] = "1"
        self.old_token = os.environ.get("NEWS_RESEARCH_ADMIN_TOKEN")
        os.environ["NEWS_RESEARCH_ADMIN_TOKEN"] = "secret-token"
        
        self.test_db_path = os.path.join(root_dir, "scratch", "test_scraper_memory_os.db")
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)
            
        # Reset orchestrator singleton instance
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

    def test_reddit_connector_parsing(self):
        context = ConnectorContext(
            source_id=10,
            source_type="reddit",
            name="Reddit Test",
            policy_tier="E",
            source_url="https://reddit.com/r/test"
        )
        connector = RedditConnector(context, max_items_per_run=2)
        mock_reddit_json = json.dumps({
            "kind": "Listing",
            "data": {
                "children": [
                    {
                        "data": {
                            "id": "post-1",
                            "title": "Post Title One",
                            "permalink": "/r/test/comments/1",
                            "created_utc": 1780000000,
                            "subreddit": "test",
                            "author": "user1",
                            "score": 100,
                            "num_comments": 10,
                            "selftext": "Content body"
                        }
                    },
                    {
                        "data": {
                            "id": "post-2",
                            "title": "Post Title Two",
                            "permalink": "/r/test/comments/2",
                            "created_utc": 1780000100,
                            "subreddit": "test",
                            "author": "user2",
                            "score": 50,
                            "num_comments": 5,
                            "selftext": ""
                        }
                    }
                ]
            }
        })
        
        result = connector.fetch(json_text=mock_reddit_json, delay_sec=0.0)
        self.assertEqual(result.records_seen, 2)
        self.assertEqual(len(result.records), 2)
        self.assertEqual(result.records[0].title, "Post Title One")
        self.assertEqual(result.records[0].url, "https://www.reddit.com/r/test/comments/1")
        self.assertEqual(result.records[0].metadata["subreddit"], "test")

    def test_github_connector_parsing(self):
        context = ConnectorContext(
            source_id=11,
            source_type="github",
            name="GitHub Test",
            policy_tier="C",
            external_id="owner/repo"
        )
        connector = GitHubConnector(context, max_items_per_run=2)
        mock_github_json = json.dumps([
            {
                "sha": "sha123",
                "html_url": "https://github.com/owner/repo/commit/sha123",
                "commit": {
                    "message": "Commit title line\nMore commit details here",
                    "author": {
                        "name": "Committer Name",
                        "date": "2026-06-03T12:00:00Z"
                    },
                    "committer": {
                        "name": "Committer Name"
                    }
                }
            }
        ])
        
        result = connector.fetch(json_text=mock_github_json, delay_sec=0.0)
        self.assertEqual(result.records_seen, 1)
        self.assertEqual(len(result.records), 1)
        self.assertEqual(result.records[0].title, "Commit title line")
        self.assertEqual(result.records[0].url, "https://github.com/owner/repo/commit/sha123")

    def test_scientific_connector_parsing(self):
        context = ConnectorContext(
            source_id=12,
            source_type="scientific",
            name="Scientific Test",
            policy_tier="A",
            external_id="physics"
        )
        connector = ScientificConnector(context, max_items_per_run=2)
        mock_arxiv_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
            <entry>
                <id>http://arxiv.org/abs/1234.5678v1</id>
                <published>2026-06-03T10:00:00Z</published>
                <title>Paper Title Example</title>
                <summary>This is a summary abstract of the paper.</summary>
                <author>
                    <name>Author One</name>
                </author>
                <author>
                    <name>Author Two</name>
                </author>
            </entry>
        </feed>"""
        
        result = connector.fetch(xml_text=mock_arxiv_xml, delay_sec=0.0)
        self.assertEqual(result.records_seen, 1)
        self.assertEqual(len(result.records), 1)
        self.assertEqual(result.records[0].title, "Paper Title Example")
        self.assertEqual(result.records[0].url, "http://arxiv.org/abs/1234.5678v1")
        self.assertEqual(result.records[0].metadata["authors"], ["Author One", "Author Two"])

    @patch("app.services.memory_os.scraper_orchestrator.run_source_ingestion")
    @patch("app.services.memory_os.scraper_orchestrator.create_source")
    @patch("app.services.memory_os.scraper_orchestrator.list_sources")
    def test_scraper_orchestrator_proposals_and_tasks(self, mock_list, mock_create, mock_ingest):
        mock_list.return_value = {"sources": []}
        mock_create.return_value = {"id": 100}
        mock_ingest.return_value = {"summary": {"records_created": 5}}
        
        orchestrator = ScraperOrchestrator(db_path=self.test_db_path, root_dir=root_dir)
        
        # Test creating a proposal
        prop_id = orchestrator.create_proposal(
            source_type="reddit",
            external_id="all",
            name="Reddit News",
            query_input={"url": "https://reddit.com/r/news"}
        )
        self.assertTrue(prop_id.startswith("proposal.scrape."))
        
        proposals = orchestrator.get_proposals()
        self.assertEqual(len(proposals), 1)
        self.assertEqual(proposals[0]["status"], "pending")
        self.assertEqual(proposals[0]["source_type"], "reddit")
        
        # Test approving proposal
        task_id = orchestrator.approve_proposal(prop_id)
        self.assertTrue(task_id.startswith("task.scrape."))
        
        # Give thread a small moment to run or check active tasks state
        time.sleep(0.1)
        
        active_tasks = orchestrator.get_active_tasks()
        self.assertEqual(len(active_tasks), 1)
        task = active_tasks[0]
        self.assertEqual(task["task_id"], task_id)
        
        # Proposals list should reflect the updated status or pending count
        proposals = orchestrator.get_proposals()
        # Its status should now be "approved"
        self.assertEqual(proposals[0]["status"], "approved")

    @patch("app.routes.scraper.ScraperOrchestrator")
    def test_scraper_endpoints_routing(self, mock_orchestrator_cls):
        # Setup mock orchestrator instance
        mock_orch = MagicMock()
        mock_orch.get_proposals.return_value = [{"id": "prop-1", "name": "reddit-prop", "status": "pending", "source_type": "reddit", "query_input": {}}]
        mock_orch.approve_proposal.return_value = "task-123"
        mock_orch.get_active_tasks.return_value = [{"task_id": "task-123", "status": "running"}]
        mock_orchestrator_cls.return_value = mock_orch
        
        client = create_app().test_client()
        headers = {"X-Admin-Token": "secret-token"}
        
        # Test get proposals
        res = client.get("/api/scraper/proposals", headers=headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()["proposals"][0]["id"], "prop-1")
        
        # Test approve proposal
        res = client.post("/api/scraper/proposals/prop-1/approve", headers=headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()["task_id"], "task-123")
        mock_orch.approve_proposal.assert_called_once_with("prop-1")
        
        # Test get tasks
        res = client.get("/api/scraper/tasks", headers=headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()["tasks"][0]["task_id"], "task-123")

    def test_polite_scraper_engine_delay_and_backoff(self):
        from scraper.connectors.polite_engine import PoliteScraperEngine
        
        PoliteScraperEngine._instance = None
        engine = PoliteScraperEngine(default_delay=2.5, max_delay=10.0)
        
        domain = engine._get_domain("https://example.com/some/path?query=1")
        self.assertEqual(domain, "https://example.com")
        
        delay = engine.get_crawl_delay("https://example.com/news")
        self.assertEqual(delay, 2.5)
        
        engine.report_rate_limit("https://example.com/news")
        delay_after_limit = engine.get_crawl_delay("https://example.com/news")
        self.assertEqual(delay_after_limit, 5.0)
        
        engine.report_rate_limit("https://example.com/news")
        engine.report_rate_limit("https://example.com/news")
        delay_capped = engine.get_crawl_delay("https://example.com/news")
        self.assertEqual(delay_capped, 10.0)
        
        engine.reset_delay("https://example.com/news")
        delay_reset = engine.get_crawl_delay("https://example.com/news")
        self.assertEqual(delay_reset, 2.5)

    @patch("scraper.connectors.base.time.sleep")
    @patch("scraper.connectors.reddit_connector.RedditConnector._download")
    def test_connector_delegates_polite_sleep(self, mock_download, mock_sleep):
        from scraper.connectors.polite_engine import PoliteScraperEngine
        PoliteScraperEngine._instance = None
        PoliteScraperEngine(default_delay=3.0)
        
        context = ConnectorContext(
            source_id=20,
            source_type="reddit",
            name="Reddit Test Delay",
            policy_tier="E",
            source_url="https://reddit.com/r/test"
        )
        connector = RedditConnector(context, max_items_per_run=1)
        mock_download.return_value = json.dumps({"kind": "Listing", "data": {"children": []}})
        
        connector.fetch(url="https://reddit.com/r/test", json_text=None, delay_sec=None)
        
        mock_sleep.assert_called_with(3.0)


if __name__ == "__main__":
    unittest.main()
