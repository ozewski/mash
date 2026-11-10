import os
import pwd
import socket

from shell.colors import colors

def get_username() -> str:
    return pwd.getpwuid(os.getuid()).pw_name

def get_hostname() -> str:
    return socket.gethostname()

def get_abbreviated_cwd(max_length: int) -> str:
    """Abbreviates the current working directory to a maximum length."""
    cwd = os.getcwd()

    if len(cwd) <= max_length:
        return cwd

    parts = cwd.split("/")
    char_len = 0

    if (len(parts[-1]) > (max_length - 4)):
        return ".../" + parts[-1]

    for i in range(1, len(parts) + 1):
        entry = parts[-i]
        char_len += len(entry)
        if char_len > (max_length - i - 3):
            return ".../" + "/".join(parts[(-i + 1):])

    return cwd

def get_prompt() -> str:
    username = get_username()
    hostname = get_hostname()

    max_cwd_length = 20
    max_cwd_env = os.environ.get("MASH_CWD_MAX", None)
    if max_cwd_env and max_cwd_env.isdigit():
        max_cwd_length = int(max_cwd_env)

    cwd = get_abbreviated_cwd(max_cwd_length)

    return f"{colors.CYAN}{username}{colors.RESET}@{colors.YELLOW}{hostname}{colors.RESET} {colors.BRIGHT_BLACK}{cwd}{colors.RESET}> "