import shlex

from shell.command import Command, FdDuplication, FileRedirection, Pipeline, RedirectOp

"""
General rules for parsing symbols:

1. If a bare read operator is given (< rather than n<), n=0 [stdin] by default.
2. If a bare write operator is given (> or >> rather than n> or n>>), n=1 [stdout] by default.
3. If a read or write operator is given, immediately followed by an & symbol, this is to be parsed as a FdDuplication.
    a. The & symbol must be followed by a number token, indicating the dup target.
    b. Duplications are always write operations (default n=1 [stdout]).
4. Otherwise, with no & symbol, the operation is to be parsed as a FileRedirection.
"""

class ParseError(Exception):
    pass

# Parser helpers

def is_operator(token: str) -> bool:
    return token in [">", ">>", "<", ">&"]

def is_number(token: str) -> bool:
    return token.isascii() and token.isdigit()

def next_token(tokens: list[str], i: int) -> str:
    # searches for the next token
    # if it doesn't exist, throws ParseError

    if i < len(tokens) - 1:
        return tokens[i + 1]
    else:
        raise ParseError("Expected more arguments")

def next_token_safe(tokens: list[str], i: int) -> str | None:
    # like next_token, but safely returns None instead of throwing error

    if i < len(tokens) - 1:
        return tokens[i + 1]
    else:
        return None

# End parser helpers

def tokenize(command: str) -> list[str]:
    lexer = shlex.shlex(command, posix=True, punctuation_chars="|<>&")
    lexer.whitespace_split = True
    lexer.commenters = ""
    return list(lexer)

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
            new_command = Command(program=next_token(tokens, i))
            pipeline.append(new_command)

            i += 2
            continue

        elif is_number(token):
            # numeric token
            next = next_token_safe(tokens, i)

            if type(next) is str and is_operator(next):
                # part of an operator; save this value
                fd_arg = int(token)
            else:
                # otherwise, just part of the command args
                command.args.append(token)

            i += 1
            continue

        elif is_operator(token):
            # operator token
            next = next_token(tokens, i)

            if token == ">&":
                # duplication; requires number following
                if not is_number(next):
                    raise ParseError("Dup target is not a fd")
                
                target = int(next)
                dup = FdDuplication(fd=(fd_arg or 1), target=target)
                command.redirections.append(dup)

                i += 2
                continue

            else:
                # redirection
                fd = 0
                op = RedirectOp.READ

                match token:
                    case "<":
                        fd = fd_arg or 0
                        op = RedirectOp.READ
                    case ">":
                        fd = fd_arg or 1
                        op = RedirectOp.WRITE_TRUNC
                    case ">>":
                        fd = fd_arg or 1
                        op = RedirectOp.WRITE_APPEND

                redirection = FileRedirection(
                    fd=fd, 
                    op=op, 
                    path=next
                )

                command.redirections.append(redirection)
                
                i += 2
                continue

        else:
            # all other valid tokens
            command.args.append(token)

            i += 1
            continue

    return Pipeline(commands=pipeline)
