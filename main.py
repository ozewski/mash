import platform
import readline
import sys
from pprint import pprint
from shell.parser import parse_command, ParseError

print(platform.release())
print(platform.version())
print()

while True:
    # TODO: add custom shell prompt with colors
    pipeline = None

    try:
        command = input("> ").strip()
        if not command:
            continue
    except KeyboardInterrupt:
        print("^C")
        continue
    except EOFError:
        print("\nmash: exiting gracefully...")
        break

    try:
        pipeline = parse_command(command)
    except ParseError as e:
        print(f"mash: syntax error: {e}", file=sys.stderr)
    except Exception as e:
        print(f"mash: unexpected error: {e}", file=sys.stderr)

    if pipeline:
        pprint(pipeline)

