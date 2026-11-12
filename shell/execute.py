import os
import signal
import sys

import shell.defaults
import shell.jobs
from shell.command import Command, FdDuplication, FileRedirection, Pipeline, RedirectOp, Redirection
from shell.state import state

"""
Some notes about job control:
- We run setpgid (setting the process group) and tcsetpgrp (setting a process
  group to foreground) in both the parent and child to fix a couple rare but
  important race conditions that the internet says could occur.
"""

DEFAULT_COMMANDS = {
    "cd": shell.defaults.cd,
    "exit": shell.defaults.exit,
    "export": shell.defaults.export,
    "history": shell.defaults.history,
    "jobs": shell.defaults.jobs,
    "bg": shell.defaults.bg,
    "fg": shell.defaults.fg
}

def _close_all(fds: list[int]) -> None:
    # try to close as many fds as possible
    # helper utility to prevent fd leaks in pipelines
    for fd in fds:
        try:
            os.close(fd)
        except OSError:
            pass

def _report(msg: str) -> None:
    # use low-level os.write to prevent issues with buffered output
    # this is used in the child process after a fork
    try:
        os.write(2, f"mash: {msg}\n".encode(errors="replace"))
    except OSError:
        pass

class ExecutionError(Exception):
    """Raised when the execution of a pipeline fails."""

class RedirectionError(Exception):
    """Raised in the child when a redirection can't be set up."""

def apply_redirections(redirections: list[Redirection]):
    for redir in redirections:
        if isinstance(redir, FileRedirection):
            flags = {
                RedirectOp.READ: os.O_RDONLY,
                RedirectOp.WRITE_TRUNC: os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
                RedirectOp.WRITE_APPEND: os.O_WRONLY | os.O_CREAT | os.O_APPEND
            }[redir.op]

            try:
                # get fd for target path
                path_fd = os.open(redir.path, flags, 0o666)
            except OSError as e:
                raise RedirectionError(f"{redir.path}: {e.strerror}") from e

            if path_fd != redir.fd: # the internet says that there are cases where this could be an issue
                try:
                    # perform the redirection
                    os.dup2(path_fd, redir.fd)
                except OSError as e:
                    raise RedirectionError(f"{redir.fd}: {e.strerror}") from e
                finally:
                    # close the fd to prevent leaks
                    os.close(path_fd)

        elif isinstance(redir, FdDuplication):
            try:
                os.dup2(redir.target, redir.fd)
            except OSError as e:
                raise RedirectionError(f"{redir.target}: {e.strerror}") from e

def run_in_child(
        command: Command, 
        stdin_fd: int | None, 
        stdout_fd: int | None, 
        pipe_fds: list[int], 
        pgid: int
    ) -> None:
    # runs in the newly created child process after a fork
    # will never return
    try:
        # must restore SIGPIPE for the child, since python disables it
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)

        # perform terminal handoff (job control)
        if state.interactive:
            # first stage: pgid == 0
            # - in this scenario, process becomes leader of a new group
            # all other stages: pgid > 0
            # - process joins the group created by the first stage
            os.setpgid(0, pgid)

            try:
                # best-effort attempt to set the foreground process group
                # this is a no-op if it worked in the parent
                os.tcsetpgrp(state.tty_fd, os.getpgrp())
            except OSError:
                # the only failure here would be caused by some kind of
                # race case with the parent, and the parent would have
                # already fixed and ensured that tcsetpgrp worked. so we
                # don't care about any issue
                pass

            for sig in (
                signal.SIGINT, 
                signal.SIGQUIT, 
                signal.SIGTSTP,
                signal.SIGTTIN, 
                signal.SIGTTOU
            ):
                # resume processing for all relevant signals in the child
                signal.signal(sig, signal.SIG_DFL)

        # wire up pipes
        try:
            if stdin_fd is not None:
                os.dup2(stdin_fd, 0)
            if stdout_fd is not None:
                os.dup2(stdout_fd, 1)
        except OSError as e:
            _report(f"pipe setup failed: {e.strerror}")
            os._exit(1)

        # close original pipe FDs (the dups survive)
        _close_all(pipe_fds)

        # handle explicit I/O redirections
        try:
            apply_redirections(command.redirections)
        except RedirectionError as e:
            _report(str(e))
            os._exit(1)

        # intercept built-ins to run them in the child process
        if command.program in DEFAULT_COMMANDS:
            status = DEFAULT_COMMANDS[command.program](*command.args)
            # since built-ins use python printing, must flush stdout and stderr before exiting
            sys.stdout.flush()
            sys.stderr.flush()
            os._exit(status)

        # otherwise, replace process with the requested program
        try:
            os.execvp(command.program, command.argv)
        except FileNotFoundError:
            _report(f"{command.program}: command not found")
            os._exit(127)
        except PermissionError:
            _report(f"{command.program}: permission denied")
            os._exit(126)
        except OSError as e:
            _report(f"{command.program}: {e.strerror}")
            os._exit(1)

    except BaseException as e:
        _report(f"internal error: {e}")
    finally:
        os._exit(1)

