import os
import signal
import termios

from shell.state import state

def load_job_control():
    if state.interactive:
        # we will ignore these for the shell and re-enable them in the children
        # if we didn't, these operations would affect the shell itself rather than
        # the children, leading to undesirable behavior

        # SIGTTOU: when a bg process group attempts to change terminal settings
        signal.signal(signal.SIGTTOU, signal.SIG_IGN)

        # SIGTTIN: when a bg process groups tries to read from the terminal
        signal.signal(signal.SIGTTIN, signal.SIG_IGN)

        # SIGTSTP: when the user presses CTRL+Z
        signal.signal(signal.SIGTSTP, signal.SIG_IGN)

        # use /dev/tty because stdin or stdout could have been redirected
        tty_fd = os.open("/dev/tty", os.O_RDWR)
        shell_pgid = os.getpid()

        # we attempt to put the shell in its own process group, so that we can
        # set it as the foreground later (give it terminal control)
        try:
            os.setpgid(0, shell_pgid)
        except OSError:
            print("mash: fatal error: could not establish job control")
            os._exit(1)

        os.tcsetpgrp(tty_fd, shell_pgid)

        

        