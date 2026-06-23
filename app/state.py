import os
import sys
import time
import subprocess
import threading
from datetime import datetime

from news_scraper.db_client import DatabaseClient
from news_scraper.postgres_sync import PostgresSyncClient

# Calculate root directory relative to this file
app_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(app_dir)

SCRAPE_LOG_PATH = os.path.join(root_dir, "data", "web_app_scrape.log")
SYNC_LOG_PATH = os.path.join(root_dir, "data", "web_app_sync.log")
UPDATE_LOG_PATH = os.path.join(root_dir, "data", "web_app_update.log")
VIEWS_UPDATE_LOG_PATH = os.path.join(root_dir, "data", "web_app_views_update.log")

# Global states for background tasks
bg_state = {
    "active_task": "idle",  # "idle", "scraping", "syncing", "updating", "updating_views"
    "process": None,        # Subprocess object for scraping / updating
    "thread": None,         # Thread object for syncing
    "log_file": None,       # Path to active log file
    "error_msg": None,
    "last_update_time": 0.0
}

# RLock so check_active_tasks() can be called from within an already-locked context.
_bg_lock = threading.RLock()

ENTITLEMENT_FLAGS = {
    "ready_workspace": {
        "label": "Ready Workspace",
        "default_enabled": True,
        "description": "Prebuilt editorial workspace, daily brief surface, and monitored source cards."
    },
    "dense_workspace": {
        "label": "Dense Workspace",
        "default_enabled": True,
        "description": "Resizable grid widgets, saved layouts, and keyboard-friendly analyst workflow."
    },
    "linked_intelligence": {
        "label": "Linked Intelligence",
        "default_enabled": False,
        "description": "Entity linking, cross-source filtering, timelines, and evidence inspection."
    },
    "operator_runtime": {
        "label": "Operator Runtime",
        "default_enabled": False,
        "description": "Source registry, connector jobs, model routing, quotas, prompts, and job logs."
    },
    "autonomous_watchers": {
        "label": "Autonomous Watchers",
        "default_enabled": False,
        "description": "Scheduled watchers, agent runs, anomaly queues, and human approval workflows."
    }
}

DEFAULT_ENTITLEMENT_STATE = {
    key: config["default_enabled"]
    for key, config in ENTITLEMENT_FLAGS.items()
}

# TODO: Phase 1 toggle: enable ready_workspace + dense_workspace by default during MVP; gate linked_intelligence + autonomous_watchers for Phase 2+

def get_entitlement_state(overrides=None):
    """Return progressive workspace feature flags with optional explicit overrides."""
    state = DEFAULT_ENTITLEMENT_STATE.copy()
    if overrides:
        for key, value in overrides.items():
            if key in state:
                state[key] = bool(value)
    return state


def background_daemons_disabled():
    """Return True when tests/import checks must not start background work."""
    return (
        os.environ.get("NEWS_RESEARCH_DISABLE_BACKGROUND_DAEMONS") == "1"
        or "pytest" in sys.modules
        or "unittest" in sys.modules
    )


def get_sqlite_conn():
    """Helper to get a connection to the local SQLite database."""
    db_client = DatabaseClient()
    return db_client.get_connection()


def check_active_tasks():
    """Checks background jobs and resets states if completed."""
    global bg_state
    with _bg_lock:
        if bg_state["active_task"] in ["scraping", "updating", "updating_views"]:
            proc = bg_state["process"]
            if proc and proc.poll() is not None:
                exit_code = proc.poll()
                if exit_code != 0:
                    if bg_state["active_task"] == "updating":
                        task_name = "Update"
                    elif bg_state["active_task"] == "updating_views":
                        task_name = "Views Update"
                    else:
                        task_name = "Scraper"
                    bg_state["error_msg"] = f"{task_name} exited with error code {exit_code}."
                bg_state["active_task"] = "idle"
                bg_state["process"] = None

        elif bg_state["active_task"] == "syncing":
            thr = bg_state["thread"]
            if thr and not thr.is_alive():
                bg_state["active_task"] = "idle"
                bg_state["thread"] = None


