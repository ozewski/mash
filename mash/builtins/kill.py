import os
import signal
import sys

import mash.jobs
from mash.state import state

# for these signals, wakeup after kill is skipped
SKIP_WAKEUP = (
    signal.Signals["SIGKILL"], # since it already kills stopped processes
    signal.Signals["SIGCONT"], # since it already wakes the job
    signal.Signals["SIGSTOP"], # since the user wants it to stay stopped
    signal.Signals["SIGTSTP"], # ^
    signal.Signals["SIGTTIN"], # ^
    signal.Signals["SIGTTOU"], # ^
)

KILL_USAGE = "kill [-s sigspec | -sigspec] pid | jobspec ... or kill -l [sigspec]"

def kill(*args) -> int:
    if not args:
        print(f"mash: kill: usage: {KILL_USAGE}", file=sys.stderr)
        return 1

    sig = None
    sig_query = ""
    targets_start = 0

    if args[0] == "-l":
        if len(args) > 1 and args[1].isascii() and args[1].isdigit():
            val = int(args[1])
            try:
                name = signal.Signals(val).name[3:]
                print(name)
                return 0
            except ValueError:
                print(f"mash: kill: {args[1]}: invalid signal", file=sys.stderr)
                return 1
        else:
            for s in signal.Signals:
                print(f"{s.value}) {s.name}")
            return 0

    elif args[0].startswith("-"):
        # need to parse out what kind of query it is
        if args[0] == "-s":
            if len(args) < 2:
                print(f"mash: kill: -s: missing argument", file=sys.stderr)
                return 1
            
            sig_query = args[1]
            targets_start = 2
        else:
            sig_query = args[0][1:]
            targets_start = 1

        if sig_query == "":
            print(f"mash: kill: invalid syntax", file=sys.stderr)
            return 1

        elif sig_query.isascii() and sig_query.isdigit():
            # kill -9 ...
            n = int(sig_query)
            try:
                sig = signal.Signals(n)
            except ValueError:
                print(f"mash: kill: {sig_query}: invalid signal specification", file=sys.stderr)
                return 1

        else:
            # kill -SIGPIPE or kill -PIPE
            sig_query = sig_query.upper()
            query = sig_query
            if not query.startswith("SIG"):
                query = "SIG" + query
            
            try:
                sig = signal.Signals[query]
            except KeyError:
                print(f"mash: kill: {sig_query}: invalid signal", file=sys.stderr)
                return 1

    else:
        # default: use SIGTERM
        sig = signal.Signals["SIGTERM"]

    targets = args[targets_start:]
    status = 0

    if not targets:
        # they didn't pass any targets, so just print usage
        print(f"mash: kill: usage: {KILL_USAGE}", file=sys.stderr)
        return 1

    # at this point, we know the signal and all the targets that we need to send the signal to

    for target in targets:
        if target.startswith("%"):
            # this is a JOB target
            if not state.interactive:
                print(f"mash: kill: {target}: no job control", file=sys.stderr)
                status = 1
                continue

            try:
                # try to resolve the job
                job = mash.jobs.resolve_jobspec(target)
            except mash.jobs.JobSpecError as e:
                print(f"mash: kill: {e}", file=sys.stderr)
                status = 1
                continue

            was_stopped = job.is_stopped

            try:
                # attempt to send the signal to the job
                os.killpg(job.pgid, sig)
            except OSError as e:
                print(f"mash: kill: {target}: {e.strerror}", file=sys.stderr)
                status = 1
                continue

            # user-requested SIGCONT counts as being resumed too
            resumed = (sig == signal.SIGCONT)
              
            if was_stopped and sig not in SKIP_WAKEUP:
                # attempt to wake up job so that signal can be executed
                try:
                    os.killpg(job.pgid, signal.SIGCONT)
                    resumed = True
                except OSError:
                    # group may already be gone: that's not a failure
                    pass

            if resumed and was_stopped:
                # update our local process state if we did wake up the job
                for proc in job.procs:
                    if proc.state == "stopped":
                        proc.state = "running"
                # ...but it didn't get the terminal, so it's background
                job.background = True

            # if the job dies, it will be marked by the "reaping sweep" at the next prompt
        
        elif target.isascii() and target.isdigit():
            # this is a bare PID target
            pid = int(target)
            try:
                os.kill(pid, sig)

            except (OSError, OverflowError) as e:
                # we can get an overflow error if int works for Python but
                # it's too large to be converted to a C int
                reason = e.strerror if isinstance(e, OSError) else "No such process"
                print(f"mash: kill: ({pid}) - {reason}", file=sys.stderr)
                status = 1
                continue

        else:
            # not a job spec or a PID
            print(f"mash: kill: {target}: arguments must be process or job IDs", file=sys.stderr)
            status = 1
            continue

    return status
