"""
Chat Logger Service
Governed Autonomous Intelligence Workspace
"""

from typing import Optional

from scraper.db_client import DatabaseClient

class ChatLogger:
    """Encapsulates recording of AI chat interactions to the database."""

    @staticmethod
    def log(role: str, provider: str, model: str, user_message: str, assistant_answer: str) -> Optional[int]:
        """Insert a chat interaction record. Returns the new row ID, or None on failure."""
        try:
            db_client = DatabaseClient()
            conn = db_client.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO agent_chats (role, provider, model, user_message, assistant_answer) VALUES (?, ?, ?, ?, ?)",
                (role, provider, model, user_message, assistant_answer)
            )
            chat_id = cursor.lastrowid
            conn.commit()
            db_client.close_connection(conn)
            return chat_id
        except Exception as e:
            print(f"[ChatLogger] Failed to log chat transaction: {e}")
            return None

    @staticmethod
    def mark_learned(chat_id: int) -> bool:
        """Set learned_at timestamp for a chat record."""
        try:
            from datetime import datetime
            db_client = DatabaseClient()
            conn = db_client.get_connection()
            conn.execute(
                "UPDATE agent_chats SET learned_at = ? WHERE id = ?",
                (datetime.now().isoformat(timespec="seconds"), chat_id)
            )
            conn.commit()
            db_client.close_connection(conn)
            return True
        except Exception as e:
            print(f"[ChatLogger] Failed to mark learned: {e}")
            return False
