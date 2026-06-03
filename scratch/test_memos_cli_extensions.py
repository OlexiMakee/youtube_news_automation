import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from datetime import datetime

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from scripts import memos
from app.services.memory_os import MemoryOS
from app.services.prompt_builder import SystemPromptBuilder


class TestMemosCliExtensions(unittest.TestCase):

    def setUp(self):
        # Redirect stdout and stderr to avoid terminal spam
        self.stdout = StringIO()
        self.stderr = StringIO()

    def test_search_command_finds_nodes_and_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # Initialize memos structure
            _quiet_call(memos.cmd_init, _args(root))

            # Add a mock node
            node = {
                "id": "rule.test_cli_search",
                "type": "rule",
                "summary": "This is a test search node for unit tests",
                "evidence": ["test_memos_cli_extensions.py"],
                "status": "verified",
                "freshness": "2026-06-03T12:00:00",
                "trust": "verified",
                "related_nodes": []
            }
            (root / "memory" / "nodes.jsonl").write_text(json.dumps(node) + "\n", encoding="utf-8")

            # Add a mock snapshot
            snapshot = {
                "generated_at": "2026-06-03T12:00:00",
                "items": [
                    {
                        "vector_text": "app/services/memory_os/core.py MemoryOS init_db",
                        "meta": {
                            "file": "app/services/memory_os/core.py",
                            "layer": "domain-layer",
                            "classes": ["MemoryOS:6"],
                            "functions": ["init_db:26"],
                            "dependencies": []
                        }
                    }
                ]
            }
            (root / "agent_context" / "memory_snapshot.json").write_text(json.dumps(snapshot), encoding="utf-8")

            # Search command arguments
            args = _args(root)
            args.query = "MemoryOS"
            args.depth = 1
            args.json = False
            args.config = str(root / "memos.config.json")

            # Capture stdout
            stdout_capture = StringIO()
            with redirect_stdout(stdout_capture):
                res = memos.cmd_search(args)

            output = stdout_capture.getvalue()
            self.assertEqual(res, 0)
            self.assertIn("Found 1 matched codebase files:", output)
            self.assertIn("MemoryOS", output)

    def test_user_memory_cli_actions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # Create data folder
            (root / "data").mkdir(parents=True, exist_ok=True)
            db_path = root / "data" / "memory_os.db"

            # 1. Test add action
            args = _args(root)
            args.action = "add"
            args.id = "pref.theme"
            args.type = "preference"
            args.content = "User prefers Shades of Grey theme"
            args.summary = "Theme Preference"
            args.importance = 0.95
            args.timestamp = int(datetime.utcnow().timestamp())

            stdout_capture = StringIO()
            with redirect_stdout(stdout_capture):
                res = memos.cmd_user_memory(args)

            self.assertEqual(res, 0)
            self.assertIn("Successfully added/updated user memory", stdout_capture.getvalue())

            # Verify in DB
            memory_os = MemoryOS(db_path=str(db_path))
            memories = memory_os.get_memories()
            self.assertEqual(len(memories), 1)
            self.assertEqual(memories[0]["id"], "pref.theme")
            self.assertEqual(memories[0]["content"], "User prefers Shades of Grey theme")

            # 2. Test list action
            args_list = _args(root)
            args_list.action = "list"
            args_list.limit = 50
            stdout_list = StringIO()
            with redirect_stdout(stdout_list):
                res_list = memos.cmd_user_memory(args_list)

            self.assertEqual(res_list, 0)
            list_output = stdout_list.getvalue()
            self.assertIn("pref.theme", list_output)
            self.assertIn("User prefers Shades of Grey theme", list_output)

            # 3. Test search action
            args_search = _args(root)
            args_search.action = "search"
            args_search.query = "Shades"
            args_search.limit = 50
            stdout_search = StringIO()
            with redirect_stdout(stdout_search):
                res_search = memos.cmd_user_memory(args_search)

            self.assertEqual(res_search, 0)
            search_output = stdout_search.getvalue()
            self.assertIn("pref.theme", search_output)
            self.assertIn("User prefers Shades of Grey theme", search_output)

            # 4. Test delete action
            args_del = _args(root)
            args_del.action = "delete"
            args_del.id = "pref.theme"
            stdout_del = StringIO()
            with redirect_stdout(stdout_del):
                res_del = memos.cmd_user_memory(args_del)

            self.assertEqual(res_del, 0)
            self.assertIn("Successfully deleted user memory", stdout_del.getvalue())

            # Verify empty
            self.assertEqual(len(memory_os.get_memories()), 0)

    def test_context_command(self):
        args = _args(Path("."))
        args.role = "user"
        args.channels = None
        args.start_date = None
        args.end_date = None
        args.limit = 5
        stdout_capture = StringIO()
        with redirect_stdout(stdout_capture):
            res = memos.cmd_context(args)

        self.assertEqual(res, 0)
        self.assertIn("=== СИСТЕМНІ ВИМОГИ ===", stdout_capture.getvalue())

    def test_prompt_injection_safety_filters(self):
        # We want to test SystemPromptBuilder.build's memory injection
        # Initialize isolated DB first
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # Create data folder
            (root / "data").mkdir(parents=True, exist_ok=True)
            db_path = root / "data" / "memory_os.db"

            # Mock MemoryOS target path in core.py by temporarily pointing it to our temp database
            # We can instantiate MemoryOS directly using our db_path
            memory_os = MemoryOS(db_path=str(db_path))
            
            # Add safe user memory
            memory_os.add_or_update_memory(
                memory_id="pref.safe_user_fact",
                mem_type="preference",
                content="Always respond concisely",
                summary="Conciseness Preference",
                importance=0.8
            )

            # Add potentially leaking codebase memory (starts with file: or type code_file)
            memory_os.add_or_update_memory(
                memory_id="file:app/routes/actions.py",
                mem_type="code_file",
                content="def shutdown_route(): pass",
                summary="Shutdown Code Symbol",
                importance=0.9
            )
            memory_os.add_or_update_memory(
                memory_id="code.class_symbol",
                mem_type="code_file",
                content="class DatabaseClient:",
                summary="DB Client Code",
                importance=0.85
            )

            # We need to ensure SystemPromptBuilder.build queries this mock database.
            # SystemPromptBuilder imports MemoryOS which defaults to data/memory_os.db in the workspace.
            # To test it cleanly without modifying the global workspace database, we can temporarily patch the
            # default db_path in MemoryOS. Let's do that!
            original_db_path = MemoryOS().db_path
            try:
                # Patch class variable or defaults
                # The default is in __init__ of MemoryOS. We can patch it by modifying its instantiation.
                # Let's mock MemoryOS.get_connection to point to our db_path instead.
                old_get_connection = MemoryOS.get_connection
                def mock_get_connection(self_obj):
                    import sqlite3
                    conn = sqlite3.connect(str(db_path))
                    conn.row_factory = sqlite3.Row
                    return conn
                MemoryOS.get_connection = mock_get_connection

                prompt = SystemPromptBuilder.build("test_db_context", role="admin")

                # Verify safe memory is present
                self.assertIn("Always respond concisely", prompt)
                # Verify codebase leaks are strictly filtered and absent
                self.assertNotIn("app/routes/actions.py", prompt)
                self.assertNotIn("class DatabaseClient", prompt)
                self.assertNotIn("code.class_symbol", prompt)

            finally:
                # Restore original
                MemoryOS.get_connection = old_get_connection


def _args(root):
    class Args:
        pass

    args = Args()
    args.root = str(root)
    return args


def _quiet_call(func, args):
    with redirect_stdout(StringIO()):
        return func(args)


if __name__ == "__main__":
    unittest.main()
