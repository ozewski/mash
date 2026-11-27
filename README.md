# MASH: Minimal Application Shell

A minimal shell implemented in Python, loosely based on Bash.

## Installation

If using this shell on Windows, WSL must be installed.

```
git clone https://github.com/ozewski/mash.git
python3 mash/run.py
```

## Features
* Dynamically-sized prompt
* Executing system programs with arguments
* Command history
* I/O redirection
* Pipelines
* Certain shell builtins supported:
    * `cd`, `exit`, `export`, `history`
* Job control
    * CTRL+Z to put jobs in the background
    * Commands supported: `jobs`, `fg`, `bg`, `kill`

Known issues:
* Shell variables are not supported.
* Pipelines cannot be created with built-in commands, such as `cd` and `history`.
* `run.py` is not executable on Linux.

This shell was created as my final project for COSC 519 (Operating Systems) at Towson University, under the direction of Dr. Nicholas Phillips.
