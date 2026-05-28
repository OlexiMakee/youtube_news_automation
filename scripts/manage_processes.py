#!/usr/bin/env python3
"""
scripts/manage_processes.py — Application process manager.

Automatically detects and terminates running background app processes
(web_app.py, update_db.py, update_views.py, scrape_multi.py, init_db.py).
Lists other active Python processes and offers an interactive menu to close them.
"""
import os
import sys
import signal
import subprocess

# Specific script names related to our application to target for auto-termination
APP_SCRIPTS = [
    "web_app.py",
    "update_db.py",
    "update_views.py",
    "scrape_multi.py",
    "init_db.py"
]

if "--skip-web" in sys.argv:
    if "web_app.py" in APP_SCRIPTS:
        APP_SCRIPTS.remove("web_app.py")


def get_running_python_processes():
    """Parses 'ps aux' to extract running Python processes."""
    processes = []
    try:
        # Run 'ps aux' to list all processes on macOS
        output = subprocess.check_output(["ps", "aux"], text=True)
        lines = output.split('\n')
        
        # Line format: USER PID %CPU %MEM VSZ RSS TT STAT STARTED TIME COMMAND
        for line in lines[1:]:
            if not line.strip():
                continue
            parts = line.split(None, 10)
            if len(parts) < 11:
                continue
            
            pid_str = parts[1]
            command = parts[10]
            
            # Check if it's a Python process
            if "python" in command.lower() or "sys.executable" in command:
                # Exclude the current manager process itself and its parent process
                if pid_str in [str(os.getpid()), str(os.getppid())]:
                    continue
                processes.append({
                    "pid": int(pid_str),
                    "command": command
                })
    except Exception as e:
        print(f"[!] Failed to retrieve running processes: {e}")
    return processes


def main():
    print("=" * 60)
    print(f"{'APPLICATION PROCESS MANAGER':^60}")
    print("=" * 60)
    
    processes = get_running_python_processes()
    
    app_processes = []
    other_python_processes = []
    
    for p in processes:
        is_app = False
        for script in APP_SCRIPTS:
            if script in p["command"]:
                is_app = True
                break
        if is_app:
            app_processes.append(p)
        else:
            other_python_processes.append(p)
            
    # Step 1: Automatically terminate app background processes
    if app_processes:
        print("[*] Automatically terminating background app processes...")
        for p in app_processes:
            print(f"    - Killing PID {p['pid']}: {p['command'][:70]}...")
            try:
                os.kill(p["pid"], signal.SIGTERM)
            except ProcessLookupError:
                pass
            except Exception as e:
                print(f"      [!] Error: {e}")
        print("[✓] Background app processes terminated.")
    else:
        print("[i] No background app processes found.")
        
    print("-" * 60)
    
    # Step 2: Show list of other python processes and offer to close them
    if other_python_processes:
        print("Other running Python processes / servers:")
        for idx, p in enumerate(other_python_processes, 1):
            print(f"  {idx}. [PID {p['pid']}] {p['command'][:90]}")
        print("-" * 60)
        
        if not sys.stdin.isatty() or "--non-interactive" in sys.argv:
            print("[i] Non-interactive mode: skipping process termination menu.")
        else:
            try:
                ans = input("Enter numbers to close (e.g., 1, 2 or raw PIDs), or press Enter to skip:\n> ").strip()
                if ans:
                    targets = [x.strip() for x in ans.split(",")]
                    for target in targets:
                        pid_to_kill = None
                        if target.isdigit():
                            val = int(target)
                            if 1 <= val <= len(other_python_processes):
                                pid_to_kill = other_python_processes[val - 1]["pid"]
                            else:
                                pid_to_kill = val
                        
                        if pid_to_kill:
                            print(f"[*] Terminating process {pid_to_kill}...")
                            try:
                                os.kill(pid_to_kill, signal.SIGTERM)
                                print(f"[✓] Process {pid_to_kill} terminated.")
                            except ProcessLookupError:
                                print(f"[!] Process {pid_to_kill} not found.")
                            except Exception as e:
                                print(f"[!] Failed to terminate {pid_to_kill}: {e}")
            except KeyboardInterrupt:
                print("\n[i] Skipping interactive menu.")
    else:
        print("[i] No other Python processes found.")
        
    print("\nProcess cleanup complete.")


if __name__ == "__main__":
    main()
