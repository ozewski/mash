# <img src="assets/icon.svg" alt="Project Logo" height="40" valign="middle"> MASH: Minimal Application Shell

A minimal shell implemented in Python, loosely based on Bash.

Minimum Python version supported: **`3.10`**

## Installation

If using this shell on Windows, WSL must be installed.

```
git clone https://github.com/ozewski/mash.git
./mash/run.py    # on Linux
mash/run.py      # on Windows
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

This shell was created as my final project for COSC 519 (Operating Systems) at Towson University, under the direction of Dr. Nicholas Phillips.
