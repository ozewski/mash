import platform
from shell.parser import tokenize

print(platform.release())
print(platform.version())
print()

while True:
    # TODO: up/down arrow key support
    command = input("> ")
    print(tokenize(command))