def trigger_background_update(cooldown_seconds=30):
    """Launches update_db.py in the background if idle and cooldown has passed."""
    global bg_state
    if background_daemons_disabled():
        return False

    with _bg_lock:
        check_active_tasks()

        if bg_state["active_task"] != "idle":
            return False

        current_time = time.time()
        last_time = bg_state.get("last_update_time", 0.0)
        if current_time - last_time < cooldown_seconds:
            return False

        bg_state["last_update_time"] = current_time

        try:
            with open(UPDATE_LOG_PATH, 'w') as f:
                f.write(f"=== DATABASE UPDATE PROCESS STARTED AT {datetime.now().isoformat()} ===\n")

            with open(UPDATE_LOG_PATH, 'a') as log_file:
                proc = subprocess.Popen(
                    [sys.executable, 'update_db.py', '--cron'],
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    cwd=root_dir
                )
            # log_file closed in parent; child inherited the fd before close
            bg_state["active_task"] = "updating"
            bg_state["process"] = proc
            bg_state["log_file"] = UPDATE_LOG_PATH
            bg_state["error_msg"] = None
            return True
        except Exception as e:
            bg_state["error_msg"] = f"Failed to launch database updater: {e}"
            return False


def bg_sync_worker():
    """Background worker that calls Postgres Sync and writes to log."""
    global bg_state
    try:
        # Custom print function that writes to sync log
        def log_write(msg):
            with open(SYNC_LOG_PATH, 'a') as lf:
                lf.write(f"{datetime.now().strftime('%H:%M:%S')} - {msg}\n")
        
        log_write("Starting Neon Postgres delta replication...")
        
        db_client = DatabaseClient()
        pg_client = PostgresSyncClient()
        
        if not pg_client.is_configured():
            log_write(f"ERROR: {pg_client.get_status_message()}")
            return
            
        log_write("Verifying database schema...")
        pg_client.init_pg_db()
        log_write("Database schema initialized. Running delta upload...")
        
        # Redirect standard output during sync to capture logs
        class LogRedirector:
            def write(self, text):
                if text.strip():
                    log_write(text.strip())
            def flush(self):
                pass
            def isatty(self):
                return False
                
        sys_stdout_backup = sys.stdout
        sys.stdout = LogRedirector()
        
        try:
            success = pg_client.sync_delta(db_client, silent=False)
            if success:
                log_write("Neon Postgres delta replication completed successfully!")
            else:
                log_write("ERROR: Delta replication failed. Check connection parameters.")
        finally:
            sys.stdout = sys_stdout_backup
            
    except Exception as e:
        with open(SYNC_LOG_PATH, 'a') as lf:
            lf.write(f"CRITICAL ERROR: {e}\n")
        bg_state["error_msg"] = str(e)


def trigger_background_views_update(period, cooldown_seconds=2):
    """Launches update_views.py in the background if idle."""
    global bg_state
    if background_daemons_disabled():
        return False

    with _bg_lock:
        check_active_tasks()

        if bg_state["active_task"] != "idle":
            return False

        try:
            with open(VIEWS_UPDATE_LOG_PATH, 'w') as f:
                f.write(f"=== VIDEOS VIEWS UPDATE PROCESS STARTED AT {datetime.now().isoformat()} ===\n")

            with open(VIEWS_UPDATE_LOG_PATH, 'a') as log_file:
                proc = subprocess.Popen(
                    [sys.executable, 'update_views.py', '--period', period],
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    cwd=root_dir
                )
            bg_state["active_task"] = "updating_views"
            bg_state["process"] = proc
            bg_state["log_file"] = VIEWS_UPDATE_LOG_PATH
            bg_state["error_msg"] = None
            return True
        except Exception as e:
            bg_state["error_msg"] = f"Failed to launch views updater: {e}"
            return False