def execute_pipeline(pipeline: Pipeline, cmdline: str) -> int:
    if len(pipeline.commands) == 1 and pipeline.commands[0].program in DEFAULT_COMMANDS:
        # handle a single built-in command directly in the shell process
        command = pipeline.commands[0]
        if command.redirections:
            raise ExecutionError(f"{command.program}: redirections on builtins not yet supported")
        return DEFAULT_COMMANDS[command.program](*command.args)

    # perform flushing before forking to avoid duplicate output in the child process
    sys.stdout.flush()
    sys.stderr.flush()

    # set up variables to track pipeline information
    n = len(pipeline.commands)
    pipe_fds: list[int] = []  # track every fd we created to ensure they all get closed
    pipes: list[tuple[int, int]] = []  # all pipes created by OS
    pids: list[int] = []  # all PIDs (stages of pipeline) that we have run so far
    pipeline_error = None  # track any errors that occur during the execution of the pipeline
    pgid: int = 0  # initial group ID, which is set later to the PID of the process that created the group

    try:
        for _ in range(n - 1):
            try:
                r, w = os.pipe()
            except OSError as e:
                raise ExecutionError(f"failed to create pipe: {e.strerror}") from e

            pipes.append((r, w))
            pipe_fds += [r, w]
        
        for i, command in enumerate(pipeline.commands):
            # select appropriate stdin and stdout for this command in the pipeline
            # if we're at the beginning or end, either stdin or stdout is None
            # meaning the child will inherit the shell's stdin or stdout
            stdin_fd = pipes[i - 1][0] if i > 0 else None
            stdout_fd = pipes[i][1] if i < n - 1 else None
            
            try:
                pid = os.fork()
            except OSError as e:
                raise ExecutionError("failed to create new process") from e

            if pid == 0:
                # child process
                run_in_child(command, stdin_fd, stdout_fd, pipe_fds, pgid)
            else:
                # parent process
                # track the PID of the child
                pids.append(pid)

                if state.interactive:
                    if pgid == 0:
                        # we just created the first child;
                        # set the group ID to its PID so all following children
                        # join the process group
                        pgid = pid

                    try:
                        # parent attempts to set process group
                        os.setpgid(pid, pgid)
                    except OSError:
                        # ...but maybe the child already did it
                        pass
            
    except BaseException as e:
        # we save the error so that we can proceed and wait on the rest of the pipeline
        pipeline_error = e

    finally:
        # guaranteed resource cleanup: close all pipe fds in the parent process
        _close_all(pipe_fds)

    if not pids:
        raise pipeline_error or ExecutionError("no processes started")

    # create new shell job
    job = shell.jobs.add_job(pgid, pids, cmdline)

    if state.interactive:
        # attempt to give the foreground to the job
        try:
            os.tcsetpgrp(state.tty_fd, pgid)
        except OSError as e:
            print(f"mash: warning: could not give terminal to job: {e.strerror}", file=sys.stderr)

    # wait for the job to finish or get stopped
    status = shell.jobs.wait_for_job(job)

    if pipeline_error:
       raise pipeline_error

    return status
