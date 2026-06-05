import os
import sys
import json
import subprocess
import threading
from datetime import datetime
from flask import Blueprint, jsonify, request, Response
from app.services.rbac import (
    ADMIN_SESSION_COOKIE,
    ADMIN_SESSION_TTL_SECONDS,
    assistant_role_for_request,
    configured_admin_token,
    create_admin_session,
    current_request_role,
    destroy_admin_session,
    has_admin_access,
    has_valid_admin_session,
    require_admin as _admin_required,
)
from app.state import (
    background_daemons_disabled,
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
PROPOSAL_STATUSES = {"active", "done", "deferred", "rejected"}


def _proposal_inbox_path():
    proposals_dir = os.path.join(root_dir, "agent_proposals")
    os.makedirs(proposals_dir, exist_ok=True)
    return os.path.join(proposals_dir, "admin_proposals.jsonl")


def _read_proposal_rows():
    proposals_path = _proposal_inbox_path()
    if not os.path.exists(proposals_path):
        return []

    rows = []
    with open(proposals_path, "r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                row = {
                    "id": f"invalid-{lineno}",
                    "ts": None,
                    "role": "system",
                    "type": "bug",
                    "status": "active",
                    "el": "admin_proposals.jsonl",
                    "src": "agent_proposals/admin_proposals.jsonl",
                    "desc": f"Invalid JSONL row at line {lineno}"
                }
            row.setdefault("status", "active")
            rows.append(row)
    return rows


def _write_proposal_rows(rows):
    proposals_path = _proposal_inbox_path()
    tmp_path = f"{proposals_path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    os.replace(tmp_path, proposals_path)


@actions_bp.route('/api/auth/status', methods=['GET'])
def auth_status():
    """Return non-secret request auth status for UI gating."""
    token_configured = bool(configured_admin_token())
    return jsonify({
        "ok": True,
        "token_configured": token_configured,
        "admin": has_admin_access(request),
        "role": current_request_role(request),
        "session_authenticated": has_valid_admin_session(request),
        "auth_methods": ["X-Admin-Token", "Authorization: Bearer", "HttpOnly session cookie"] if token_configured else []
    })


@actions_bp.route('/api/auth/session', methods=['POST'])
def auth_session_create():
    """Mint an HttpOnly admin session from the configured admin token."""
    session = create_admin_session(request)
    if session is None:
        return jsonify({"error": "Admin access required."}), 403

    response = jsonify({
        "ok": True,
        "admin": True,
        "role": "admin",
        "expires_at": session["expires_at"]
    })
    response.set_cookie(
        ADMIN_SESSION_COOKIE,
        session["id"],
        max_age=ADMIN_SESSION_TTL_SECONDS,
        httponly=True,
        samesite="Lax",
        secure=request.is_secure
    )
    return response


@actions_bp.route('/api/auth/session', methods=['DELETE'])
def auth_session_destroy():
    """Clear the current server-side admin session."""
    destroyed = destroy_admin_session(request)
    response = jsonify({"ok": True, "destroyed": destroyed})
    response.delete_cookie(ADMIN_SESSION_COOKIE, samesite="Lax", secure=request.is_secure)
    return response


@actions_bp.route('/api/action/add_channel', methods=['POST'])
@_admin_required
def add_channel_route():
    global bg_state
    if background_daemons_disabled():
        return jsonify({"error": "Background daemons are disabled."}), 503

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
@_admin_required
def start_scrape():
    global bg_state
    if background_daemons_disabled():
        return jsonify({"error": "Background daemons are disabled."}), 503

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
@_admin_required
def start_sync():
    global bg_state
    if background_daemons_disabled():
        return jsonify({"error": "Background daemons are disabled."}), 503

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
@_admin_required
def start_update():
    global bg_state
    if background_daemons_disabled():
        return jsonify({"error": "Background daemons are disabled."}), 503

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
@_admin_required
def start_views_update():
    if background_daemons_disabled():
        return jsonify({"error": "Background daemons are disabled."}), 503

    period = request.json.get("period", "1m") if request.is_json else request.args.get("period", "1m")
    success = trigger_background_views_update(period)
    if success:
        return jsonify({"message": f"Views update process ({period}) successfully launched in background."})
    else:
        check_active_tasks()
        return jsonify({"error": f"Another task ({bg_state['active_task']}) is already running."}), 400


@actions_bp.route('/api/action/status', methods=['GET'])
@_admin_required
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


@actions_bp.route('/api/admin/health', methods=['GET'])
@_admin_required
def admin_health():
    """Return non-secret host/app health metrics for the admin UI."""
    from app.services.health import build_admin_health

    return jsonify(build_admin_health(root_dir, bg_state))


@actions_bp.route('/api/admin/quota-metrics', methods=['GET'])
@_admin_required
def admin_quota_metrics():
    """Return aggregated LLM run metrics (cost, tokens, success/error rates) from memory_os.db."""
    import sqlite3
    db_path = os.path.join(root_dir, "data", "memory_os.db")
    
    time_range = request.args.get("time_range", "24h")
    if time_range not in ("24h", "7d", "30d", "all"):
        time_range = "24h"

    where_clause = ""
    if time_range == "24h":
        where_clause = "WHERE created_at >= datetime('now', '-1 day', 'localtime')"
    elif time_range == "7d":
        where_clause = "WHERE created_at >= datetime('now', '-7 days', 'localtime')"
    elif time_range == "30d":
        where_clause = "WHERE created_at >= datetime('now', '-30 days', 'localtime')"

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        # Check if table exists first to avoid crash on empty DB initialization
        table_exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='memory_os_telemetry'"
        ).fetchone() is not None

        if not table_exists:
            return jsonify({
                "summary": {
                    "total_cost": 0.0, "total_input_tokens": 0, "total_output_tokens": 0,
                    "total_cached_tokens": 0, "total_runs": 0, "success_count": 0,
                    "error_count": 0, "avg_latency": 0.0
                },
                "model_breakdown": [],
                "recent_errors": []
            })

        summary_query = f"""
            SELECT 
                SUM(cost) as total_cost,
                SUM(input_tokens) as total_input_tokens,
                SUM(output_tokens) as total_output_tokens,
                SUM(cached_tokens) as total_cached_tokens,
                COUNT(*) as total_runs,
                SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success_count,
                SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as error_count,
                AVG(latency_ms) as avg_latency
            FROM memory_os_telemetry
            {where_clause}
        """
        row = conn.execute(summary_query).fetchone()
        summary = dict(row) if row else {}

        # Fill default values
        for key in ["total_cost", "total_input_tokens", "total_output_tokens", "total_cached_tokens", "total_runs", "success_count", "error_count", "avg_latency"]:
            if summary.get(key) is None:
                summary[key] = 0.0 if key in ("total_cost", "avg_latency") else 0

        model_query = f"""
            SELECT 
                model_id,
                provider_id,
                SUM(cost) as cost,
                SUM(input_tokens) as input_tokens,
                SUM(output_tokens) as output_tokens,
                COUNT(*) as run_count,
                SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success_count,
                SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as error_count
            FROM memory_os_telemetry
            {where_clause}
            GROUP BY model_id, provider_id
            ORDER BY cost DESC
        """
        model_breakdown = [dict(r) for r in conn.execute(model_query).fetchall()]

        error_where = f"{where_clause} AND status = 'error'" if where_clause else "WHERE status = 'error'"
        error_query = f"""
            SELECT id, prompt_name, provider_id, model_id, status, created_at
            FROM memory_os_telemetry
            {error_where}
            ORDER BY id DESC
            LIMIT 5
        """
        recent_errors = [dict(r) for r in conn.execute(error_query).fetchall()]

        return jsonify({
            "summary": summary,
            "model_breakdown": model_breakdown,
            "recent_errors": recent_errors
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@actions_bp.route('/api/admin/system-metrics', methods=['GET'])
@_admin_required
def admin_system_metrics():
    """Return recent host metrics (CPU, RAM, Disk IO, HTTP sessions) from youtube_news.db."""
    import sqlite3
    db_path = os.path.join(root_dir, "data", "youtube_news.db")
    limit = request.args.get("limit", 50)
    try:
        limit = int(limit)
    except ValueError:
        limit = 50

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        table_exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='system_metrics'"
        ).fetchone() is not None

        if not table_exists:
            return jsonify({"metrics": []})

        query = """
            SELECT timestamp, cpu_percent, ram_mb_used, disk_io_mb, http_sessions_active
            FROM system_metrics
            ORDER BY timestamp DESC
            LIMIT ?
        """
        rows = conn.execute(query, (limit,)).fetchall()
        metrics = [dict(r) for r in reversed(rows)]
        return jsonify({"metrics": metrics})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@actions_bp.route('/api/widgets/registry', methods=['GET'])
def widgets_registry():
    """Return supported dashboard widget types gated by progressive entitlements."""
    from app.services.widgets import widget_registry
    from app.state import get_entitlement_state

    entitlements = get_entitlement_state()
    reg = widget_registry()
    filtered_types = []

    for wtype in reg.get("types", []):
        if wtype["type"] == "channel-analytics" and entitlements.get("ready_workspace"):
            filtered_types.append(wtype)
        elif wtype["type"] == "anomaly-alerts" and entitlements.get("dense_workspace"):
            filtered_types.append(wtype)
        elif wtype["type"] == "daily-brief" and entitlements.get("ready_workspace"):
            filtered_types.append(wtype)
        elif wtype["type"] == "minified-stats" and entitlements.get("ready_workspace"):
            filtered_types.append(wtype)
        elif wtype["type"] == "entity-timeline" and entitlements.get("ready_workspace"):
            filtered_types.append(wtype)
        elif wtype["type"] == "system-status" and entitlements.get("ready_workspace"):
            filtered_types.append(wtype)
        elif wtype["type"] == "cost-quota" and entitlements.get("operator_runtime"):
            filtered_types.append(wtype)

    reg["types"] = filtered_types
    return jsonify(reg)


@actions_bp.route('/api/widgets/state', methods=['GET'])
@_admin_required
def widgets_state_get():
    """Return persisted dashboard widget layout/state."""
    from app.services.widgets import load_widget_state

    return jsonify(load_widget_state(root_dir))


@actions_bp.route('/api/widgets/state', methods=['PUT'])
@_admin_required
def widgets_state_put():
    """Persist dashboard widget layout/state."""
    from app.services.widgets import save_widget_state

    data = request.json or {}
    try:
        state = save_widget_state(root_dir, data.get("widgets", []))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"ok": True, **state})


