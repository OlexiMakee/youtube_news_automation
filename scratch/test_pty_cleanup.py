import os
import sys
import time
import unittest


# Add root dir to sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import scraper.utils as utils
utils.load_env()

from app import create_app
from app.routes.actions import terminal_session, cleanup_terminal, start_terminal

class TestPTYCleanup(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()
        
    def test_pty_cleanup_flow(self):
        print("[*] Testing PTY terminal session spawning and cleanup...")
        
        # Clean up any existing terminal first
        cleanup_terminal()
        self.assertFalse(terminal_session["active"])
        
        # Get terminal stream (which calls start_terminal)
        res = self.client.get('/api/terminal/stream')
        self.assertEqual(res.status_code, 200)
        
        # Verify terminal session is active and has a pid
        self.assertTrue(terminal_session["active"])
        pid = terminal_session["pid"]
        self.assertIsNotNone(pid)
        
        # Verify the process is running
        try:
            os.kill(pid, 0)
            process_running = True
        except OSError:
            process_running = False
        self.assertTrue(process_running)
        print(f"    PTY spawned process (PID {pid}) is running.")
        
        # Simulate generator client disconnect (call cleanup_terminal)
        print("[*] Simulating client disconnect / SSE stream close...")
        cleanup_terminal()
        
        # Verify session state is reset
        self.assertFalse(terminal_session["active"])
        self.assertIsNone(terminal_session["pid"])
        self.assertIsNone(terminal_session["fd"])
        
        # Give it a tiny bit of time to terminate
        time.sleep(0.2)
        
        # Verify the process has been killed
        try:
            os.kill(pid, 0)
            process_running = True
        except OSError:
            process_running = False
        self.assertFalse(process_running)
        print("    Success: PTY process was reaped and is no longer running.")

if __name__ == '__main__':
    unittest.main()
