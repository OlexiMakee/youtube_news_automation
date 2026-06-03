"""
Chat Logger Service
Governed Autonomous Intelligence Workspace
"""

from scraper.db_client import DatabaseClient

class ChatLogger:
    """Encapsulates recording of AI chat interactions to the database."""

    @staticmethod
    def log(role: str, provider: str, model: str, user_message: str, assistant_answer: str) -> bool:
        """Insert a chat interaction record into the agent_chats table."""
        try:
            db_client = DatabaseClient()
            conn = db_client.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO agent_chats (role, provider, model, user_message, assistant_answer) VALUES (?, ?, ?, ?, ?)",
                (role, provider, model, user_message, assistant_answer)
            )
            conn.commit()
            db_client.close_connection(conn)
            return True
        except Exception as e:
            print(f"[ChatLogger] Failed to log chat transaction: {e}")
            return False
