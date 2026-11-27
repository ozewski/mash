import os
import re
import sys

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

    processed_args = args[1:] if args[0] == "-p" else args

    for arg in processed_args:
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
