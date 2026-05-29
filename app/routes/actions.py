import os
import sys
import subprocess
import threading
from datetime import datetime
from flask import Blueprint, jsonify, request, Response
from app.state import (
    bg_state,
    check_active_tasks,
    trigger_background_update,
    trigger_background_views_update,
    bg_sync_worker,
    root_dir,
    SCRAPE_LOG_PATH,
    SYNC_LOG_PATH
)

actions_bp = Blueprint('actions', __name__)


@actions_bp.route('/api/action/add_channel', methods=['POST'])
def add_channel_route():
    global bg_state
    check_active_tasks()
    
    if bg_state["active_task"] != "idle":
        return jsonify({"error": f"Another task ({bg_state['active_task']}) is already running."}), 400
        
    data = request.json or {}
    channel_url = data.get("channel_url", "").strip()
    mode = data.get("mode", "").strip()
    val = data.get("value", "").strip()
    
    if not channel_url:
        return jsonify({"error": "Channel URL or handle is required."}), 400
        
    if mode not in ["1", "2"] or not val:
        return jsonify({"error": "Scraping mode and value are required."}), 400
        
    # Clear old log file
    with open(SCRAPE_LOG_PATH, 'w') as f:
        f.write(f"=== ADD CHANNEL PROCESS STARTED AT {datetime.now().isoformat()} ===\n")
        f.write(f"Channel URL: {channel_url}\n")
        f.write(f"Mode: {mode}, Value: {val}\n\n")
        
    try:
        log_file = open(SCRAPE_LOG_PATH, 'a')
        proc = subprocess.Popen(
            [sys.executable, 'scripts/init_db.py', channel_url, mode, val],
            stdout=log_file,
            stderr=subprocess.STDOUT,
            cwd=root_dir
        )
        
        bg_state["active_task"] = "scraping"
        bg_state["process"] = proc
        bg_state["log_file"] = SCRAPE_LOG_PATH
        bg_state["error_msg"] = None
        
        return jsonify({"message": f"Scraping task for '{channel_url}' successfully launched in background."})
    except Exception as e:
        bg_state["error_msg"] = f"Failed to launch channel scraper: {e}"
        return jsonify({"error": str(e)}), 500


@actions_bp.route('/api/action/scrape', methods=['POST'])
def start_scrape():
    global bg_state
    check_active_tasks()
    
    if bg_state["active_task"] != "idle":
        return jsonify({"error": f"Another task ({bg_state['active_task']}) is already running."}), 400
        
    # Clear old log file
    with open(SCRAPE_LOG_PATH, 'w') as f:
        f.write(f"=== SCRAPE PROCESS STARTED AT {datetime.now().isoformat()} ===\n")
        
    try:
        # Run scrape_multi.py as a subprocess
        log_file = open(SCRAPE_LOG_PATH, 'a')
        proc = subprocess.Popen(
            [sys.executable, 'scrape_multi.py', '--no-prompt'],
            stdout=log_file,
            stderr=subprocess.STDOUT,
            cwd=root_dir
        )
        
        bg_state["active_task"] = "scraping"
        bg_state["process"] = proc
        bg_state["log_file"] = SCRAPE_LOG_PATH
        bg_state["error_msg"] = None
        
        return jsonify({"message": "Scraping process successfully launched in background."})
    except Exception as e:
        bg_state["error_msg"] = f"Failed to launch scraper: {e}"
        return jsonify({"error": str(e)}), 500


@actions_bp.route('/api/action/sync', methods=['POST'])
def start_sync():
    global bg_state
    check_active_tasks()
    
    if bg_state["active_task"] != "idle":
        return jsonify({"error": f"Another task ({bg_state['active_task']}) is already running."}), 400
        
    # Clear old log file
    with open(SYNC_LOG_PATH, 'w') as f:
        f.write(f"=== NEON SYNC PROCESS STARTED AT {datetime.now().isoformat()} ===\n")
        
    try:
        thr = threading.Thread(target=bg_sync_worker)
        thr.daemon = True
        thr.start()
        
        bg_state["active_task"] = "syncing"
        bg_state["thread"] = thr
        bg_state["log_file"] = SYNC_LOG_PATH
        bg_state["error_msg"] = None
        
        return jsonify({"message": "Neon Postgres synchronization launched in background."})
    except Exception as e:
        bg_state["error_msg"] = f"Failed to launch sync: {e}"
        return jsonify({"error": str(e)}), 500


@actions_bp.route('/api/action/update', methods=['POST'])
def start_update():
    global bg_state
    # Bypass default page refresh/cooldown (30s) but use 2s to avoid double-clicking
    success = trigger_background_update(cooldown_seconds=2)
    if success:
        return jsonify({"message": "Database update successfully launched in background."})
    else:
        check_active_tasks()
        if bg_state["active_task"] != "idle":
            return jsonify({"error": f"Another task ({bg_state['active_task']}) is already running."}), 400
        else:
            return jsonify({"error": "Updater is on cooldown. Please wait a moment."}), 429


