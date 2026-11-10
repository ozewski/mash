import platform
import readline
import sys
import os

from datetime import datetime, timezone
from pprint import pprint

from shell.cli import get_prompt
from shell.colors import colors
from shell.execute import execute_pipeline, ExecutionError
from shell.history import init_history
from shell.parser import parse_command, ParseError
from shell.state import state

VERSION = "0.1.0"

init_history()

if "MASH_CWD_MAX" not in os.environ:
    os.environ["MASH_CWD_MAX"] = "20"

utc_now = datetime.now(timezone.utc)
using_wsl = "wsl" in platform.release().lower()

print(f"\nmash: minimal application shell [v{VERSION}]")
if using_wsl:
    print("mash: running in WSL mode")

print()

try:
    while True:
        pipeline = None

        try:
            command = input(get_prompt()).strip()
            if not command:
                continue
        except KeyboardInterrupt:
            print("^C")
            continue
        except EOFError:
            print("^D")
            break

        try:
            try:
                pipeline = parse_command(command)
            except ParseError as e:
                print(f"mash: syntax error: {e}", file=sys.stderr)

            if pipeline:
                try:
                    execute_pipeline(pipeline)
                except ExecutionError as e:
                    print(f"mash: execution error: {e}", file=sys.stderr)
                if state.exit_requested:
                    break

        except Exception as e:
            print(f"mash: unexpected error: {e}", file=sys.stderr)

finally:
    print("\nmash: exiting gracefully...\n" + colors.RESET)
