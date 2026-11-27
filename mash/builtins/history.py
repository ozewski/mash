import readline
import sys

def history(*args) -> int:
    if len(args) > 1:
        # keeping it simple for now
        print("mash: history: too many arguments", file=sys.stderr)
        return 1

    length = readline.get_current_history_length()

    if args and args[0] == "-c":
        readline.clear_history()
        return 0

    start = 1
    if args:
        # expecting numeric argument
        n = args[0]
        if not (n.isdigit() and n.isascii()):
            print(f"mash: history: {args[0]}: numeric argument required", file=sys.stderr)
            return 1
        
        n = int(n)
        if n == 0:
            return 0

        # snap start to entry that will produce n entries from the end
        # also, prevent negative lengths
        start = max(1, length - n + 1)

    for i in range(start, length + 1):
        # left-padded number
        print(f"{i:5d}  {readline.get_history_item(i)}")

    return 0
