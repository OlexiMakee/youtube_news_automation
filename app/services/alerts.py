import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict
from app.services.governance import add_audit_event


class AlertsService:
    """Service to handle anomaly detection alert routing and audit logging."""

    @staticmethod
    def send_anomaly_alert(root_dir: str, video_id: str, z_score: float, threshold: float = 2.0) -> Dict[str, Any]:
        """Check Z-score threshold, format anomaly alert, and log audit event.
        
        Args:
            root_dir: Project root directory.
            video_id: Target video ID.
            z_score: Calculated views Z-score.
            threshold: Z-score alert threshold.
            
        Returns:
            Dictionary containing alert status and metadata.
        """
        if z_score < threshold:
            return {
                "sent": False,
                "reason": f"Z-score {z_score} is below alert threshold {threshold}."
            }

        # Fetch video title and channel details from youtube_news.db
        main_db_path = Path(root_dir) / "data" / "youtube_news.db"
        title = "Unknown Video"
        channel_id = "Unknown Channel"

        if main_db_path.exists():
            try:
                conn = sqlite3.connect(str(main_db_path))
                conn.row_factory = sqlite3.Row
                row = conn.execute(
                    "SELECT title, channel_id FROM videos WHERE video_id = ?",
                    (video_id,)
                ).fetchone()
                if row:
                    title = row["title"]
                    channel_id = row["channel_id"]
                conn.close()
            except Exception as e:
                print(f"[AlertsService] Failed to query video details: {e}", file=sys.stderr)

        message = (
            f"[ANOMALY ALERT] Video '{title}' (ID: {video_id}) in channel '{channel_id}' "
            f"has reached anomaly Z-score of {z_score} (threshold: {threshold})."
        )

        # Print alert output to system logs
        print(message, file=sys.stderr)

        # Log audit event in governance.db
        add_audit_event(
            root_dir=root_dir,
            action="anomaly.alert",
            object_type="video",
            object_id=video_id,
            metadata={
                "z_score": z_score,
                "threshold": threshold,
                "channel_id": channel_id,
                "title": title[:200] if title else ""
            }
        )

        return {
            "sent": True,
            "message": message,
            "video_id": video_id,
            "z_score": z_score,
            "channel_id": channel_id,
            "title": title
        }
