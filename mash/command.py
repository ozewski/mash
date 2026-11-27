from dataclasses import dataclass, field
from enum import Enum
from typing import Union

class RedirectOp(Enum):
    READ = "<"
    WRITE_TRUNC = ">"
    WRITE_APPEND = ">>"

@dataclass
class FileRedirection:
    # for I/O redirections on files
    fd: int         # descriptor (bare syntax: in case of read, this is stdin [0]; for write, this is stdout [1])
    op: RedirectOp  # based on syntax
    path: str       # where is it going? (file path)

@dataclass
class FdDuplication:
    fd: int        # descriptor (typically stdout [1] or stderr [2] )
    target: int    # where is it going? (a common use: fd=2, target=1 [redirect stderr to stdout])

Redirection = Union[FileRedirection, FdDuplication]

@dataclass
class Command:
    program: str
    args: list[str] = field(default_factory=list)
    redirections: list[Redirection] = field(default_factory=list)

    @property
    def argv(self) -> list[str]:
        return [self.program, *self.args]

@dataclass
class Pipeline:
    commands: list[Command]
