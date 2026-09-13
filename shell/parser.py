import shlex

from shell.command import Command, FdDuplication, FileRedirection, Pipeline

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

def _is_operator(token: str):
    return token in [">", ">>", "<", ">&"]

def _is_number(token: str):
    return token.isascii() and token.isdigit()

def parse(tokens: list[str]) -> Pipeline:
    pipeline = [Command(program=tokens[0])]
    i = 1
    fd_arg = None

    while i < len(tokens):
        command = pipeline[-1]  # get final command
        token = tokens[i]

        if token == "|":
            # pipe token
            # stop processing current command and create new command in pipeline
            new_command = Command(program=tokens[i+1])
            pipeline.append(new_command)

            i += 2
            continue

        elif _is_number(token):
            # numeric token
            if _is_operator(tokens[i + 1]):
                # part of an operator; save this value
                fd_arg = int(token)
            else:
                # otherwise, just part of the command args
                command.args.append(token)

            i += 1
            continue

        elif _is_operator(token):
            # operator token
            if token == "&>":
                # duplication; requires number following
                if not _is_number(tokens[i+1]):
                    raise ValueError("Dup requires following argument to be a fd")
                
                target = int(tokens[i+1])
                dup = FdDuplication(fd=(fd_arg or 1), target=target)
                command.redirections.append(dup)

                i += 2
                continue

            else:

                i += 1

        else:
            # all other valid tokens
            command.args.append(token)

            i += 1
            continue

    return Pipeline(commands=pipeline) # TODO
