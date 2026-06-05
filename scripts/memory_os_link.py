#!/usr/bin/env python3
import json
import os
import argparse
from datetime import datetime
from pathlib import Path

# Assuming memory_os is parallel to the current project
DEFAULT_SDK_PATH = Path(os.environ.get("MEMORY_OS_PATH", Path(__file__).resolve().parent.parent.parent / "memory_os"))
INTEGRATION_DIR = DEFAULT_SDK_PATH / "integration"

def ensure_integration_dir():
    if not INTEGRATION_DIR.exists():
        print(f"Warning: SDK integration directory not found at {INTEGRATION_DIR}")
        print("Ensure memory_os is located alongside this project or MEMORY_OS_PATH is set.")
        return False
    return True

def report_bug(title: str, description: str, severity: str = "medium"):
    if not ensure_integration_dir(): return
    path = INTEGRATION_DIR / "bug_reports.jsonl"
    entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "title": title,
        "description": description,
        "severity": severity,
        "status": "open"
    }
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    print(f"Bug report submitted to {path.name}")

def request_feature(title: str, description: str, priority: str = "low"):
    if not ensure_integration_dir(): return
    path = INTEGRATION_DIR / "feature_requests.jsonl"
    entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "title": title,
        "description": description,
        "priority": priority,
        "status": "pending"
    }
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    print(f"Feature request submitted to {path.name}")

def read_changelog():
    if not ensure_integration_dir(): return
    path = INTEGRATION_DIR / "changelog.jsonl"
    if not path.exists() or path.stat().st_size == 0:
        print("No recent changes in memory_os.")
        return
        
    print("--- Memory OS Changelog ---")
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip(): continue
            try:
                data = json.loads(line)
                print(f"[{data.get('date', 'Unknown')}] {data.get('version', 'N/A')}: {data.get('summary', '')}")
            except json.JSONDecodeError:
                pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cross-Agent Communication Link to Memory OS SDK")
    subparsers = parser.add_subparsers(dest="command", required=True)

    bug_parser = subparsers.add_parser("bug", help="Report a bug to the SDK")
    bug_parser.add_argument("title")
    bug_parser.add_argument("description")
    bug_parser.add_argument("--severity", default="medium")

    feature_parser = subparsers.add_parser("feature", help="Propose a feature to the SDK")
    feature_parser.add_argument("title")
    feature_parser.add_argument("description")
    feature_parser.add_argument("--priority", default="low")

    changelog_parser = subparsers.add_parser("changelog", help="Read the SDK changelog")

    args = parser.parse_args()

    if args.command == "bug":
        report_bug(args.title, args.description, args.severity)
    elif args.command == "feature":
        request_feature(args.title, args.description, args.priority)
    elif args.command == "changelog":
        read_changelog()
