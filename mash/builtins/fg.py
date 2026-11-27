import os
import signal
import sys
import termios

import mash.jobs
from mash.state import state

def fg(*args) -> int:
    if len(args) > 1:
        print("mash: fg: too many arguments", file=sys.stderr)
        return 1

    if not state.interactive:
        # without job control, this command is a no-op
        print("mash: fg: no job control", file=sys.stderr)
        return 1

    try:
        # try to resolve the desired job
        job = mash.jobs.resolve_jobspec(args[0] if args else None)
    except mash.jobs.JobSpecError as e:
        print(f"mash: fg: {e}", file=sys.stderr)
        return 1

    print(job.cmdline, flush=True)

    try:
        # give control to the process
        os.tcsetpgrp(state.tty_fd, job.pgid)
        if job.terminal_modes:
            # if the process had some special terminal settings, apply them
            termios.tcsetattr(state.tty_fd, termios.TCSADRAIN, job.terminal_modes)

    except (OSError, termios.error) as e:
        # in case of an error, make sure to give back control to the terminal
        print(f"mash: fg: could not give terminal to job: {e}", file=sys.stderr)
        try:
            os.tcsetpgrp(state.tty_fd, state.shell_pgid)
        except OSError:
            # even taking back the terminal could fail,
            # but there's nothing we could do about it at this point
            pass
        return 1

    job.background = False

    for proc in job.procs:
        if proc.state == "stopped":
            proc.state = "running"

    try:
        # send a signal to the process to wake itself up
        os.killpg(job.pgid, signal.SIGCONT)
    except ProcessLookupError:
        # the internet says this could happen in rare circumstances where the whole group
        # is already done; in this case, update state accordingly
        for proc in job.procs:
            if proc.state == "running":
                proc.state = "done"
    
    return mash.jobs.wait_for_job(job)
