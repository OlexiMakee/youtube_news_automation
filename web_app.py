"""
Flask web server entry point for the News Research Automation project (web_app.py).

Uses the Application Factory pattern to instantiate the app from the `app` package.
Manages dev server port allocation and triggers startup tasks (database migration, initial update).
"""
import warnings
warnings.filterwarnings("ignore")

import os
import sys
import threading

# Add the current directory to sys.path so that scraper and app imports work seamlessly
root_dir = os.path.dirname(os.path.abspath(__file__))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import scraper.utils as utils
# Automatically reboot inside venv if not already active, ensuring all dependencies are met
utils.setup_and_run_venv(__file__, required_libs=["psycopg2-binary", "pytesseract", "pillow"])

from app import create_app
from app.state import background_daemons_disabled, trigger_background_update

# Initialize the Flask app using the application factory
app = create_app()


def should_start_initial_update(is_reloader_child):
    """Return True when the dev reloader child may start the initial DB update."""
    return is_reloader_child and not background_daemons_disabled()


def find_free_port(preferred=5001, max_tries=20):
    """
    Returns the first free TCP port starting from `preferred`.
    If the preferred port is busy, offers to kill the blocking process
    or automatically falls back to the next available port.
    
    NOTE: Only called by the parent process (before Werkzeug reloader starts).
    The selected port is stored in WEB_APP_PORT env var for reloaded workers.
    """
    import socket
    import subprocess as _sp

    for port in range(preferred, preferred + max_tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind(("127.0.0.1", port))
                return port          # port is free
            except OSError:
                if port == preferred:
                    # Show which PID owns the preferred port
                    try:
                        result = _sp.run(
                            ["lsof", "-ti", f"tcp:{port}"],
                            capture_output=True, text=True
                        )
                        pids = result.stdout.strip()
                        if pids:
                            print(f"[!] Port {port} is in use by PID(s): {pids}")
                            ans = input(f"    Kill process(es) and use port {port}? [y/N]: ").strip().lower()
                            if ans == "y":
                                _sp.run(["kill", "-9"] + pids.split(), capture_output=True)
                                import time as _t; _t.sleep(0.6)
                                return port
                            else:
                                print(f"[!] Falling back to next available port...")
                        else:
                            print(f"[!] Port {port} is busy. Trying next available port...")
                    except Exception:
                        print(f"[!] Port {port} is busy. Trying next available port...")
                continue

    # Last resort: let OS assign any free port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def main():
    # Make sure we load the env configuration
    utils.load_env()

    # Run process management cleanup script before doing anything else (parent only)
    is_reloader_child = os.environ.get("WERKZEUG_RUN_MAIN") == "true"
    if not is_reloader_child:
        print("[*] Cleaning up background processes...")
        try:
            import subprocess
            subprocess.run([sys.executable, os.path.join(root_dir, 'scripts', 'manage_processes.py')])
        except Exception as e:
            print(f"[!] Process cleanup failed: {e}")

    # Initialize DB (run migrations) on web app startup
    from scraper.db_client import DatabaseClient
    db_client = DatabaseClient()
    db_client.init_db()

    # ── Port selection ──────────────────────────────────────────────────
    # Werkzeug debug reloader spawns a child process with WERKZEUG_RUN_MAIN=true.
    # We select the port ONCE in the parent and pass it via env var WEB_APP_PORT.
    # The reloaded worker simply reads that var — no interactive prompt again.
    is_reloader_child = os.environ.get("WERKZEUG_RUN_MAIN") == "true"

    if is_reloader_child:
        # Read port chosen by parent
        port = int(os.environ.get("WEB_APP_PORT", "5001"))
    else:
        # Parent process: find a free port (may ask user to kill existing process)
        port = find_free_port(preferred=5001)
        os.environ["WEB_APP_PORT"] = str(port)

    # Trigger initial database update only in the reloader child (runs the real app)
    if should_start_initial_update(is_reloader_child):
        print("[*] Starting initial database update in the background...")
        threading.Thread(target=lambda: trigger_background_update(cooldown_seconds=0), daemon=True).start()

    print("-" * 60)
    print(f"Starting News Automation Web Application in Dev Server mode...")
    print(f"URL: http://127.0.0.1:{port}")
    print("-" * 60)

    app.run(host="127.0.0.1", port=port, debug=True)


if __name__ == "__main__":
    main()
