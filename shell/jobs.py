import os
import signal
import sys
import termios

from shell.state import state

def init_job_control():
    if not state.interactive:
        return

    try:
        state.tty_fd = os.open("/dev/tty", os.O_RDWR)
    except OSError:
        # we can keep running even if we're not interactive
        state.interactive = False
        return

    # wait until our shell is in the foreground
    while os.tcgetpgrp(state.tty_fd) != os.getpgrp():
        # we send SIGTTIN to our shell's process group to suspend it
        os.killpg(os.getpgrp(), signal.SIGTTIN)

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
    state.tty_fd = os.open("/dev/tty", os.O_RDWR)
    
    # we attempt to put the shell in its own process group, so that we can
    # set it as the foreground later (give it terminal control)
    state.shell_pgid = os.getpid()

    # there could be a case where our shell already has a pgid
    # in that case, we could skip this step
    if os.getpgrp() != state.shell_pgid:
        try:
            os.setpgid(0, state.shell_pgid)
        except OSError:
            print("mash: fatal error: could not establish job control", file=sys.stderr)
            state.interactive = False
            return

    # put our app in the foreground
    os.tcsetpgrp(state.tty_fd, state.shell_pgid)
    state.terminal_modes = termios.tcgetattr(state.tty_fd)
        