import platform
import readline
import sys

from datetime import datetime, timezone
from pprint import pprint

from shell.cli import get_prompt
from shell.colors import colors
from shell.parser import parse_command, ParseError

VERSION = "0.1.0"

utc_now = datetime.now(timezone.utc)
using_wsl = "wsl" in platform.release().lower()

print(f"\nmash: minimal application shell [v{VERSION}]")
if using_wsl:
    print("mash: running in WSL mode")

print()

while True:
    # TODO: add custom shell prompt with colors
    pipeline = None

    try:
        command = input(get_prompt()).strip()
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

print(colors.RESET)
