import shlex

def tokenize(command: str) -> list[str]:
    lexer = shlex.shlex(command, posix=True, punctuation_chars="|<>")
    lexer.whitespace_split = True
    lexer.commenters = ""

    return list(lexer)

def parse(tokens: list[str]):
    return [] # TODO
