import sys

import mash.jobs

def jobs(*args) -> int:
    # run job reap first thing so we have updated job table
    mash.jobs.reap_jobs()

    if args:
        print("mash: jobs: arguments not supported", file=sys.stderr)
        return 1

    current, previous = mash.jobs.current_and_previous()

    # list in job-number order; the markers show recency
    for job in sorted(mash.jobs.all_jobs(), key=lambda j: j.num):
        # the current/previous check matches bash conventions for table display
        marker = mash.jobs.job_marker(job, current, previous)
        print(mash.jobs.format_job(job, marker))

    return 0
