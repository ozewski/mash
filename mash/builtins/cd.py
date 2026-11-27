import os
import sys

def _run_cd(path) -> int:
    saved_pwd = os.getcwd()
    try:
        os.chdir(path)
    except OSError as e:
        print(f"mash: cd: {path}: {e.strerror}", file=sys.stderr)
        return 1
    
    os.environ["OLDPWD"] = saved_pwd
    os.environ["PWD"] = os.getcwd()
    return 0

def cd(*args) -> int:
    if len(args) > 1:
        print("mash: cd: too many arguments", file=sys.stderr)
        return 1

    if not args or args[0] == "~":
        # change to home directory
        return _run_cd(os.path.expanduser("~"))
    
    path = args[0]

    if path == "-":
        old_pwd = os.environ.get("OLDPWD", None)
        if old_pwd:
            print(old_pwd) # this is how bash does it
            return _run_cd(os.environ["OLDPWD"])
        else:
            print("mash: cd: no previous directory", file=sys.stderr)
            return 1
        
    else:
        if os.path.isfile(path):
            print(f"mash: cd: {path}: not a directory", file=sys.stderr)
            return 1
        if os.path.isdir(path):
            return _run_cd(path)
        else:
            print(f"mash: cd: {path}: no such file or directory", file=sys.stderr)
            return 1