from dataclasses import dataclass, field

@dataclass
class Command:
    program: str
    args: list[str] = field(default_factory=list)
    