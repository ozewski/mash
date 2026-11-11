import os
import signal
import termios

from shell.state import state

def load_job_control():
    if state.interactive:
        # we will ignore these for the shell and re-enable them in the children
        signal.signal(signal.SIGTTOU, signal.SIG_IGN)
        signal.signal(signal.SIGTTIN, signal.SIG_IGN)
        signal.signal(signal.SIGTSTP, signal.SIG_IGN)

        