@actions_bp.route('/api/widgets/layouts', methods=['GET'])
@_admin_required
def widgets_layouts_get():
    """Return all available layout presets."""
    from app.services.widgets import load_layouts
    return jsonify({"layouts": load_layouts(root_dir)})


@actions_bp.route('/api/widgets/layouts', methods=['POST'])
@_admin_required
def widgets_layouts_create():
    """Create a new named layout preset."""
    from app.services.widgets import create_layout
    data = request.json or {}
    name = str(data.get("name") or "").strip()
    is_default = bool(data.get("is_default"))
    if not name:
        return jsonify({"error": "Layout name is required"}), 400
    try:
        layout = create_layout(root_dir, name, is_default)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"ok": True, "layout": layout})


@actions_bp.route('/api/widgets/layouts/<int:layout_id>', methods=['DELETE'])
@_admin_required
def widgets_layouts_delete(layout_id):
    """Delete a layout preset."""
    from app.services.widgets import delete_layout
    try:
        ok = delete_layout(root_dir, layout_id)
        if not ok:
            return jsonify({"error": "Layout not found"}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"ok": True})


@actions_bp.route('/api/widgets/layouts/activate/<int:layout_id>', methods=['POST'])
@_admin_required
def widgets_layouts_activate(layout_id):
    """Set a layout preset as active/default."""
    from app.services.widgets import activate_layout
    ok = activate_layout(root_dir, layout_id)
    if not ok:
        return jsonify({"error": "Layout not found"}), 404
    return jsonify({"ok": True})



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
@_admin_required
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
@_admin_required
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
@_admin_required
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
@_admin_required
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
@_admin_required
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
    role        = assistant_role_for_request(data.get("role"), request)
    history     = data.get("history") or []

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
        for chunk in AgentService.stream_chat_response(message, ctx, provider=provider, model_id=model_id, role=role, history=history):
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
@_admin_required
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
    role        = assistant_role_for_request(data.get("role"), request)
    history     = data.get("history") or []

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
        yield from AgentService.stream_chat_response(message, ctx, provider=provider, model_id=model_id, role=role, history=history)

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )


