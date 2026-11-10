import atexit
import os
import readline
import sys

from shell.state import state

HISTFILE = os.environ.get("HISTFILE", os.path.expanduser("~/.mash_history"))
HISTSIZE = 1000

def init_history() -> None:
    readline.set_history_length(HISTSIZE)
    try:
        readline.read_history_file(HISTFILE)
    except FileNotFoundError:
        pass
    except OSError as e:
        print(f"mash: warning: could not read {HISTFILE}: {e.strerror}", file=sys.stderr)
    
    state.history_length_on_load = readline.get_current_history_length()
    atexit.register(_save_history)

def _save_history() -> None:
    new = readline.get_current_history_length() - state.history_length_on_load
    if new <= 0: # no new entries
        return
    
    try:
        readline.append_history_file(new, HISTFILE)
    except OSError as e:
        print(f"mash: warning: could not write {HISTFILE}: {e.strerror}", file=sys.stderr)