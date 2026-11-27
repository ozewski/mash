# <img src="assets/icon.svg" alt="Project Logo" height="40" valign="middle"> MASH: Minimal Application Shell

A minimal shell implemented in Python, loosely based on Bash.

MASH supports most common shell workflows. However, this shell is experimental and there are some known limitations. See below for more information about the full feature set and what is not yet supported.

## Installation

MASH requires Python `3.10` or newer to run. 

```
git clone https://github.com/ozewski/mash.git
./mash/run.py    # on Linux
mash/run.py      # on Windows
```

**Supported platforms:** Linux, Mac, Windows (partial)
- MASH on Windows operates using WSL, which must be installed.

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

## Issues and future work

This shell supports many common shell workflows. However, there are two critical issues that prevent some workflows:

1) Due to the nature of the built-in Python `shlex` shell lexer, commands that have number arguments prior to I/O redirections are improperly parsed, and quoting information is dropped. 
    - For example, `echo "2" > file.txt` is treated as `echo 2> file.txt`.
2) Pipelines cannot be created using built-in shell commands, such as `cd` and `history`.
    - For example, `history | grep cat` will fail.

Some other common features that are not supported:
* Shell variables
* Non-interactive mode
* Many other built-in commands supported by the POSIX standard
* Scripting

**Some suggested future goals to clear up critical workflow issues:**
1) Add support for using built-in shell commands in pipelines.
2) Implement a custom lexer, which can index tokens as contextual objects (i.e. information about quoting).
3) Add a parsing/replacement mechanism for shell variables.

## About this project

This shell was created by Michael Oltarzewski as his final project for COSC 519 (Operating Systems) at Towson University, under the direction of Dr. Nicholas Phillips. It was presented on December 2, 2026.

This project will not be actively maintained as of December 2026. Any contributors are welcome to reach out or open a pull request. Please refer to the "Future Work" section for more information.
