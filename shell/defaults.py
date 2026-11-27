import os
import re
import readline
import signal
import sys
import termios

import shell.jobs
from shell.state import state

# All defaults should return a status number.

def _run_cd(path) -> int:
    saved_pwd = os.getcwd()
    try:
        os.chdir(path)
    except OSError as e:
        print(f"mash: cd: {path}: {e.strerror}", file=sys.stderr)
        return 1
    
    os.environ["OLDPWD"] = saved_pwd
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

    for arg in args:
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
        if not n.isdigit():
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

def jobs(*args) -> int:
    if args:
        print("mash: jobs: arguments not supported", file=sys.stderr)
        return 1

    current, previous = shell.jobs.current_and_previous()

    # list in job-number order; the markers show recency
    for job in sorted(shell.jobs.all_jobs(), key=lambda j: j.num):
        # the current/previous check matches bash conventions for table display
        marker = "+" if job is current else "-" if job is previous else " "
        print(shell.jobs.format_job(job, marker))

    return 0

def fg(*args) -> int:
    if len(args) > 1:
        print("mash: fg: too many arguments", file=sys.stderr)
        return 1

    if not state.interactive:
        # without job control, this command is a no-op
        print("mash: fg: no job control", file=sys.stderr)
        return 1

    try:
        # try to resolve the desired job
        job = shell.jobs.resolve_jobspec(args[0] if args else None)
    except shell.jobs.JobSpecError as e:
        print(f"mash: fg: {e}", file=sys.stderr)
        return 1

    print(job.cmdline)

    try:
        # give control to the process
        os.tcsetpgrp(state.tty_fd, job.pgid)
        if job.terminal_modes:
            # if the process had some special terminal settings, apply them
            termios.tcsetattr(state.tty_fd, termios.TCSADRAIN, job.terminal_modes)

    except (OSError, termios.error):
        # in case of an error, make sure to give back control to the terminal
        print(f"mash: fg: could not give terminal to job: {e}", file=sys.stderr)
        try:
            os.tcsetpgrp(state.tty_fd, state.shell_pgid)
        except OSError:
            # even taking back the terminal could fail,
            # but there's nothing we could do about it at this point
            pass
        return 1

    job.background = False

    for proc in job.procs:
        if proc.state == "stopped":
            proc.state = "running"

    try:
        # send a signal to the process to wake itself up
        os.killpg(job.pgid, signal.SIGCONT)
    except ProcessLookupError:
        # the internet says this could happen in rare circumstances where the whole group
        # is already done; in this case, update state accordingly
        for proc in job.procs:
            if proc.state == "running":
                proc.state = "done"
    
    return shell.jobs.wait_for_job(job)

def bg(*args) -> int:
    if not state.interactive:
        # without job control, this command is a no-op
        print("mash: bg: no job control", file=sys.stderr)
        return 1

    targets = args
    if not args:
        targets = [None]

    # using exit status tracker to allow one jobspec to be backgrounded even if another fails
    status = 0

    for target in targets:
        try:
            # try to resolve the desired job
            job = shell.jobs.resolve_jobspec(target)
        except shell.jobs.JobSpecError as e:
            print(f"mash: bg: {e}", file=sys.stderr)
            status = 1
            continue

        if job.is_stopped:
            # this job is already in the background
            print(f"mash: bg: job {job.num} already in background", file=sys.stderr)
            status = 1
            continue

        job.background = True
        for proc in job.procs:
            proc.state = "running"

        # why do we touch here?
        shell.jobs.touch(job)

        # what do we print here?

        try:
            # send a signal to the process to wake itself up
            os.killpg(job.pgid, signal.SIGCONT)
        except ProcessLookupError:
            # same reasoning as in fg
            for proc in job.procs:
                if proc.state == "running":
                    proc.state = "done"
        
    return status

# for these signals, wakeup after kill is skipped
SKIP_WAKEUP = (
    signal.Signals["SIGKILL"], # since it already kills stopped processes
    signal.Signals["SIGCONT"], # since it already wakes the job
    signal.Signals["SIGSTOP"], # since the user wants it to stay stopped
    signal.Signals["SIGTSTP"],
    signal.Signals["SIGTTIN"],
    signal.Signals["SIGTTOU"],
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
                print(f"mash: kill: {sig_query}: invalid signal", file=sys.stderr)
                return 1

        else:
            # kill -SIGPIPE or kill -PIPE
            sig_query = sig_query.upper()
            if not sig_query.startswith("SIG"):
                sig_query = "SIG" + sig_query
            
            try:
                sig = signal.Signals[sig_query]
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
                job = shell.jobs.resolve_jobspec(target)
            except shell.jobs.JobSpecError as e:
                print(f"mash: kill: {e}", file=sys.stderr)
                status = 1
                continue

            was_stopped = job.is_stopped

            try:
                # attempt to send the signal to the job
                os.killpg(job.pgid, sig)
            except OSError as e:
                print(f"mash: kill: {e}", file=sys.stderr)
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

            except OSError as e:
                print(f"mash: kill: ({pid}) - {e.strerror}", file=sys.stderr)
                status = 1
                continue

        else:
            # not a job spec or a PID
            print(f"mash: kill: {target}: arguments must be process or job IDs", file=sys.stderr)
            status = 1
            continue

    return status