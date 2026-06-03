"""Entity extraction service for Phase 2 Workspace.

Uses LLM client factory to extract political actors, organizations, and locations
from video titles, descriptions, and transcripts, resolving them to a canonical dictionary.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.services.llm_clients import LLMClientFactory


def _connect_db(root_dir: str) -> sqlite3.Connection:
    db_path = Path(root_dir) / "data" / "youtube_news.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


class EntityExtractionService:
    """Service to run entity extraction pipelines and manage entity-alias mapping."""

    @staticmethod
    def extract_entities_from_text(
        root_dir: str,
        text: str,
        provider: str = "gemini",
        model: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        """Sends the text to LLM to extract political actors, organizations, and locations."""
        if not text.strip():
            return []

        if os.environ.get("NEWS_RESEARCH_MOCK_ENTITIES") == "1":
            return [
                {"name": "Volodymyr Zelenskyy", "type": "person", "alias_of": ""},
                {"name": "UATV", "type": "organization", "alias_of": ""},
                {"name": "Kyiv", "type": "location", "alias_of": ""},
            ]

        api_key, base_url, resolved_model = LLMClientFactory.get_provider_config(provider, model)
        if not api_key:
            return []

        system_prompt = (
            "You are an expert OSINT intelligence analyst.\n"
            "Extract all political actors (persons), organizations, and geographic locations mentioned in the text.\n"
            "Return ONLY a valid JSON array of objects representing the extracted entities. Do not include markdown formatting except the JSON payload.\n"
            "Each object MUST contain the following string fields:\n"
            "- 'name': The standard, canonical name of the entity.\n"
            "- 'type': Must be exactly one of: 'person', 'organization', 'location'.\n"
            "- 'alias_of': If this entity name is a variation or alias of a well-known canonical name (e.g. 'Zelensky' is a variation of 'Volodymyr Zelenskyy'), specify the canonical name here. Otherwise, leave empty.\n"
            "Output structure example:\n"
            '[{"name": "Volodymyr Zelenskyy", "type": "person", "alias_of": ""}, '
            '{"name": "UN", "type": "organization", "alias_of": "United Nations"}]'
        )

        user_message = f"Text to extract entities from:\n{text}"

        try:
            client = LLMClientFactory.create_client(provider)
            chunks = []
            for chunk in client.stream_chat(
                api_key=api_key,
                base_url=base_url,
                model=resolved_model,
                user_message=user_message,
                system_prompt=system_prompt,
            ):
                chunks.append(chunk)
            response_text = "".join(chunks)

            # Strip potential markdown wrapping ```json ... ```
            cleaned = response_text.strip()
            if cleaned.startswith("```"):
                lines = cleaned.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                cleaned = "\n".join(lines).strip()

            data = json.loads(cleaned)
            if isinstance(data, list):
                result = []
                for item in data:
                    if isinstance(item, dict) and "name" in item and "type" in item:
                        t = str(item.get("type", "")).lower()
                        if t in {"person", "organization", "location"}:
                            result.append({
                                "name": str(item["name"]).strip(),
                                "type": t,
                                "alias_of": str(item.get("alias_of", "") or "").strip(),
                            })
                return result
        except Exception:
            # Return empty on failure
            pass

        return []

    @staticmethod
    def save_extracted_entities(
        root_dir: str,
        video_id: str,
        raw_entities: List[Dict[str, str]],
        source: str = "description",
    ) -> None:
        """Resolves alias/canonical names and registers associations in video_entities."""
        if not raw_entities:
            return

        conn = _connect_db(root_dir)
        cursor = conn.cursor()

        try:
            for ent in raw_entities:
                name = ent["name"]
                ent_type = ent["type"]
                alias_of = ent["alias_of"]

                # 1. Clean and check if this exact name is already registered as an alias or canonical entity
                cursor.execute(
                    "SELECT canonical_id FROM entity_aliases WHERE alias = ?",
                    (name,)
                )
                row = cursor.fetchone()
                
                if row:
                    canonical_id = row["canonical_id"]
                else:
                    # Check if the name matches a canonical entity directly
                    cursor.execute(
                        "SELECT id FROM entities WHERE name = ?",
                        (name,)
                    )
                    row_ent = cursor.fetchone()
                    
                    if row_ent:
                        canonical_id = row_ent["id"]
                    else:
                        # Determine canonical name to register
                        canonical_name = alias_of if alias_of else name
                        
                        # Find or create canonical entity
                        cursor.execute(
                            "SELECT id FROM entities WHERE name = ?",
                            (canonical_name,)
                        )
                        row_can = cursor.fetchone()
                        
                        if row_can:
                            canonical_id = row_can["id"]
                        else:
                            cursor.execute(
                                "INSERT INTO entities (name, type) VALUES (?, ?)",
                                (canonical_name, ent_type)
                            )
                            canonical_id = cursor.lastrowid
                        
                        # Register both the canonical name and the alias
                        cursor.execute(
                            "INSERT OR IGNORE INTO entity_aliases (canonical_id, alias) VALUES (?, ?)",
                            (canonical_id, canonical_name)
                        )
                        if name != canonical_name:
                            cursor.execute(
                                "INSERT OR IGNORE INTO entity_aliases (canonical_id, alias) VALUES (?, ?)",
                                (canonical_id, name)
                            )

                # 2. Insert connection into video_entities
                cursor.execute(
                    """
                    INSERT INTO video_entities (video_id, entity_id, mentions_count, source)
                    VALUES (?, ?, 1, ?)
                    ON CONFLICT(video_id, entity_id, source) DO UPDATE SET
                        mentions_count = mentions_count + 1
                    """,
                    (video_id, canonical_id, source)
                )
            conn.commit()
        finally:
            conn.close()

    @classmethod
    def extract_entities_for_video(
        cls,
        root_dir: str,
        video_id: str,
        provider: str = "gemini",
        model: Optional[str] = None,
    ) -> int:
        """Helper to run extraction for a single cached video, scanning title, description, and transcript."""
        conn = _connect_db(root_dir)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT title, description, full_description FROM videos WHERE video_id = ?",
            (video_id,)
        )
        row = cursor.fetchone()
        conn.close()

        if not row:
            return 0

        title = row["title"] or ""
        desc = row["full_description"] or row["description"] or ""

        # Check for cached transcript file
        transcript = ""
        transcript_path = Path(root_dir) / "data" / "transcripts" / f"{video_id}.txt"
        if transcript_path.exists():
            try:
                transcript = transcript_path.read_text(encoding="utf-8")
            except Exception:
                pass

        total_extracted = 0

        # Run extraction on Title
        if title:
            entities = cls.extract_entities_from_text(root_dir, title, provider, model)
            if entities:
                cls.save_extracted_entities(root_dir, video_id, entities, source="title")
                total_extracted += len(entities)

        # Run extraction on Description
        if desc:
            entities = cls.extract_entities_from_text(root_dir, desc, provider, model)
            if entities:
                cls.save_extracted_entities(root_dir, video_id, entities, source="description")
                total_extracted += len(entities)

        # Run extraction on Transcript
        if transcript:
            entities = cls.extract_entities_from_text(root_dir, transcript, provider, model)
            if entities:
                cls.save_extracted_entities(root_dir, video_id, entities, source="transcript")
                total_extracted += len(entities)

        return total_extracted
