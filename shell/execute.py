import os

from shell.command import FdDuplication, FileRedirection, Pipeline, RedirectOp, Redirection
from shell.defaults import cd as mash_cd, exit as mash_exit

DEFAULT_COMMANDS = {
    "cd": mash_cd,
    "exit": mash_exit
}

class ExecutionError(Exception):
    """Raised when the execution of a pipeline fails."""

def apply_redirections(redirections: list[Redirection]):
    for redir in redirections:
        if isinstance(redir, FileRedirection):
            flags = {
                RedirectOp.READ: os.O_RDONLY,
                RedirectOp.WRITE_TRUNC: os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
                RedirectOp.WRITE_APPEND: os.O_WRONLY | os.O_CREAT | os.O_APPEND
            }[redir.op]

            path_fd = os.open(redir.path, flags, 0o666)
            os.dup2(path_fd, redir.fd)
            os.close(path_fd)
        elif isinstance(redir, FdDuplication):
            os.dup2(redir.target, redir.fd)


def execute_pipeline(pipeline: Pipeline) -> int:
    if len(pipeline.commands) > 1:
        raise ExecutionError("multi-stage pipelines not yet supported")
    
    for command in pipeline.commands:
        if command.program in DEFAULT_COMMANDS:
            return DEFAULT_COMMANDS[command.program](*command.args)

        try:
            pid = os.fork()
        except OSError as e:
            raise ExecutionError("failed to create new process") from e

        if pid == 0:
            # child process
            try:
                apply_redirections(pipeline.commands[0].redirections)
                os.execvp(command.program, command.argv)
            except FileNotFoundError:
                # my research says these are standard exit codes
                os._exit(127)
            except PermissionError:
                os._exit(126)
            except OSError:
                os._exit(1)
            finally:
                os._exit(1)
            
                
        else:
            # parent process
            _, status = os.waitpid(pid, 0)
            return os.waitstatus_to_exitcode(status)

    return -1
