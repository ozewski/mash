import platform
import readline
from shell.parser import tokenize

print(platform.release())
print(platform.version())
print()

while True:
    # TODO: add custom shell prompt with colors
    command = input("> ")
    print(tokenize(command))
