import os
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

# Add root directory to sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from app import create_app
from app.services.memory_os.core import MemoryOS

class TestChatFeedbackMemory(unittest.TestCase):
    def setUp(self):
        os.environ["NEWS_RESEARCH_DISABLE_BACKGROUND_DAEMONS"] = "1"
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_memory_os.db"

        # Patch MemoryOS init to use the temporary test database path
        self.original_init = MemoryOS.__init__
        test_db = str(self.db_path)
        def mock_init(slf, db_path=None):
            self.original_init(slf, db_path=test_db)
        
        MemoryOS.__init__ = mock_init

        # Initialize the global rotation engine using a mock db
        from app.services.cloud_rotation import init_rotation_engine
        self.main_db_dir = tempfile.TemporaryDirectory()
        self.main_db_path = Path(self.main_db_dir.name) / "youtube_news.db"
        
        # Create a dummy main db and the table agent_feedback_memory so rotation engine is happy
        import sqlite3
        conn = sqlite3.connect(str(self.main_db_path))
        conn.execute("CREATE TABLE IF NOT EXISTS agent_feedback_memory (id INTEGER PRIMARY KEY, prompt_text TEXT, response_text TEXT, model_id TEXT, provider_id TEXT, feedback_type TEXT, latency_ms INTEGER)")
        conn.commit()
        conn.close()

        init_rotation_engine(str(self.main_db_path))

        self.app = create_app()
        self.client = self.app.test_client()

    def tearDown(self):
        MemoryOS.__init__ = self.original_init
        self.tmp_dir.cleanup()
        self.main_db_dir.cleanup()

    def test_chat_feedback_saves_to_memory_os_database(self):
        payload = {
            "feedback_type": "like",
            "provider_id": "gemini",
            "model_id": "gemini-2.5-flash",
            "prompt_text": "How is local time calculated?",
            "response_text": "Local time is calculated based on system clock settings.",
            "latency_ms": 120,
            "comment": "Very accurate and concise response."
        }

        # Post feedback
        response = self.client.post("/api/chat/feedback", json=payload)
        self.assertEqual(response.status_code, 200)
        
        data = response.get_json()
        self.assertTrue(data.get("ok"))
        self.assertEqual(data.get("feedback_type"), "like")
        self.assertEqual(data.get("comment"), "Very accurate and concise response.")

        # Query MemoryOS directly to verify the memory was saved
        memory_os = MemoryOS()
        memories = memory_os.get_memories()
        
        self.assertEqual(len(memories), 1)
        mem = memories[0]
        self.assertEqual(mem["type"], "chat_feedback")
        self.assertEqual(mem["summary"], "Feedback: Very accurate and concise response.")
        self.assertIn("Rating: like", mem["content"])
        self.assertIn("Model: gemini-2.5-flash (gemini)", mem["content"])
        self.assertIn("User Comment: Very accurate and concise response.", mem["content"])
        self.assertGreaterEqual(mem["importance"], 0.95)

    def test_chat_feedback_without_comment(self):
        payload = {
            "feedback_type": "dislike",
            "provider_id": "openai",
            "model_id": "gpt-4o",
            "prompt_text": "Calculate 2+2.",
            "response_text": "The result is 5.",
            "latency_ms": 250
        }

        response = self.client.post("/api/chat/feedback", json=payload)
        self.assertEqual(response.status_code, 200)

        memory_os = MemoryOS()
        memories = memory_os.get_memories()
        self.assertEqual(len(memories), 1)
        mem = memories[0]
        self.assertEqual(mem["type"], "chat_feedback")
        self.assertEqual(mem["summary"], "Feedback on: Calculate 2+2....")
        self.assertIn("Rating: dislike", mem["content"])
        self.assertEqual(mem["importance"], 0.35)

if __name__ == "__main__":
    unittest.main()
