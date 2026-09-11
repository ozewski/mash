import platform
import subprocess
import sys

def main():
    args = sys.argv[1:]
    if platform.system() == "Windows":
        cmd = ["wsl", "python3", "main.py", *args]
    else:
        cmd = ["python3", "main.py", *args]

    result = subprocess.run(cmd)
    sys.exit(result.returncode)

if __name__ == "__main__":
    main()