@actions_bp.route('/api/action/update_views', methods=['POST'])
def start_views_update():
    period = request.json.get("period", "1m") if request.is_json else request.args.get("period", "1m")
    success = trigger_background_views_update(period)
    if success:
        return jsonify({"message": f"Views update process ({period}) successfully launched in background."})
    else:
        check_active_tasks()
        return jsonify({"error": f"Another task ({bg_state['active_task']}) is already running."}), 400


@actions_bp.route('/api/action/status', methods=['GET'])
def get_action_status():
    check_active_tasks()
    
    logs = ""
    log_path = bg_state["log_file"]
    
    if log_path and os.path.exists(log_path):
        try:
            # Read last 50 lines of logs
            with open(log_path, 'r') as f:
                lines = f.readlines()
                logs = "".join(lines[-50:])
        except Exception as e:
            logs = f"Error reading logs: {e}"
            
    return jsonify({
        "status": bg_state["active_task"],
        "error": bg_state["error_msg"],
        "logs": logs
    })


# ── Terminal PTY Console Endpoints ────────────────────────────────────

# Terminal session status
session_lock = threading.RLock()
terminal_session = {
    "fd": None,
    "pid": None,
    "active": False
}

def cleanup_terminal():
    """Kills the active shell process and closes PTY file descriptors."""
    global terminal_session
    with session_lock:
        fd = terminal_session["fd"]
        pid = terminal_session["pid"]
        terminal_session["active"] = False
        terminal_session["fd"] = None
        terminal_session["pid"] = None
        
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass
                
        if pid is not None:
            import signal
            import time
            try:
                w_pid, status = os.waitpid(pid, os.WNOHANG)
                if w_pid == 0:
                    os.kill(pid, signal.SIGTERM)
                    for _ in range(10):
                        time.sleep(0.05)
                        w_pid, status = os.waitpid(pid, os.WNOHANG)
                        if w_pid != 0:
                            break
                    else:
                        os.kill(pid, signal.SIGKILL)
                        os.waitpid(pid, 0)
            except OSError:
                pass

def start_terminal():
    global terminal_session
    with session_lock:
        if terminal_session["active"] and terminal_session["pid"] is not None:
            try:
                pid, status = os.waitpid(terminal_session["pid"], os.WNOHANG)
                if pid == 0:
                    return
            except OSError:
                pass
            cleanup_terminal()
            
        env = os.environ.copy()
        venv_bin = os.path.join(root_dir, "venv_auto", "bin")
        env["PATH"] = f"{venv_bin}:{env.get('PATH', '')}"
        env["VIRTUAL_ENV"] = os.path.join(root_dir, "venv_auto")
        env["PYTHONPATH"] = root_dir
        env["TERM"] = "xterm-256color"
        
        import pty
        pid, fd = pty.fork()
        if pid == 0:
            os.chdir(root_dir)
            shell = "/bin/zsh" if os.path.exists("/bin/zsh") else "/bin/bash"
            try:
                os.execve(shell, [shell, "-i"], env)
            except Exception:
                try:
                    os.execve("/bin/bash", ["/bin/bash", "-i"], env)
                except Exception:
                    os.execv("/bin/sh", ["/bin/sh"])
        else:
            terminal_session["fd"] = fd
            terminal_session["pid"] = pid
            terminal_session["active"] = True
            
            # Set fd non-blocking
            import fcntl
            fl = fcntl.fcntl(fd, fcntl.F_GETFL)
            fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)


@actions_bp.route('/api/terminal/stream')
def terminal_stream():
    start_terminal()
    
    import select
    import base64
    import time
    
    def generate():
        fd = terminal_session["fd"]
        last_heartbeat = time.time()
        try:
            while terminal_session["active"] and terminal_session["fd"] == fd:
                r, _, _ = select.select([fd], [], [], 0.05)
                if fd in r:
                    try:
                        data = os.read(fd, 4096)
                        if not data:
                            break
                        b64_data = base64.b64encode(data).decode('ascii')
                        yield f"data: {b64_data}\n\n"
                        last_heartbeat = time.time()
                    except OSError:
                        break
                
                # Check heartbeat interval
                now = time.time()
                if now - last_heartbeat > 15:
                    yield ": ping\n\n"
                    last_heartbeat = now
        except (GeneratorExit, Exception):
            pass
        finally:
            if terminal_session["fd"] == fd:
                cleanup_terminal()
            
    return Response(generate(), mimetype='text/event-stream')


