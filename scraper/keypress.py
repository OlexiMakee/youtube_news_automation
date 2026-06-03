"""
Module for non-blocking keypress detection (keypress.py).

This module enables monitoring Spacebar/Enter keypresses during scraping execution
without stalling the main data collection flow. It provides the KeypressDetector class,
which automatically adapts to Windows and Unix-based (Linux/macOS) platforms.
"""

import sys
from abc import ABC, abstractmethod

# If on Unix-like system (macOS or Linux), import terminal I/O libraries
if sys.platform != "win32":
    import termios
    import tty
    import select


class BaseKeypressDetector(ABC):
    """
    Abstract base class for non-blocking keyboard input detectors.
    """

    @abstractmethod
    def check_space(self):
        """Checks if the user pressed the trigger key (Spacebar or Enter)."""
        pass

    @abstractmethod
    def restore(self):
        """Restores the terminal attributes to their original state."""
        pass


class KeypressDetector(BaseKeypressDetector):
    """
    Class that detects whether the user pressed the Spacebar or Enter in the console.
    Operates in a background non-blocking manner (execution does not block waiting for input).
    """

    def __init__(self, active=True):
        """
        Initializes the keypress detector.

        Parameters:
            active (bool): If True, activates the detector (only if the terminal supports interactive input).
        """
        # The detector operates only if input is routed to an interactive terminal (tty)
        self.active = active and sys.platform != "win32" and sys.stdin.isatty()
        if self.active:
            try:
                self.fd = sys.stdin.fileno()
                # Save existing terminal attributes to restore them at exit
                self.old_settings = termios.tcgetattr(self.fd)
                # Set terminal to cbreak mode (characters read immediately without waiting for Enter)
                tty.setcbreak(self.fd)
            except Exception:
                self.active = False
            
    def check_space(self):
        """
        Checks if the user pressed the Spacebar or Enter key.
        Non-blocking: if no target key was pressed, returns False.

        Returns:
            bool: True if Spacebar or Enter was pressed, False otherwise.
        """
        # Windows platform flow
        if sys.platform == "win32":
            try:
                import msvcrt
                has_trigger_key = False
                # Consume all accumulated keys in buffer to empty the queue
                while msvcrt.kbhit():
                    ch = msvcrt.getch()
                    # Special keys (arrows, function keys) send 2 bytes (prefix 0x00 or 0xE0)
                    if ch in (b'\x00', b'\xe0'):
                        if msvcrt.kbhit():
                            msvcrt.getch()  # Read and ignore trailing byte
                    # Check for Spacebar or Enter (fallback trigger)
                    elif ch in (b' ', b'\r', b'\n', ' ', '\r', '\n'):
                        has_trigger_key = True
                if has_trigger_key:
                    return True
            except Exception:
                pass
            return False
            
        # macOS & Linux flow
        try:
            # Use select to poll stdin for available bytes without blocking
            rlist, _, _ = select.select([sys.stdin], [], [], 0)
            if rlist:
                ch = sys.stdin.read(1)
                # Check for Spacebar or Enter keypresses
                if ch in (' ', '\n', '\r'):
                    return True
        except Exception:
            pass
        return False
        
    def restore(self):
        """
        Restores macOS/Linux terminal attributes to their original state.
        Must be executed before prompting user input (e.g. via input()),
        otherwise standard input will not behave correctly.
        """
        if self.active:
            try:
                termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old_settings)
            except Exception:
                pass
