import os

from shell.command import Pipeline

class ExecutionError(Exception):
    """Raised when the execution of a pipeline fails."""

def execute_pipeline(pipeline: Pipeline) -> int:
    if len(pipeline.commands) > 1:
        raise ExecutionError("multi-stage pipelines not yet supported")

    if pipeline.commands[0].redirections:
        raise ExecutionError("I/O redirections not yet supported")
    
    for command in pipeline.commands:
        try:
            pid = os.fork()
        except OSError as e:
            raise ExecutionError("failed to create new process") from e

        if pid == 0:
            # child process
            try:
                os.execvp(command.program, command.argv)
            except FileNotFoundError:
                # my research says these are standard exit codes
                os._exit(127)
            except PermissionError:
                os._exit(126)
            except OSError:
                os._exit(1)
                
        else:
            # parent process
            _, status = os.waitpid(pid, 0)
            return os.waitstatus_to_exitcode(status)

    return -1
