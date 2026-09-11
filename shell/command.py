from dataclasses import dataclass, field
from enum import Enum

class RedirectOp(Enum):
    READ = "<"
    # TODO: implement other operations

@dataclass
class Redirection:
    # for I/O redirections
    fd: int         # could be stdin/stdout/stderr or a custom fd
    op: RedirectOp  # based on syntax of operator
    target: str

@dataclass
class Command:
    program: str
    args: list[str] = field(default_factory=list)
    redirections: list[Redirection] = field(default_factory=list)
