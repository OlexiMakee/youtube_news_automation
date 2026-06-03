import os
import shutil
import tempfile
import unittest
from pathlib import Path

from app.services.memory_os.core import MemoryOS
from app.services.memory_os.telemetry import TelemetryRecorder
from app.services.memory_os.versioner import PromptVersioner
from app.services.memory_os.context import ContextRegistry
from app.services.memory_os.optimizer import RouteOptimizer

class TestMemoryOS(unittest.TestCase):

    def setUp(self):
        # Create a temporary directory for test database and file indexers
        self.test_dir = tempfile.mkdtemp()
        self.db_path = Path(self.test_dir) / "test_memory_os.db"
        self.memory_os = MemoryOS(db_path=str(self.db_path))
        self.recorder = TelemetryRecorder(self.memory_os)
        self.versioner = PromptVersioner()
        self.optimizer = RouteOptimizer(self.memory_os)
        self.registry = ContextRegistry(root_dir=self.test_dir)

    def tearDown(self):
        # Clean up temporary test files
        shutil.rmtree(self.test_dir)

    def test_database_initialization(self):
        """Verify telemetry table is initialized properly."""
        self.assertTrue(self.db_path.exists())
        conn = self.memory_os.get_connection()
        try:
            # Check table columns
            cursor = conn.execute("PRAGMA table_info(memory_os_telemetry)")
            columns = {row["name"]: row["type"] for row in cursor.fetchall()}
            self.assertIn("prompt_name", columns)
            self.assertIn("prompt_version", columns)
            self.assertIn("prompt_hash", columns)
            self.assertIn("input_tokens", columns)
            self.assertIn("output_tokens", columns)
            self.assertIn("latency_ms", columns)
            self.assertIn("cost", columns)
            self.assertIn("status", columns)
        finally:
            conn.close()

    def test_telemetry_recording(self):
        """Verify runs can be successfully logged and retrieved."""
        success = self.recorder.record_run(
            prompt_name="test_prompt",
            prompt_version="1.0.0",
            prompt_hash="abc123hash",
            provider_id="gemini",
            model_id="gemini-2.5-flash",
            input_tokens=100,
            output_tokens=50,
            cached_tokens=0,
            latency_ms=150,
            cost=0.0001,
            status="success"
        )
        self.assertTrue(success)

        conn = self.memory_os.get_connection()
        try:
            row = conn.execute("SELECT * FROM memory_os_telemetry").fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row["prompt_name"], "test_prompt")
            self.assertEqual(row["prompt_version"], "1.0.0")
            self.assertEqual(row["input_tokens"], 100)
            self.assertEqual(row["output_tokens"], 50)
            self.assertEqual(row["latency_ms"], 150)
            self.assertEqual(row["cost"], 0.0001)
            self.assertEqual(row["status"], "success")
        finally:
            conn.close()

    def test_prompt_versioner(self):
        """Verify prompt templates are successfully hashed, registered, and mapped."""
        template = "Hello {name}, summarize this text: {text}"
        h = self.versioner.compute_hash(template)
        self.assertEqual(len(h), 16)
        
        self.versioner.register_prompt("summary", "1.2.0", template)
        details = self.versioner.get_prompt("summary")
        self.assertIsNotNone(details)
        self.assertEqual(details["version"], "1.2.0")
        self.assertEqual(details["template"], template)
        self.assertEqual(details["hash"], h)

    def test_route_optimizer(self):
        """Verify average stats and routing recommendations work correctly."""
        # Log successful runs for two different models
        self.recorder.record_run(
            prompt_name="optimized_prompt",
            prompt_version="1.0.0",
            prompt_hash="h1",
            provider_id="gemini",
            model_id="gemini-2.5-flash",
            input_tokens=1000,
            output_tokens=500,
            cached_tokens=0,
            latency_ms=100,
            cost=0.0001,
            status="success"
        )
        self.recorder.record_run(
            prompt_name="optimized_prompt",
            prompt_version="1.0.0",
            prompt_hash="h1",
            provider_id="openai",
            model_id="gpt-4o",
            input_tokens=1000,
            output_tokens=500,
            cached_tokens=0,
            latency_ms=300,
            cost=0.005,
            status="success"
        )
        # Log a failed run to check error rate computation
        self.recorder.record_run(
            prompt_name="optimized_prompt",
            prompt_version="1.0.0",
            prompt_hash="h1",
            provider_id="openai",
            model_id="gpt-4o",
            input_tokens=1000,
            output_tokens=0,
            cached_tokens=0,
            latency_ms=200,
            cost=0.0,
            status="error"
        )

        metrics = self.optimizer.analyze_metrics("optimized_prompt")
        self.assertEqual(len(metrics), 2)
        
        # Flash should be the lowest cost first
        flash_stats = [m for m in metrics if m["model_id"] == "gemini-2.5-flash"][0]
        self.assertEqual(flash_stats["run_count"], 1)
        self.assertEqual(flash_stats["avg_latency_ms"], 100.0)
        self.assertEqual(flash_stats["error_rate"], 0.0)

        gpt_stats = [m for m in metrics if m["model_id"] == "gpt-4o"][0]
        self.assertEqual(gpt_stats["run_count"], 2)
        self.assertEqual(gpt_stats["error_rate"], 0.5)

        # Recommendation should choose Gemini due to lower cost and lower error rate
        rec = self.optimizer.recommend_route("optimized_prompt", max_cost_cap=0.01, max_error_threshold=0.2)
        self.assertIsNotNone(rec)
        self.assertEqual(rec["model_id"], "gemini-2.5-flash")

    def test_context_registry(self):
        """Verify context indexing processes files and parses symbols correctly."""
        # Create a mock python file
        py_file = Path(self.test_dir) / "mock_service.py"
        py_file.write_text(
            "import os\n"
            "class MockService:\n"
            "    def perform_action(self):\n"
            "        pass\n",
            encoding="utf-8"
        )

        # Create a mock readme file
        md_file = Path(self.test_dir) / "README.md"
        md_file.write_text(
            "# Mock Project\n"
            "## Getting Started\n"
            "This is a test readme.\n",
            encoding="utf-8"
        )

        snapshot = self.registry.build_snapshot(paths=["mock_service.py", "README.md"])
        self.assertEqual(snapshot["counts"]["items"], 2)

        items = {item["meta"]["file"]: item for item in snapshot["items"]}
        self.assertIn("mock_service.py", items)
        self.assertIn("README.md", items)

        py_item = items["mock_service.py"]
        self.assertEqual(py_item["meta"]["layer"], "domain-layer")
        self.assertIn("MockService:2", py_item["meta"]["classes"])
        self.assertIn("perform_action:3", py_item["meta"]["functions"])
        self.assertIn("os", py_item["meta"]["dependencies"])

        md_item = items["README.md"]
        self.assertEqual(md_item["meta"]["layer"], "meta-layer")
        self.assertIn("Mock Project", md_item["meta"]["headings"])
        self.assertIn("Getting Started", md_item["meta"]["headings"])