def trigger_server_shutdown():
    import signal
    import time
    
    print("[*] Shutdown requested. Terminating background scrapers and Flask server...")
    
    # Run scripts/manage_processes.py to kill child worker tasks
    try:
        import subprocess
        subprocess.run([sys.executable, 'scripts/manage_processes.py', '--skip-web'])
    except Exception as e:
        print(f"Failed to run process manager cleanup: {e}")
        
    def perform_kill():
        time.sleep(1.0)
        pid = os.getpid()
        ppid = os.getppid()
        if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
            try:
                os.kill(ppid, signal.SIGTERM)
            except Exception:
                pass
        try:
            os.kill(pid, signal.SIGTERM)
        except Exception:
            pass
            
    threading.Thread(target=perform_kill, daemon=True).start()


@actions_bp.route('/api/terminal/input', methods=['POST'])
def terminal_input():
    if not terminal_session["active"] or terminal_session["fd"] is None:
        return jsonify({"error": "Terminal session is not active."}), 400
        
    data = request.json or {}
    msg = data.get("input", "")
    if msg:
        if '\x11' in msg:  # Ctrl+Q byte
            trigger_server_shutdown()
            return jsonify({"message": "Shutdown triggered via terminal input"}), 200
        try:
            os.write(terminal_session["fd"], msg.encode('utf-8'))
        except OSError as e:
            return jsonify({"error": f"Failed to write to terminal: {e}"}), 500
            
    return '', 204


@actions_bp.route('/api/terminal/resize', methods=['POST'])
def terminal_resize():
    if not terminal_session["active"] or terminal_session["fd"] is None:
        return jsonify({"error": "Terminal session is not active."}), 400
        
    data = request.json or {}
    cols = int(data.get("cols", 80))
    rows = int(data.get("rows", 24))
    
    import fcntl
    import termios
    import struct
    
    try:
        s = struct.pack('HHHH', rows, cols, 0, 0)
        fcntl.ioctl(terminal_session["fd"], termios.TIOCSWINSZ, s)
    except Exception as e:
        return jsonify({"error": f"Failed to resize terminal: {e}"}), 500
        
    return '', 204


@actions_bp.route('/api/agent/models', methods=['GET'])
def agent_models():
    """Returns available AI models from the configured provider."""
    try:
        from app.services.agent import AgentService
        provider = request.args.get("provider", "gemini")
        models = AgentService.list_models(provider=provider)
        return jsonify({"models": models})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@actions_bp.route('/api/agent/chat', methods=['POST'])
def agent_chat():
    """Legacy non-streaming chat endpoint (kept for compatibility)."""
    data = request.json or {}
    message = data.get("message", "").strip()
    if not message:
        return jsonify({"error": "Message content cannot be empty."}), 400

    channel_ids = data.get("channel_ids") or []
    start_date  = data.get("start_date", "")
    end_date    = data.get("end_date", "")
    provider    = data.get("provider", "gemini")
    model_id    = data.get("model_id") or None
    role        = data.get("role", "admin")

    try:
        from app.services.agent import AgentService
        context_override = data.get("context_override")
        if context_override:
            ctx = context_override
        else:
            ctx = AgentService.build_dashboard_context(
                channel_ids=channel_ids,
                start_date=start_date,
                end_date=end_date
            )
        # Collect streamed text into a single string
        full_text = ""
        for chunk in AgentService.stream_chat_response(message, ctx, provider=provider, model_id=model_id, role=role):
            if chunk.startswith("data: [DONE]"):
                break
            if chunk.startswith("data: "):
                try:
                    import json as _json
                    obj = _json.loads(chunk[len("data: "):].strip())
                    if "text" in obj:
                        full_text += obj["text"]
                    elif "error" in obj:
                        return jsonify({"error": obj["error"]}), 500
                except Exception:
                    pass
        return jsonify({"response": full_text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@actions_bp.route('/api/agent/chat/stream', methods=['POST'])
def agent_chat_stream():
    """Streaming SSE chat endpoint."""
    data = request.json or {}
    message = data.get("message", "").strip()
    if not message:
        return jsonify({"error": "Message content cannot be empty."}), 400

    channel_ids = data.get("channel_ids") or []
    start_date  = data.get("start_date", "")
    end_date    = data.get("end_date", "")
    provider    = data.get("provider", "gemini")
    model_id    = data.get("model_id") or None
    role        = data.get("role", "admin")

    from app.services.agent import AgentService
    from flask import stream_with_context

    context_override = data.get("context_override")
    if context_override:
        ctx = context_override
    else:
        ctx = AgentService.build_dashboard_context(
            channel_ids=channel_ids,
            start_date=start_date,
            end_date=end_date
        )

    def generate():
        yield from AgentService.stream_chat_response(message, ctx, provider=provider, model_id=model_id, role=role)

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )


@actions_bp.route('/api/action/shutdown', methods=['POST'])
def actions_shutdown():
    trigger_server_shutdown()
    return jsonify({"message": "Server shutting down..."}), 200

