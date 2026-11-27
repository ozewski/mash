import sys

from mash.state import state

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
