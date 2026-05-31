#!/usr/bin/env python3
"""
System Telemetry Daemon (v1.1.0)
YouTube News Automation

Purpose: Collect real-time system metrics (CPU, RAM, Disk IO, HTTP sessions) for cloud migration planning.
Runs as lightweight background daemon thread. Safe for SQLite WAL mode (no write bottlenecks).

Metrics Collected:
  - CPU usage (%)
  - RAM used (MB)
  - Disk IO (MB read/written per sample)
  - Active HTTP session count (from Flask)

Storage: SQLite table `system_metrics` (1 row per sample, ~5-10 second intervals)

Usage:
  from app.services.telemetry import TelemetryDaemon
  daemon = TelemetryDaemon(db_path="data/youtube_news.db", interval=10)
  daemon.start()  # Run in background
  # ... Flask app continues ...
  daemon.stop()   # Graceful shutdown
"""

import threading
import sqlite3
import time
import os
import sys
from pathlib import Path
from datetime import datetime
import logging

try:
    import psutil
except ImportError:
    psutil = None

logger = logging.getLogger(__name__)

class TelemetryDaemon(threading.Thread):
    """Background daemon for system metrics collection."""
    
    def __init__(self, db_path: str, interval: int = 10, session_getter=None):
        """
        Initialize telemetry daemon.
        
        Args:
            db_path: Path to SQLite database
            interval: Collection interval in seconds (default: 10)
            session_getter: Callable returning current HTTP session count
                          (default: None, will use 0)
        """
        super().__init__(daemon=True)
        self.db_path = db_path
        self.interval = interval
        self.session_getter = session_getter or (lambda: 0)
        self._stop_event = threading.Event()
        self._last_disk_stats = None
    
    def run(self):
        """Main daemon loop."""
        logger.info(f"Telemetry daemon starting (interval={self.interval}s)")
        
        # Verify database exists
        if not Path(self.db_path).exists():
            logger.error(f"Database not found: {self.db_path}")
            return
        
        while not self._stop_event.is_set():
            try:
                metrics = self._collect_metrics()
                self._store_metrics(metrics)
                time.sleep(self.interval)
            except Exception as e:
                logger.error(f"Telemetry collection error: {e}")
                time.sleep(self.interval)
    
    def _collect_metrics(self) -> dict:
        """Collect system metrics."""
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "cpu_percent": 0.0,
            "ram_mb_used": 0.0,
            "disk_io_mb": 0.0,
            "http_sessions_active": self.session_getter()
        }
        
        if psutil is None:
            logger.warning("psutil not installed, skipping CPU/RAM/Disk metrics")
            return metrics
        
        try:
            # CPU usage (%)
            metrics["cpu_percent"] = psutil.cpu_percent(interval=0.1)
            
            # RAM usage (MB)
            process = psutil.Process(os.getpid())
            metrics["ram_mb_used"] = process.memory_info().rss / (1024 * 1024)
            
            # Disk IO (delta from last sample)
            try:
                disk_io = psutil.disk_io_counters()
                if disk_io and self._last_disk_stats:
                    # Calculate delta
                    read_delta = (disk_io.read_bytes - self._last_disk_stats[0]) / (1024 * 1024)
                    write_delta = (disk_io.write_bytes - self._last_disk_stats[1]) / (1024 * 1024)
                    metrics["disk_io_mb"] = read_delta + write_delta
                
                if disk_io:
                    self._last_disk_stats = (disk_io.read_bytes, disk_io.write_bytes)
            except (OSError, AttributeError):
                logger.debug("Disk IO metrics unavailable on this platform")
        
        except Exception as e:
            logger.warning(f"Error collecting metrics: {e}")
        
        return metrics
    
    def _store_metrics(self, metrics: dict):
        """Store metrics in database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                """
                INSERT INTO system_metrics
                (timestamp, cpu_percent, ram_mb_used, disk_io_mb, http_sessions_active)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    metrics["timestamp"],
                    metrics["cpu_percent"],
                    metrics["ram_mb_used"],
                    metrics["disk_io_mb"],
                    metrics["http_sessions_active"]
                )
            )
            
            conn.commit()
            conn.close()
        
        except Exception as e:
            logger.error(f"Error storing metrics: {e}")
    
    def stop(self):
        """Signal daemon to stop gracefully."""
        logger.info("Telemetry daemon stopping...")
        self._stop_event.set()
        self.join(timeout=5)


# Singleton instance (managed by Flask app)
_telemetry_daemon = None

def start_telemetry(db_path: str, interval: int = 10, session_getter=None):
    """Start global telemetry daemon."""
    global _telemetry_daemon
    
    if _telemetry_daemon is not None:
        logger.warning("Telemetry daemon already running")
        return
    
    _telemetry_daemon = TelemetryDaemon(db_path, interval, session_getter)
    _telemetry_daemon.start()
    logger.info(f"Telemetry daemon started (interval={interval}s)")

def stop_telemetry():
    """Stop global telemetry daemon."""
    global _telemetry_daemon
    
    if _telemetry_daemon is not None:
        _telemetry_daemon.stop()
        _telemetry_daemon = None
        logger.info("Telemetry daemon stopped")

def get_metrics_summary(db_path: str, limit: int = 10):
    """Get recent metrics from database."""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT * FROM system_metrics
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (limit,)
        )
        
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return rows
    
    except Exception as e:
        logger.error(f"Error retrieving metrics: {e}")
        return []


if __name__ == "__main__":
    # Test mode: run telemetry for 30 seconds
    logging.basicConfig(level=logging.INFO)
    
    db_path = Path(__file__).parent.parent / "data" / "youtube_news.db"
    
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        sys.exit(1)
    
    daemon = TelemetryDaemon(str(db_path), interval=5)
    daemon.start()
    
    print("Telemetry daemon running for 30 seconds... (press Ctrl+C to stop)")
    try:
        time.sleep(30)
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        daemon.stop()
    
    print("\nRecent metrics:")
    metrics = get_metrics_summary(str(db_path), limit=5)
    for m in metrics:
        print(f"  {m['timestamp']}: CPU={m['cpu_percent']:.1f}% RAM={m['ram_mb_used']:.1f}MB IO={m['disk_io_mb']:.1f}MB")
