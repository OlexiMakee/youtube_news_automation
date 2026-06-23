#!/usr/bin/env python3
"""
Incremental Transcript Watcher

Monitors `data/transcripts/*.txt` for new or updated YouTube transcripts.
Uses a line-cursor to read transcripts in chunks to prevent exceeding LLM token limits,
similarly to how the memory_os daemon monitors its agent log.

Cursor states are saved in `data/transcript_cursors.json`.
"""

import json
import os
import sys
import time
from pathlib import Path

# Setup paths
ROOT = Path(__file__).resolve().parent.parent
TRANSCRIPTS_DIR = ROOT / "data" / "transcripts"
CURSORS_FILE = ROOT / "data" / "transcript_cursors.json"

# Append app root to path
sys.path.append(str(ROOT))

from app.services.llm_clients import LLMClientFactory
from memory_os import MemoryOSConfig
from app.services.memory_os import MemoryOS

CHUNK_LINES = 150  # Number of lines to process per LLM call
POLL_INTERVAL = 10  # Seconds to wait between passes

PROMPT = """You are an AI assistant analyzing a chunk of a YouTube video transcript.
Extract any key facts, insights, or entities mentioned in this segment.
Format your output as a JSON list of objects:
[
  {"type": "insight", "summary": "A concise summary of the point.", "tags": ["tag1", "tag2"]}
]
If there is no meaningful information, return an empty list: []
Only output raw JSON. Do not include markdown formatting.
"""

class TranscriptWatcher:
    def __init__(self):
        self.cursors = self._load_cursors()
        active_space = os.environ.get("MEMORY_OS_SPACE", "news")
        self.config = MemoryOSConfig(space=active_space)
        self.memory_os = MemoryOS(config=self.config)
        # Use primary configured LLM client
        self.llm = LLMClientFactory.get_client()
        TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)

    def _load_cursors(self) -> dict:
        if CURSORS_FILE.exists():
            try:
                return json.loads(CURSORS_FILE.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                return {}
        return {}

    def _save_cursors(self):
        CURSORS_FILE.write_text(json.dumps(self.cursors, indent=2), encoding="utf-8")

    def _process_chunk(self, video_id: str, chunk: list, start_line: int, end_line: int):
        text = "\n".join(chunk)
        if not text.strip():
            return

        user_msg = f"Transcript from {video_id} (lines {start_line}-{end_line}):\n\n{text}"
        try:
            raw_response = self.llm.call_llm(user_msg, system_prompt=PROMPT, model="gemini")
            raw_response = raw_response.strip()
            
            # Remove markdown if present
            if raw_response.startswith("```"):
                raw_response = "\n".join(raw_response.split("\n")[1:-1])
            
            insights = json.loads(raw_response)
            
            for i, item in enumerate(insights):
                mem_type = item.get("type", "insight")
                summary = item.get("summary", "")
                tags = item.get("tags", [])
                
                if not summary:
                    continue
                    
                mem_id = f"yt_transcript.{video_id}.{start_line}.{i}"
                content = {
                    "video_id": video_id,
                    "lines": f"{start_line}-{end_line}",
                    "tags": tags
                }
                
                self.memory_os.add_or_update_memory(
                    memory_id=mem_id,
                    mem_type=mem_type,
                    content=json.dumps(content),
                    summary=summary,
                    importance=0.6
                )
                print(f"    [+] Insight: {summary[:60]}...")
                
        except json.JSONDecodeError:
            print(f"    [!] Failed to parse LLM response for {video_id} chunk.")
        except Exception as e:
            print(f"    [!] LLM error: {e}")

    def watch(self):
        print(f"Watching for new transcripts in {TRANSCRIPTS_DIR}...")
        try:
            while True:
                processed_any = False
                
                for filepath in TRANSCRIPTS_DIR.glob("*.txt"):
                    video_id = filepath.stem
                    current_cursor = self.cursors.get(video_id, 0)
                    
                    try:
                        with open(filepath, "r", encoding="utf-8") as f:
                            lines = f.readlines()
                    except Exception as e:
                        print(f"[!] Could not read {filepath.name}: {e}")
                        continue
                        
                    total_lines = len(lines)
                    if current_cursor >= total_lines:
                        continue  # Nothing new
                        
                    print(f"Processing {filepath.name} from line {current_cursor} to {total_lines}...")
                    
                    # Read in chunks
                    while current_cursor < total_lines:
                        end_cursor = min(current_cursor + CHUNK_LINES, total_lines)
                        chunk = lines[current_cursor:end_cursor]
                        
                        print(f"  -> Chunk {current_cursor}-{end_cursor}")
                        self._process_chunk(video_id, chunk, current_cursor, end_cursor)
                        
                        current_cursor = end_cursor
                        self.cursors[video_id] = current_cursor
                        self._save_cursors()
                        processed_any = True
                        
                if not processed_any:
                    time.sleep(POLL_INTERVAL)
                    
        except KeyboardInterrupt:
            print("\nShutting down transcript watcher.")

if __name__ == "__main__":
    watcher = TranscriptWatcher()
    watcher.watch()
