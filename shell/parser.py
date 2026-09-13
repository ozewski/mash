import shlex

from shell.command import Command, FdDuplication, FileRedirection, Pipeline, RedirectOp

"""
General rules for parsing symbols:

1. If a bare read operator is given (< rather than n<), n=0 [stdin] by default.
2. If a bare write operator is given (> or >> rather than n> or n>>), n=1 [stdout] by default.
3. If a read or write operator is given, immediately followed by an & symbol, this is to be parsed as a FdDuplication.
    a. The & symbol must be followed by a number token, indicating the dup target.
    b. Duplications follow read/write default n values based on the according direction of the arrow.
4. Otherwise, with no & symbol, the operation is to be parsed as a FileRedirection.
"""

class ParseError(Exception):
    """Raised when malformed input syntax prevents complete command parsing."""
    pass

# Parser helpers

safe_or = lambda x, y: y if x is None else x

def is_io_operator(token: str) -> bool:
    return token in [">", ">>", "<", ">&", "<&"]

def is_number(token: str) -> bool:
    return token.isascii() and token.isdigit()

def next_token(tokens: list[str], i: int) -> str:
    # searches for the next token
    # if it doesn't exist, throws ParseError

    if i < len(tokens) - 1:
        return tokens[i + 1]
    else:
        raise ParseError("Expected more arguments")

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

            fd_arg = None
            i += 2
            continue

        elif is_number(token):
            # numeric token
            try:
                next = next_token(tokens, i)
            except ParseError:
                # we're at the end of the command: this can't be part of an operator
                command.args.append(token)
                break;

            if is_io_operator(next):
                # part of an operator; save this value
                fd_arg = int(token)
            else:
                # otherwise, just part of the command args
                command.args.append(token)

            i += 1
            continue

        elif is_io_operator(token):
            # operator token
            next = next_token(tokens, i)

            if token in (">&", "<&"):
                # duplication; requires number following
                if not is_number(next):
                    raise ParseError("Dup target is not a fd")
                
                target = int(next)
                fd = safe_or(
                    fd_arg,
                    1 if token == ">&" else 0
                )

                dup = FdDuplication(fd=fd, target=target)
                command.redirections.append(dup)

                fd_arg = None
                i += 2
                continue

            else:
                # redirection
                fd = 0
                op = RedirectOp.READ

                match token:
                    case "<":
                        fd = safe_or(fd_arg, 0)
                        op = RedirectOp.READ
                    case ">":
                        fd = safe_or(fd_arg, 1)
                        op = RedirectOp.WRITE_TRUNC
                    case ">>":
                        fd = safe_or(fd_arg, 1)
                        op = RedirectOp.WRITE_APPEND

                redirection = FileRedirection(
                    fd=fd, 
                    op=op, 
                    path=next
                )

                command.redirections.append(redirection)

                fd_arg = None
                i += 2
                continue

        else:
            # all other valid tokens
            command.args.append(token)

            i += 1
            continue

    return Pipeline(commands=pipeline)

def parse_command(line: str) -> Pipeline:
    """Parses a MASH command into a runnable Pipeline."""
    try:
        tokens = tokenize(line)
    except ValueError as e:
        raise ParseError("Could not parse command") from e

    return parse(tokens)
