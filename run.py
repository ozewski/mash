#!/usr/bin/env python3

import os
import platform
import subprocess
import sys

from mash import python_version_check

python_version_check()

def main():
    args = sys.argv[1:]
    script_dir = os.path.dirname(os.path.abspath(__file__))

    if platform.system() == "Windows":
        script_dir = script_dir.replace("\\", "/")
        result = subprocess.run(
            ["wsl", "wslpath", script_dir],
            capture_output=True,
            text=True,
        )

        main_path = result.stdout.strip() + "/main.py"
        cmd = ["wsl", "python3", main_path, *args]
    else:
        main_path = os.path.join(script_dir, "main.py")
        cmd = ["python3", main_path, *args]

    result = subprocess.run(cmd)
    sys.exit(result.returncode)

if __name__ == "__main__":
    main()