@actions_bp.route('/api/proposals', methods=['GET'])
@_admin_required
def list_agent_proposals():
    """List admin proposal inbox rows. Default hides completed rows."""
    status_filter = (request.args.get("status") or "active").strip().lower()
    if status_filter != "all" and status_filter not in PROPOSAL_STATUSES:
        return jsonify({"error": "status must be one of active, done, deferred, rejected, all."}), 400

    rows = _read_proposal_rows()
    if status_filter != "all":
        rows = [row for row in rows if row.get("status", "active") == status_filter]

    return jsonify({"ok": True, "count": len(rows), "proposals": rows})


@actions_bp.route('/api/proposals/submit', methods=['POST'])
@_admin_required
def submit_agent_proposal():
    """Append contextual UI feedback to the admin proposals JSONL inbox."""
    data = request.json or {}
    proposal_type = (data.get("type") or "").strip().lower()
    if proposal_type not in {"bug", "feature"}:
        return jsonify({"error": "type must be 'bug' or 'feature'."}), 400

    desc = (data.get("desc") or "").strip()
    if not desc:
        return jsonify({"error": "desc is required."}), 400

    workflow = (data.get("workflow") or "product").strip().lower()
    if workflow not in {"product", "memory_os"}:
        return jsonify({"error": "workflow must be 'product' or 'memory_os'."}), 400

    role_tier = (data.get("role_tier") or "admin").strip().lower()
    valid_roles = {"developer", "automated", "master_admin", "admin", "user"}
    if role_tier not in valid_roles:
        return jsonify({"error": f"role_tier must be one of {', '.join(sorted(valid_roles))}."}), 400

    now = int(datetime.now().timestamp() * 1000)
    row = {
        "id": now,
        "ts": now,
        "role": "admin",
        "type": proposal_type,
        "status": "active",
        "priority": (data.get("priority") or "").strip() or None,
        "el": (data.get("el") or "").strip(),
        "src": (data.get("src") or "").strip(),
        "desc": desc,
        "workflow": workflow,
        "role_tier": role_tier
    }
    row = {key: value for key, value in row.items() if value is not None}

    try:
        with open(_proposal_inbox_path(), "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    except OSError as e:
        return jsonify({"error": f"Failed to write proposal: {e}"}), 500

    return jsonify({"ok": True, "proposal": row})


@actions_bp.route('/api/proposals/status', methods=['POST'])
@_admin_required
def update_agent_proposal_status():
    """Update a proposal row status so completed items stop resurfacing."""
    data = request.json or {}
    proposal_id = data.get("id")
    status = (data.get("status") or "").strip().lower()
    if proposal_id is None:
        return jsonify({"error": "id is required."}), 400
    if status not in PROPOSAL_STATUSES:
        return jsonify({"error": "status must be one of active, done, deferred, rejected."}), 400

    rows = _read_proposal_rows()
    now = int(datetime.now().timestamp() * 1000)
    found = False
    for row in rows:
        if str(row.get("id")) != str(proposal_id):
            continue
        row["status"] = status
        row["status_updated_at"] = now
        note = (data.get("note") or "").strip()
        if note:
            row["status_note"] = note
        found = True
        break

    if not found:
        return jsonify({"error": "proposal not found."}), 404

    try:
        _write_proposal_rows(rows)
    except OSError as e:
        return jsonify({"error": f"Failed to update proposal: {e}"}), 500

    return jsonify({"ok": True, "id": proposal_id, "status": status})


@actions_bp.route('/api/chat/clear-context', methods=['POST'])
@_admin_required
def chat_clear_context():
    """Compatibility hook for clearing server-side chat context."""
    return jsonify({
        "ok": True,
        "message": "Chat context cleared."
    })


@actions_bp.route('/api/chat/feedback', methods=['POST'])
@_admin_required
def chat_feedback():
    """Record like/dislike feedback for provider efficiency scoring."""
    data = request.json or {}
    feedback_type = (data.get("feedback_type") or "").strip().lower()
    if not feedback_type and data.get("rating") is not None:
        try:
            feedback_type = "like" if int(data.get("rating")) > 0 else "dislike"
        except (TypeError, ValueError):
            feedback_type = ""
    if feedback_type not in {"like", "dislike"}:
        return jsonify({"error": "feedback_type must be 'like'/'dislike' or rating must be 1/-1."}), 400

    provider_id = (data.get("provider_id") or data.get("provider") or "").strip()
    model_id = (data.get("model_id") or data.get("model") or "").strip()
    if not provider_id:
        return jsonify({"error": "provider_id is required."}), 400
    if not model_id:
        return jsonify({"error": "model_id is required."}), 400

    prompt_text = (data.get("prompt_text") or data.get("prompt") or "").strip()
    response_text = (data.get("response_text") or data.get("response") or "").strip()
    latency_ms = data.get("latency_ms") or 0
    try:
        latency_ms = int(latency_ms)
    except (TypeError, ValueError):
        return jsonify({"error": "latency_ms must be an integer."}), 400

    from app.services.cloud_rotation import get_rotation_engine
    engine = get_rotation_engine()
    if engine is None:
        return jsonify({"error": "Cloud rotation engine is not initialized."}), 503

    ok = engine.record_feedback(
        model_id=model_id,
        provider_id=provider_id,
        prompt_text=prompt_text,
        response_text=response_text,
        feedback_type=feedback_type,
        latency_ms=latency_ms
    )
    if not ok:
        return jsonify({"error": "Feedback storage is unavailable."}), 503

    provider = engine.get_provider_by_id(provider_id)
    comment = (data.get("comment") or "").strip()

    # Save to User-Facing Memory OS
    try:
        import uuid
        import time
        from app.services.memory_os.core import MemoryOS

        memory_os = MemoryOS()
        memory_id = f"chat.feedback.{uuid.uuid4().hex[:8]}"

        content_lines = [
            f"Rating: {feedback_type}",
            f"Model: {model_id} ({provider_id})",
            f"User Prompt: {prompt_text}",
            f"Assistant Response: {response_text}"
        ]
        if comment:
            content_lines.append(f"User Comment: {comment}")

        content_str = "\n".join(content_lines)
        summary = f"Feedback: {comment}" if comment else f"Feedback on: {prompt_text[:60]}..."
        importance = 0.95 if feedback_type == "like" else 0.35
        if comment:
            importance += 0.05

        memory_os.add_or_update_memory(
            memory_id=memory_id,
            mem_type="chat_feedback",
            content=content_str,
            summary=summary,
            importance=importance,
            timestamp=int(time.time())
        )
    except Exception as e:
        print(f"[actions] Failed to write chat feedback to memory_os: {e}", file=sys.stderr)

    return jsonify({
        "ok": True,
        "provider_id": provider_id,
        "model_id": model_id,
        "feedback_type": feedback_type,
        "comment": comment if comment else None,
        "provider_efficiency": round(provider.efficiency_score, 2) if provider else None
    })


@actions_bp.route('/api/chat/report-quota', methods=['POST'])
@_admin_required
def chat_report_quota():
    """Record a provider quota/rate-limit pattern for future interception."""
    data = request.json or {}
    error_text = (
        data.get("error_text")
        or data.get("err_pattern")
        or data.get("response_text")
        or data.get("raw_output")
        or ""
    ).strip()
    if not error_text:
        return jsonify({"error": "error_text is required."}), 400

    provider_id = (data.get("provider_id") or data.get("provider") or "").strip() or None

    from app.services.cloud_rotation import get_rotation_engine
    engine = get_rotation_engine()
    if engine is None:
        return jsonify({"error": "Cloud rotation engine is not initialized."}), 503

    ok = engine.report_quota_error(error_text, provider_id=provider_id)
    if not ok:
        return jsonify({"error": "Quota report storage is unavailable."}), 503

    return jsonify({
        "ok": True,
        "provider_id": provider_id,
        "message": "Quota pattern recorded."
    })


@actions_bp.route('/api/action/shutdown', methods=['POST'])
@_admin_required
def actions_shutdown():
    trigger_server_shutdown()
    return jsonify({"message": "Server shutting down..."}), 200
