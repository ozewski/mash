import shlex

from shell.command import Command, Pipeline

"""
General rules for parsing symbols:

1. If a bare read operator is given (< rather than n<), n=0 [stdin] by default.
2. If a bare write operator is given (> or >> rather than n> or n>>), n=1 [stdout] by default.
3. If a read or write operator is given, immediately followed by an & symbol, this is to be parsed as a FdDuplication.
    a. The & symbol must be followed by a number token, indicating the dup target.
    b. Duplications are always write operations (default n=1 [stdout]).
4. Otherwise, with no & symbol, the operation is to be parsed as a FileRedirection.
"""

def tokenize(command: str) -> list[str]:
    lexer = shlex.shlex(command, posix=True, punctuation_chars="|<>&")
    lexer.whitespace_split = True
    lexer.commenters = ""
    return list(lexer)

def parse(tokens: list[str]) -> Pipeline:
    pipeline = []
    command = Command(program=tokens[0])



    return Pipeline(commands=[]) # TODO
