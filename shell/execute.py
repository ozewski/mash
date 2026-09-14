import os

from shell.command import Pipeline

class ExecutionError(Exception):
    """Raised when the execution of a pipeline fails"""

def execute_pipeline(pipeline: Pipeline):
    for command in pipeline.commands:
        pid = os.fork()

        if pid == 0:
            # child process
            os.execvp(command.program, command.args)
        elif pid > 0:
            finished_pid, status = os.waitpid(pid, 0)
        else:
            raise ExecutionError("failed to fork process")
