import os
import pwd
import socket

def get_username() -> str:
    return pwd.getpwuid(os.getuid()).pw_name

def get_hostname() -> str:
    return socket.gethostname()

def get_prompt() -> str:
    username = get_username()
    hostname = get_hostname()
    cwd = os.getcwd()

    return f"{username}@{hostname} {cwd}> "