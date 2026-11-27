import os
import signal
import sys
import termios
from dataclasses import dataclass

from mash.state import state

"""
Notes about job control:
- Job control only matters if the shell is interactive, because otherwise, there's no
  foreground and background. We store the interactivity check in state.interactive.
  So some code related to job control throughout the app is conditional on state.interactive
  being equal to True.
- In the initialization, we follow a rollback pattern that will rollback all the signal setters
  if any part of the initialization fails (and disables interactive mode). This way, the
  shell can proceed even if our attempt to initialize job control fails.
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
    last_active: int = 0
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

class JobSpecError(Exception):
    """Raised when a jobspec can't be resolved to a job."""

# keep track of all jobs
_jobs: list[Job] = []

# used to track sequence of most recent jobs interacted with
# so we can track current and previous, which is necessary for fg/bg/jobs commands
_job_seq = 0

def resolve_jobspec(arg: str | None) -> Job:
    if arg and arg.isascii() and arg.isdigit():
        arg = "%" + arg

    if arg in [None, "%", "%%", "%+"]:
        current, _ = current_and_previous()
        if current is None:
            raise JobSpecError("current: no such job")
        return current

    elif arg == "%-":
        _, previous = current_and_previous()
        if previous is None:
            raise JobSpecError("previous: no such job")
        return previous

    elif arg and arg[0] == "%":
        target = arg[1:]
        if target.isascii() and target.isdigit():
            # looking for job by number
            job_num = int(target)
            job = next(filter(
                lambda j: j.num == job_num,
                _jobs
            ), None)

            if not job:
                raise JobSpecError(f"{arg}: no such job")
            
            return job

        else:
            # try to search by prefix
            matches = list(filter(
                lambda j: j.cmdline.startswith(target),
                _jobs
            ))

            if not matches:
                raise JobSpecError(f"{arg}: no such job")
            elif len(matches) > 1:
                # found more than one job for that prefix
                raise JobSpecError(f"{arg}: ambiguous job spec")

            return matches[0]

    else:
        # reject anything else
        raise JobSpecError(f"{arg}: invalid job spec")

# friendly names for the signals that could happen to a job
_SIGNAL_NAMES = {
    signal.SIGTERM: "Terminated",
    signal.SIGKILL: "Killed",
    signal.SIGHUP: "Hangup",
    signal.SIGINT: "Interrupt",
}

def job_state(job: Job) -> str:
    if job.is_stopped:
        return "Stopped"
    
    if job.is_done:
        # a pipeline's outcome is its last stage
        raw = job.procs[-1].status

        if os.WIFSIGNALED(raw):
            # died from a signal (e.g. via `kill`): we can name the signal
            sig = os.WTERMSIG(raw)
            return _SIGNAL_NAMES.get(sig) or signal.strsignal(sig) or f"Signal {sig}"

        code = os.WEXITSTATUS(raw)
        return "Done" if code == 0 else f"Exit {code}"
    
    return "Running"

def job_marker(job: Job, current: Job | None, previous: Job | None) -> str:
    # "+" for the current job, "-" for the previous one, " " otherwise
    return "+" if job is current else "-" if job is previous else " "

def format_job(job: Job, marker: str = " ") -> str:
    # marker: "+" (current), "-" (previous), or " "
    return f"[{job.num}]{marker}  {job_state(job):<22}{job.cmdline}"

def current_and_previous() -> tuple[Job | None, Job | None]:
    ordered = sorted(_jobs, key=lambda j: j.last_active, reverse=True)
    current = ordered[0] if len(ordered) > 0 else None
    previous = ordered[1] if len(ordered) > 1 else None
    return current, previous

def touch(job: Job) -> None:
    global _job_seq
    _job_seq += 1
    job.last_active = _job_seq

def wait_status(status: int):
    # normalizes exit status to a positive integer
    code = os.waitstatus_to_exitcode(status)
    return 128 - code if code < 0 else code

def all_jobs() -> list[Job]:
    return _jobs

def add_job(pgid: int, pids: list[int], cmdline: str, background: bool = False) -> Job:
    # first number = 1, otherwise increment
    num = max((j.num for j in _jobs), default=0) + 1
    job = Job(
        num, pgid, [Proc(pid) for pid in pids], cmdline, background=background
    )

    touch(job)
    _jobs.append(job)
    return job

