import os
import signal
import sys

import mash.jobs
from mash.state import state

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
            job = mash.jobs.resolve_jobspec(target)
        except mash.jobs.JobSpecError as e:
            print(f"mash: bg: {e}", file=sys.stderr)
            status = 1
            continue

        if not job.is_stopped:
            # this job is already in the background
            print(f"mash: bg: job {job.num} already in background", file=sys.stderr)
            status = 1
            continue

        job.background = True
        for proc in job.procs:
            if proc.state == "stopped":
                proc.state = "running"

        mash.jobs.touch(job)

        # marker computed after touch(), so the job just resumed is current
        current, previous = mash.jobs.current_and_previous()
        marker = mash.jobs.job_marker(job, current, previous)
        print(f"[{job.num}]{marker} {job.cmdline} &", flush=True)

        try:
            # send a signal to the process to wake itself up
            os.killpg(job.pgid, signal.SIGCONT)
        except ProcessLookupError:
            # same reasoning as in fg
            for proc in job.procs:
                if proc.state == "running":
                    proc.state = "done"
        
    return status
