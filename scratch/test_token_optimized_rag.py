import os
import sys
import json
import shutil
import tempfile
import unittest
from pathlib import Path

# Add root dir to sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from app.services.memory_os import (
    MemoryOS,
    parse_toml,
    wrap_in_xml,
    format_user_profile,
    markdown_table_to_html,
    compress_dialog,
    strip_whitespace_noise,
)

class TestTokenOptimizedRag(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = Path(self.test_dir) / "memory_os.db"
        
        import scripts.memory.search_memory as search_mod
        self.orig_search_root = search_mod.ROOT
        self.orig_search_mem = search_mod.MEMORY_DIR
        
        search_mod.ROOT = Path(self.test_dir)
        search_mod.MEMORY_DIR = Path(self.test_dir) / "memory"
        search_mod.MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        
        self.addCleanup(lambda: setattr(search_mod, "ROOT", self.orig_search_root))
        self.addCleanup(lambda: setattr(search_mod, "MEMORY_DIR", self.orig_search_mem))

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_toml_parser_basic(self):
        toml_str = """
        # Model settings
        [model]
        provider = "ollama"
        name = "llama3"
        temperature = 0.7
        active = true

        # RAG settings
        [rag]
        chunk_size = 800
        overlap = 120
        tools = ["search", "validate"]
        """
        data = parse_toml(toml_str)
        self.assertEqual(data["model"]["provider"], "ollama")
        self.assertEqual(data["model"]["temperature"], 0.7)
        self.assertEqual(data["model"]["active"], True)
        self.assertEqual(data["rag"]["chunk_size"], 800)
        self.assertEqual(data["rag"]["tools"], ["search", "validate"])

    def test_isolated_sqlite_memories_table(self):
        # Initialize MemoryOS on the temp db path
        memory_os = MemoryOS(db_path=str(self.db_path))
        
        # Verify db is created and empty
        mems = memory_os.get_memories()
        self.assertEqual(len(mems), 0)
        
        # Add a memory
        memory_os.add_or_update_memory(
            memory_id="pref.structured",
            mem_type="preference",
            content="User prefers structured interview questions.",
            summary="User structured Qs preference.",
            importance=0.95,
            timestamp=1777800000
        )
        
        # Retrieve and verify
        mems = memory_os.get_memories()
        self.assertEqual(len(mems), 1)
        self.assertEqual(mems[0]["id"], "pref.structured")
        self.assertEqual(mems[0]["type"], "preference")
        self.assertEqual(mems[0]["importance"], 0.95)
        self.assertEqual(mems[0]["timestamp"], 1777800000)
        
        # Update existing memory
        memory_os.add_or_update_memory(
            memory_id="pref.structured",
            mem_type="preference",
            content="User prefers structured responses and TOML configs.",
            summary="User updated pref.",
            importance=0.99,
            timestamp=1777800100
        )
        
        mems = memory_os.get_memories()
        self.assertEqual(len(mems), 1)
        self.assertEqual(mems[0]["content"], "User prefers structured responses and TOML configs.")
        self.assertEqual(mems[0]["importance"], 0.99)

    def test_memory_events_jsonl_format(self):
        events_file = Path(self.test_dir) / "memory_events.jsonl"
        
        event1 = {"ts": 1777800000, "t": "pref", "c": "Structured Qs", "imp": 0.95}
        event2 = {"ts": 1777800300, "t": "proj", "c": "Local RAG chatbot", "imp": 0.99}
        
        # Append events
        with open(events_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(event1) + "\n")
            f.write(json.dumps(event2) + "\n")
            
        # Verify read
        self.assertTrue(events_file.exists())
        with open(events_file, "r", encoding="utf-8") as f:
            lines = [json.loads(line.strip()) for line in f if line.strip()]
            
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0]["t"], "pref")
        self.assertEqual(lines[1]["c"], "Local RAG chatbot")

    def test_xml_wrapping(self):
        content = "  This is prompt context.  "
        wrapped = wrap_in_xml("system_context", content)
        self.assertEqual(wrapped, "<system_context>\nThis is prompt context.\n</system_context>")

    def test_format_user_profile(self):
        profile = {
            "proj": "local_rag_chatbot",
            "stack": ["python", "ollama", "qdrant"],
            "pref": "structured_responses"
        }
        formatted = format_user_profile(profile)
        expected = "proj=local_rag_chatbot\nstack=python,ollama,qdrant\npref=structured_responses"
        self.assertEqual(formatted, expected)

    def test_markdown_table_to_html(self):
        md_table = """
        | Format | Tokens | Best Use |
        |---|---|---|
        | TOML | Very Low | Configs |
        | XML | Low-Med | Context Packaging |
        """
        html = markdown_table_to_html(md_table)
        expected = "<table><tr><th>Format</th><th>Tokens</th><th>Best Use</th></tr><tr><td>TOML</td><td>Very Low</td><td>Configs</td></tr><tr><td>XML</td><td>Low-Med</td><td>Context Packaging</td></tr></table>"
        self.assertEqual(html, expected)

    def test_compress_dialog(self):
        dialog = [
            {"role": "user", "content": "How do I build a RAG?"},
            {"role": "assistant", "content": "First, select a storage backend.\nSecond, choose a retrieval strategy."}
        ]
        compressed = compress_dialog(dialog)
        expected = "user: How do I build a RAG?\nassistant: First, select a storage backend. Second, choose a retrieval strategy."
        self.assertEqual(compressed, expected)

    def test_strip_whitespace_noise(self):
        dirty_text = """
        Line 1
        
        
        
        Line 2
          Line 3  
        """
        clean = strip_whitespace_noise(dirty_text)
        expected = "Line 1\n\nLine 2\nLine 3"
        self.assertEqual(clean, expected)

    def test_search_memory_symbols_and_traversal(self):
        # Create memory nodes file
        nodes_file = Path(self.test_dir) / "memory" / "nodes.jsonl"
        node1 = {
            "id": "openrouter.free",
            "type": "rule",
            "summary": "Must use free OpenRouter endpoints.",
            "evidence": ["AGENTS.md"],
            "status": "verified",
            "freshness": "2026-06-02T08:00:00Z",
            "trust": "verified",
            "related_nodes": []
        }
        with open(nodes_file, "w", encoding="utf-8") as f:
            f.write(json.dumps(node1) + "\n")
            
        # Create codebase snapshot file
        snapshot_file = Path(self.test_dir) / "agent_context" / "memory_snapshot.json"
        snapshot_file.parent.mkdir(parents=True, exist_ok=True)
        
        snapshot_data = {
            "generated_at": "2026-06-02T08:00:00",
            "items": [
                {
                    "vector_text": "app/services/credentials.py class CredentialsStore def store_credential decrypter governance",
                    "meta": {
                        "file": "app/services/credentials.py",
                        "layer": "domain-layer",
                        "classes": ["CredentialsStore:10"],
                        "functions": ["store_credential:34"],
                        "dependencies": ["governance"]
                    }
                },
                {
                    "vector_text": "app/services/governance.py class GovernanceManager def _connect",
                    "meta": {
                        "file": "app/services/governance.py",
                        "layer": "domain-layer",
                        "classes": ["GovernanceManager:8"],
                        "functions": ["_connect:54"],
                        "routes": ["/api/governance/policy GET"],
                        "headings": ["Goal Description"],
                        "dependencies": []
                    }
                }
            ]
        }
        with open(snapshot_file, "w", encoding="utf-8") as f:
            json.dump(snapshot_data, f)
            
        # Import search_memory
        from scripts.memory.search_memory import search_memory
        
        # Test exact class search
        res = search_memory("CredentialsStore")
        code_files = [r for r in res if r["type"] == "code_file"]
        self.assertEqual(len(code_files), 2)  # CredentialsStore exact match + traversed dependency governance.py
        self.assertEqual(code_files[0]["id"], "file:app/services/credentials.py")
        self.assertEqual(code_files[0]["rank"], 1)
        self.assertEqual(code_files[0]["match_type"], "exact_symbol")
        
        self.assertEqual(code_files[1]["id"], "file:app/services/governance.py")
        self.assertEqual(code_files[1]["rank"], 2)
        self.assertEqual(code_files[1]["match_type"], "code_dependency")
        
        # Test exact route search
        res_route = search_memory("/api/governance/policy")
        code_route = [r for r in res_route if r["type"] == "code_file"]
        self.assertEqual(len(code_route), 1)
        self.assertEqual(code_route[0]["id"], "file:app/services/governance.py")
        
        # Test exact heading search
        res_heading = search_memory("Goal Description")
        code_heading = [r for r in res_heading if r["type"] == "code_file"]
        self.assertEqual(len(code_heading), 1)
        self.assertEqual(code_heading[0]["id"], "file:app/services/governance.py")
        
        # Test lexical search fallback
        res_lex = search_memory("decrypter")
        code_lex = [r for r in res_lex if r["type"] == "code_file"]
        self.assertEqual(len(code_lex), 1)
        self.assertEqual(code_lex[0]["id"], "file:app/services/credentials.py")
        self.assertEqual(code_lex[0]["rank"], 3)

if __name__ == "__main__":
    unittest.main()
