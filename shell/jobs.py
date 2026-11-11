import os
import signal
import sys
import termios
from dataclasses import dataclass

from shell.state import state

"""
Notes about job control:
- Job control only matters if the shell is interactive, because otherwise, there's no
  foreground and background. We store the interactivity check in state.interactive.
  So some code related to job control throughout the app is conditional on state.interactive
  being equal to True.
"""

@dataclass
class Proc:
    pid: int                # pid of process
    state: str = "running"  # running, stopped (can be resumed), or done
    status: int = 0         # raw waitpid status (only meaningful once done)

@dataclass
class Job:
    num: int
    pgid: int
    procs: list[Proc]
    cmdline: str
    terminal_modes: list | None = None
    background: bool = False

    @property
    def is_done(self) -> bool:
        # every process is done
        return all(p.state == "done" for p in self.procs)

    @property
    def is_stopped(self) -> bool:
        # no processes are running, and any process is stopped
        return (
            not any(p.state == "running" for p in self.procs)
            and any(p.state == "stopped" for p in self.procs)
        )

def wait_status(status: int):
    # normalizes exit status to a positive integer
    code = os.waitstatus_to_exitcode(status)
    return 128 - code if code < 0 else code

# keep track of all jobs
_jobs: list[Job] = []

def all_jobs() -> list[Job]:
    return _jobs

def add_job(pgid: int, pids: list[int], cmdline: str, background: bool = False) -> Job:
    # first number = 1, otherwise increment
    num = max((j.num for j in _jobs), default=0) + 1
    job = Job(
        num, pgid, [Proc(pid) for pid in pids], cmdline, background=background
    )

    _jobs.append(job)
    return job

def remove_job(job: Job):
    if job in _jobs:
        _jobs.remove(job)

def find_job(id: str | int | None) -> Job | None:
    # pass either the "%1" format, 1, or None (to get most recent job)
    if not _jobs:
        return None
    if id is None:
        # return most recent job
        return _jobs[-1]

    if isinstance(id, int):
        num = id
    else:
        try:
            num = int(id.lstrip("%"))
        except ValueError:
            return None
    
    return next((j for j in _jobs if j.num == num), None)

def find_proc(pid: int) -> tuple[Job | None, Proc | None]:
    # attempt to locate a process and its associated job
    for job in _jobs:
        for p in job.procs:
            if p.pid == pid:
                return job, p
    return None, None

def update_proc(proc: Proc, status: int) -> None:
    if os.WIFSTOPPED(status):  # process was stopped by a signal
        proc.state = "stopped"
    elif os.WIFCONTINUED(status):  # process was continued by a signal
        proc.state = "running"
    else:  # process exited or was killed by a signal
        proc.state = "done"
        proc.status = status

def wait_for_job(job: Job) -> int:
    # block until no process in the job is "running"
    for proc in job.procs:
        while proc.state == "running":
            try:
                # using WUNTRACTED will also report if process was suspended
                _, status = os.waitpid(proc.pid, os.WUNTRACED)
            except ChildProcessError:
                # someone else already got the status
                # we can treat the process as finished
                proc.state = "done"
                break
            except InterruptedError:
                # we got interrupted by a signal
                # in this case, we want to keep waiting on the process
                continue
            update_proc(proc, status)

    # return terminal control to the shell
    if state.interactive:
        os.tcsetpgrp(state.tty_fd, state.shell_pgid)
        if job.is_stopped:
            # we only care about its settings if the job was stopped
            # because if the job finished, it won't be resumed, so it doesn't matter
            job.terminal_modes = termios.tcgetattr(state.tty_fd)   # save job's settings

        # reset shell terminal configuration
        termios.tcsetattr(state.tty_fd, termios.TCSADRAIN, state.terminal_modes)

    # standard output if the job was stopped
    # TODO: double check this
    if job.is_stopped:
        print(f"\n[{job.num}]+ Stopped  {job.cmdline}")
        # leave the job in the table and return standard exit code
        return 128 + signal.SIGTSTP

    remove_job(job)
    return wait_status(job.procs[-1].status)


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
        