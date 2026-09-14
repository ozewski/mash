import sys
import os

def _run_cd(path):
    saved_pwd = os.getcwd()
    os.chdir(path)
    os.environ["OLDPWD"] = saved_pwd

def cd(*args):
    if len(args) > 1:
        print("mash: cd: too many arguments", file=sys.stderr)
        return 1

    if not args:
        # change to home directory
        pass
    
    path = args[0]

    if path == "-":
        old_pwd = os.environ["OLDPWD"]
        if old_pwd:
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
    pass
