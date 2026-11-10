import sys
import os
import re

from shell.state import state
from shell.colors import colors

# All defaults should return a status number.

def _run_cd(path):
    saved_pwd = os.getcwd()
    try:
        os.chdir(path)
    except OSError as e:
        print(f"mash: cd: {path}: {e.strerror}", file=sys.stderr)
        return
    
    os.environ["OLDPWD"] = saved_pwd

def cd(*args) -> int:
    if len(args) > 1:
        print("mash: cd: too many arguments", file=sys.stderr)
        return 1

    if not args or args[0] == "~":
        # change to home directory
        _run_cd(os.path.expanduser("~"))
        return 0
    
    path = args[0]

    if path == "-":
        old_pwd = os.environ.get("OLDPWD", None)
        if old_pwd:
            print(old_pwd) # this is how bash does it
            _run_cd(os.environ["OLDPWD"])
            return 0
        else:
            print("mash: cd: no previous directory", file=sys.stderr)
            return 1
        
    else:
        if os.path.isfile(path):
            print(f"mash: cd: {path}: not a directory", file=sys.stderr)
            return 1
        if os.path.isdir(path):
            _run_cd(path)
            return 0
        else:
            print(f"mash: cd: {path}: no such file or directory", file=sys.stderr)
            return 1
    
def exit(*args) -> int:
    if len(args) > 1:
        print("mash: exit: too many arguments", file=sys.stderr)
        return 1

    exit_code = 0
    if args:
        try:
            exit_code = int(args[0])
        except ValueError:
            print(f"mash: exit: {args[0]}: numeric argument required", file=sys.stderr)
            return 1

    state.exit_requested = True
    return exit_code

def quote(value: str) -> str:
    return "'" + value.replace("'", "'\\''") + "'"

def export(*args) -> int:
    if len(args) == 0 or args[0] == "-p":
        for key, value in os.environ.items():
            print(f"{key}={quote(value)}")
        return 0

    for arg in args:
        varname, sep, value = arg.partition("=")

        if not re.fullmatch("[A-Za-z_][A-Za-z0-9_]*", varname):
            print(f"mash: export: {quote(arg)}: not a valid identifier", file=sys.stderr)
            return 1

        if not sep:
            print("mash: exit: shell variables not supported", file=sys.stderr)
            return 1

        os.environ[varname] = value

    return 0
        