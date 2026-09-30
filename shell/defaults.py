import sys
import os

from shell.colors import colors

def _run_cd(path):
    saved_pwd = os.getcwd()
    try:
        os.chdir(path)
    except OSError as e:
        print(f"mash: cd: {path}: {e.strerror}", file=sys.stderr)
        return
    
    os.environ["OLDPWD"] = saved_pwd

def cd(*args):
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
    
def exit(*args):
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

    print("mash: exiting gracefully...\n" + colors.RESET)
    sys.exit(exit_code)
