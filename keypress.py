import sys

if sys.platform != "win32":
    import termios
    import tty
    import select

class KeypressDetector:
    def __init__(self, active=True):
        self.active = active and sys.platform != "win32" and sys.stdin.isatty()
        if self.active:
            try:
                self.fd = sys.stdin.fileno()
                self.old_settings = termios.tcgetattr(self.fd)
                tty.setcbreak(self.fd)
            except Exception:
                self.active = False
            
    def check_space(self):
        if sys.platform == "win32":
            try:
                import msvcrt
                if msvcrt.kbhit():
                    ch = msvcrt.getch()
                    if ch == b' ':
                        return True
            except Exception:
                pass
            return False
            
        try:
            rlist, _, _ = select.select([sys.stdin], [], [], 0)
            if rlist:
                ch = sys.stdin.read(1)
                if ch == ' ':
                    return True
        except Exception:
            pass
        return False
        
    def restore(self):
        if self.active:
            try:
                termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old_settings)
            except Exception:
                pass
