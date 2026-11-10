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

VARNAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

def quote(value: str) -> str:
    return "'" + value.replace("'", "'\\''") + "'"

def export(*args) -> int:
    if len(args) == 0 or (len(args) == 1 and args[0] == "-p"):
        # weird behavior: when any other arguments are present, the -p behavior is ignored
        for key in sorted(os.environ):
            print(f"export {key}={quote(os.environ[key])}")
        return 0

    status = 0
    # we can't exit immediately upon bad variable name, since the bash behavior is to
    # set as many of the variables as possible. therefore, we track the status and
    # report it at the end.

    for arg in args:
        varname, sep, value = arg.partition("=")

        if not VARNAME.fullmatch(varname):
            print(f"mash: export: `{arg}': not a valid identifier", file=sys.stderr)
            status = 1
            continue

        if not sep:
            print(f"mash: export: `{arg}': bare identifiers not supported", file=sys.stderr)
            status = 1
            continue


        os.environ[varname] = value

    return status
        