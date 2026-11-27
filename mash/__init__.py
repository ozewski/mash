import sys

VERSION = "1.0.0"
MINIMUM_PYTHON_VERSION = (3, 10)

def python_version_check():
    py_version_string = ".".join(map(str, MINIMUM_PYTHON_VERSION))

    if sys.version_info < MINIMUM_PYTHON_VERSION:
        print(
            f"mash: fatal error: please upgrade to python {py_version_string} or newer to run mash", 
            file=sys.stderr
        )
        sys.exit(1)
