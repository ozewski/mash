import os

from shell.command import Command, FdDuplication, FileRedirection, Pipeline, RedirectOp, Redirection
from shell.defaults import cd as mash_cd, exit as mash_exit

DEFAULT_COMMANDS = {
    "cd": mash_cd,
    "exit": mash_exit
}

def _wait_status(status: int):
    # normalizes exit status to a positive integer
    code = os.waitstatus_to_exitcode(status)
    return 128 - code if code < 0 else code

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
                raise RedirectionError(f"{redir.target}: {e.strerror}") from e\

def run_in_child(command: Command):
    # runs in the newly created child process after a fork
    try:
        try:
            apply_redirections(command.redirections)
        except RedirectionError as e:
            _report(str(e))
            os._exit(1)

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

def execute_pipeline(pipeline: Pipeline) -> int:
    if len(pipeline.commands) > 1:
        raise ExecutionError("multi-stage pipelines not yet supported")
    
    for command in pipeline.commands:
        if command.program in DEFAULT_COMMANDS:
            if command.redirections:
                raise ExecutionError(f"{command.program}: redirections on builtins not yet supported")
            return DEFAULT_COMMANDS[command.program](*command.args)

        try:
            pid = os.fork()
        except OSError as e:
            raise ExecutionError("failed to create new process") from e

        if pid == 0:
            # child process
            run_in_child(command)
        else:
            # parent process
            _, status = os.waitpid(pid, 0)
            return _wait_status(status)

    return -1
