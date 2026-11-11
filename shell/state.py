from os import isatty

class ShellState:
    interactive = isatty(0)
    exit_requested: bool = False
    history_length_on_load: int = 0
    tty_fd: int | None = None
    shell_pgid: int = 0
    terminal_modes: list | None = None


state = ShellState()