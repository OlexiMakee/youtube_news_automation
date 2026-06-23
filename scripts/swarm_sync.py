import os
import json
import time
import argparse
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
CONTEXT_DIR = WORKSPACE_ROOT / "agent_context"
PROPOSALS_DIR = WORKSPACE_ROOT / "agent_proposals"
LOCK_FILE = CONTEXT_DIR / ".orchestrator.lock"
BACKLOG_FILE = CONTEXT_DIR / "swarm_backlog.json"

def is_pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError as e:
        import errno
        if getattr(e, 'errno', None) == errno.EPERM:
            return True
        return False
    except ValueError:
        return False

def load_backlog():
    if not BACKLOG_FILE.exists():
        return {"unassigned": [], "in_progress": {}, "done": []}
    with open(BACKLOG_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {"unassigned": [], "in_progress": {}, "done": []}

def save_backlog(data):
    with open(BACKLOG_FILE, "w") as f:
        json.dump(data, f, indent=2)

def orchestrator_sync(agent_name: str):
    print(f"[{agent_name} - ORCHESTRATOR] Syncing backlog...")
    backlog = load_backlog()
    
    # 1. Scan proposals
    if PROPOSALS_DIR.exists():
        known_tasks = set(backlog["unassigned"]) | set(backlog["done"])
        for tasks in backlog["in_progress"].values():
            known_tasks.update(tasks)
            
        for filepath in PROPOSALS_DIR.glob("*.md"):
            task_id = filepath.name
            if task_id not in known_tasks and task_id != "INDEX.md":
                backlog["unassigned"].append(task_id)
                print(f"[{agent_name} - ORCHESTRATOR] Added new proposal to queue: {task_id}")
    
    # 2. Pick a task for the Orchestrator itself
    assigned_tasks = backlog["in_progress"].setdefault(agent_name, [])
    if not assigned_tasks and backlog["unassigned"]:
        task = backlog["unassigned"].pop(0)
        assigned_tasks.append(task)
        print(f"[{agent_name} - ORCHESTRATOR] Self-assigned task: {task}")
    
    save_backlog(backlog)
    
    if assigned_tasks:
        print(f"\n✅ Next Step: Proceed with task '{assigned_tasks[0]}'")
    else:
        print(f"\n✅ Swarm Backlog is empty. Orchestrator standing by.")

def worker_sync(agent_name: str, orchestrator_info: dict):
    print(f"[{agent_name} - WORKER] Orchestrator is active ({orchestrator_info.get('agent')} - PID {orchestrator_info.get('pid')}).")
    backlog = load_backlog()
    
    assigned_tasks = backlog["in_progress"].setdefault(agent_name, [])
    if not assigned_tasks and backlog["unassigned"]:
        task = backlog["unassigned"].pop(0)
        assigned_tasks.append(task)
        save_backlog(backlog)
        print(f"[{agent_name} - WORKER] Picked up new task: {task}")
    elif assigned_tasks:
        print(f"[{agent_name} - WORKER] Continuing existing task: {assigned_tasks[0]}")
    else:
        print(f"[{agent_name} - WORKER] No tasks available in unassigned queue.")
    
    if assigned_tasks:
        print(f"\n✅ Next Step: Proceed with task '{assigned_tasks[0]}'")
    else:
        print(f"\n✅ Swarm Backlog is empty. Worker standing by.")

def main():
    parser = argparse.ArgumentParser(description="Swarm Sync for Multi-Agent Orchestration")
    parser.add_argument("--agent", required=True, help="Name of the agent running this script")
    parser.add_argument("--complete", help="Mark a specific task ID as done")
    args = parser.parse_args()
    
    agent_name = args.agent
    parent_pid = os.getppid()
    
    # Handle task completion
    if args.complete:
        backlog = load_backlog()
        if agent_name in backlog["in_progress"] and args.complete in backlog["in_progress"][agent_name]:
            backlog["in_progress"][agent_name].remove(args.complete)
            if args.complete not in backlog["done"]:
                backlog["done"].append(args.complete)
            save_backlog(backlog)
            print(f"[{agent_name}] Marked task '{args.complete}' as done.")
            return

    # Check lock
    is_orchestrator = False
    lock_data = {}
    
    if LOCK_FILE.exists():
        try:
            with open(LOCK_FILE, "r") as f:
                lock_data = json.load(f)
        except Exception:
            lock_data = {}
            
    current_orch_pid = lock_data.get("pid")
    
    if not current_orch_pid or not is_pid_alive(current_orch_pid):
        is_orchestrator = True
    elif current_orch_pid == parent_pid and lock_data.get("agent") == agent_name:
        is_orchestrator = True

    if is_orchestrator:
        lock_data = {
            "agent": agent_name,
            "pid": parent_pid,
            "timestamp": time.time()
        }
        with open(LOCK_FILE, "w") as f:
            json.dump(lock_data, f, indent=2)
            
        orchestrator_sync(agent_name)
    else:
        worker_sync(agent_name, lock_data)

if __name__ == "__main__":
    main()
