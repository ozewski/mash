from os import isatty

class ShellState:
    interactive = isatty(0)
    exit_requested: bool = False
    history_length_on_load: int = 0

state = ShellState()