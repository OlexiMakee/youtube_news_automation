import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.governance import execute_watchers

def main():
    root_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    print(f"Starting Standalone Watcher Worker targeting {root_dir}...")
    
    while True:
        try:
            res = execute_watchers(root_dir)
            if res.get("total_run", 0) > 0:
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Ran {res['total_run']} watchers: {res['ran_watchers']}")
        except Exception as e:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Watcher worker error: {e}", file=sys.stderr)
            
        time.sleep(60)

if __name__ == "__main__":
    main()
