#!/usr/bin/env python3
import sys
import argparse
import subprocess
import json
import re
from datetime import datetime, timedelta
from pathlib import Path

BACKLOG_FILE = Path("swarm_backlog.json")

def update_backlog_status(task_id: str, new_status: str, msg: str = ""):
    if not BACKLOG_FILE.exists():
        return
    try:
        with open(BACKLOG_FILE, "r") as f:
            backlog = json.load(f)
        
        for task in backlog:
            if task.get("id") == task_id:
                task["status"] = new_status
                task["last_message"] = msg
                task["updated_at"] = datetime.now().isoformat()
                
        with open(BACKLOG_FILE, "w") as f:
            json.dump(backlog, f, indent=2)
    except Exception as e:
        print(f"[SwarmInvoke] Error updating backlog: {e}", file=sys.stderr)

def main():
    parser = argparse.ArgumentParser(description="Invoke Swarm Worker safely.")
    parser.add_argument("--target", required=True, choices=["claude", "codex", "test"], help="Target agent CLI")
    parser.add_argument("--task_id", required=True, help="Task ID from swarm_backlog.json")
    parser.add_argument("--cmd_args", default="", help="Arguments to pass to the agent")
    args = parser.parse_args()

    # Determine command
    if args.target == "claude":
        cmd = ["claude"] + args.cmd_args.split()
    elif args.target == "codex":
        cmd = ["codex"] + args.cmd_args.split()
    elif args.target == "test":
        # For testing the limit logic
        cmd = ["echo", "Error: Rate limit exceeded. Quota exhausted."]
    else:
        print("Unknown target")
        sys.exit(1)

    print(f"[SwarmInvoke] Starting {args.target} for task {args.task_id}...")
    update_backlog_status(args.task_id, "running", "Process spawned")

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, # Merge stderr into stdout for easier parsing
            text=True
        )

        limit_hit = False
        limit_regex = re.compile(r"(rate\s*limit|quota\s*exhausted|limit\s*exceeded)", re.IGNORECASE)

        for line in process.stdout:
            print(f"[{args.target}] {line}", end="")
            if limit_regex.search(line):
                limit_hit = True
                process.terminate()
                break

        process.wait()

        if limit_hit:
            resume_time = datetime.now() + timedelta(hours=2) # Default 2 hours assumption
            msg = f"Limit exhausted. Paused. Resume estimated at {resume_time.isoformat()}"
            print(f"\n[SwarmInvoke] {msg}")
            update_backlog_status(args.task_id, "pending_limit", msg)
            sys.exit(429) # HTTP 429 Too Many Requests representation
        elif process.returncode == 0:
            print(f"\n[SwarmInvoke] Task completed successfully.")
            update_backlog_status(args.task_id, "completed", "Success")
            sys.exit(0)
        else:
            print(f"\n[SwarmInvoke] Task failed with exit code {process.returncode}.")
            update_backlog_status(args.task_id, "failed", f"Exit code {process.returncode}")
            sys.exit(process.returncode)

    except FileNotFoundError:
        msg = f"Command for target '{args.target}' not found on PATH."
        print(f"[SwarmInvoke] {msg}")
        update_backlog_status(args.task_id, "failed", msg)
        sys.exit(127)

if __name__ == "__main__":
    main()
