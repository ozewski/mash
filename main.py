import platform
import readline
from pprint import pprint
from shell.parser import parse, tokenize

print(platform.release())
print(platform.version())
print()

while True:
    # TODO: add custom shell prompt with colors
    command = input("> ")
    tokens = tokenize(command)
    pprint(tokens)
    pprint(parse(tokens))