def remove_job(job: Job):
    if job in _jobs:
        _jobs.remove(job)

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
            update_proc(proc, status)

    # return terminal control to the shell
    if state.interactive:
        try:
            os.tcsetpgrp(state.tty_fd, state.shell_pgid)
            if job.is_stopped:
                # we only care about its settings if the job was stopped
                # because if the job finished, it won't be resumed, so it doesn't matter
                job.terminal_modes = termios.tcgetattr(state.tty_fd)   # save job's settings

            # reset shell terminal configuration
            termios.tcsetattr(state.tty_fd, termios.TCSADRAIN, state.terminal_modes)
        except (OSError, termios.error) as e:
            print(f"mash: warning: could not restore terminal state: {e}", file=sys.stderr)

    # standard output if the job was stopped
    if job.is_stopped:
        touch(job)
        # a just-stopped job is always "current" (+)
        print(f"\n{format_job(job, '+')}")
        # leave the job in the table and return standard exit code
        return 128 + signal.SIGTSTP

    remove_job(job)
    return wait_status(job.procs[-1].status)

JOB_SIGNALS = (
    signal.SIGTTOU,  # when a bg process group attempts to change terminal settings
    signal.SIGTTIN,  # when a bg process groups tries to read from the terminal
    signal.SIGTSTP,  # when the user presses CTRL+Z
    signal.SIGQUIT,  # when the user presses CTRL+\
    signal.SIGTERM   # when a process is terminated using the kill command
)

def init_job_control():
    if not state.interactive:
        return

    try:
        tty_fd = os.open("/dev/tty", os.O_RDWR)
    except OSError:
        # we can keep running even if we're not interactive
        state.interactive = False
        return

    # rollback pattern:
    # all these operations can be rolled back upon finding any error

    saved_signal_handlers = {}
    try:
        # wait until our shell is in the foreground
        while os.tcgetpgrp(tty_fd) != os.getpgrp():
            # we send SIGTTIN to our shell's process group to suspend it
            os.killpg(os.getpgrp(), signal.SIGTTIN)

        # we will ignore these for the shell and re-enable them in the children
        # if we didn't, these operations would affect the shell itself rather than
        # the children, leading to undesirable behavior

        for sig in JOB_SIGNALS:
            saved_signal_handlers[sig] = signal.signal(sig, signal.SIG_IGN)
        
        # we attempt to put the shell in its own process group, so that we can
        # set it as the foreground later (give it terminal control)
        shell_pgid = os.getpid()

        # there could be a case where our shell already has a pgid
        # in that case, we could skip this step
        if os.getpgrp() != shell_pgid:
            os.setpgid(0, shell_pgid)

        # put our app in the foreground
        os.tcsetpgrp(tty_fd, shell_pgid)
        terminal_modes = termios.tcgetattr(tty_fd)

    except (OSError, termios.error) as e:
        # roll back everything we touched
        for sig, handler in saved_signal_handlers.items():
            signal.signal(sig, handler)

        os.close(tty_fd)
        print(f"mash: warning: job control disabled: {e}", file=sys.stderr)
        state.interactive = False
        # skip committing to state
        return

    # all operations successful: commit state
    state.tty_fd = tty_fd
    state.shell_pgid = shell_pgid
    state.terminal_modes = terminal_modes

def reap_jobs():
    # collects state from background children that nobody is waiting on
    # updates the job table accordingly, and announces finished/stopped jobs
    changed = []

    while True:
        try:
            # -1 = any child, since we don't know which one changed
            # WNOHANG = don't block; return pid 0 if nothing has changed
            # WUNTRACED = also report children that were stopped (not just exited)
            pid, status = os.waitpid(-1, os.WNOHANG | os.WUNTRACED)
        except ChildProcessError:
            # there are no children at all, so there is nothing left to collect
            break

        if pid == 0:
            # there are children, but none have changed state
            # we reach this at the end of the sweep
            break

        job, proc = find_proc(pid) # find the job and process in our state
        if job is None or proc is None:
            # we're not tracking this child
            # we've reaped the process; that's all we need to do
            continue

        # otherwise, we're tracking this process
        # must update our state
        update_proc(proc, status)
        if job not in changed:
            changed.append(job)

    if not changed:
        return

    current, previous = current_and_previous()

    # for all jobs that have changed:
    for job in changed:
        if job.is_done:
            # whole job has exited
            # announce it, then drop it from the table
            print(format_job(job, job_marker(job, current, previous)))
            remove_job(job)

        elif job.is_stopped:
            # a background job got a signal and stopped
            # it's now the most recently active job, so bump it, then it is
            # genuinely current and "+" is correct
            touch(job)
            print(format_job(job, "+"))

        # otherwise, maybe the job changed but there are stil jobs in the pipeline running
        # therefore, nothing to announce yet
    
    sys.stdout.flush()
