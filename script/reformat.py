import argparse
from contextlib import ExitStack
import re
import sys
from typing import Any


FORMAT_STRING = re.compile(
    r"""
    ^ (?:
        [0-9]
        | `[^`]*`
    )* $
    """,
    re.VERBOSE
)


SIMPLE_TOKEN = re.compile(
    r"""
    ^ (?:
        [0-9]+
        | [a-zA-Z] [a-zA-Z0-9]*
    ) $
    """,
    re.VERBOSE
)


NUMBER_TOKEN = re.compile(
    r"""
        [0-9]
        (?:
            [0-9]
            | [,] [0-9]
        )*
    """,
    re.VERBOSE
)


def parse_format(format: str) -> list[int | str]:
    if not FORMAT_STRING.match(format):
        raise ValueError(f'invalid format string "{format}"')

    parts = []
    for index, item in enumerate(format.split("`")):
        if index % 2 == 0:
            for f in [*item]:
                parts.append(int(f))
        else:
            parts.append(item)

    return parts


def parse_line(line: str) -> list[str]:
    """Parse the given line into a list of tokens."""
    tokens = line.split()

    parts = []
    for token in tokens:
        if NUMBER_TOKEN.match(token):
            break
        parts.append(token)

    if parts:
        first = " ".join(parts)
        return [first, *tokens[len(parts):]]
    else:
        return tokens


def parse_lines(lines: list[str]) -> tuple[list[list[str]], list[int]]:
    """
    Parse all lines into tokens. Also determine the maximum token width for each
    position.
    """
    tokenized_lines = []
    count = 0
    widths = []

    for line in lines:
        line = line.strip()
        if line == "" or line.startswith("#"):
            continue

        tokens = parse_line(line)
        count = max(count, len(tokens))
        while len(widths) < count:
            widths.append(0)

        for i, t in enumerate(tokens):
            widths[i] = max(widths[i], len(t) + 5)

        tokenized_lines.append(tokens)

    return tokenized_lines, widths


def format_token(value: None | str) -> str:
    """Format the token."""
    if value is None or value == "0":
        return ""
    if SIMPLE_TOKEN.match(value):
        return value
    else:
        return f'"{value}"'


def format_tokens(
    tokens: list[str], widths: list[int], format: list[int | str], compact: bool = False
) -> list[str]:
    """
    Format the tokens selected by the indices in order. If `compact` is `False`,
    also right-pad the token so that it has the correct width for its index
    position.
    """
    formatted_tokens = []

    for part in format:
        is_text = isinstance(part, str)
        t = part if is_text else tokens[part]
        s = format_token(t)

        if not compact:
            w = len(part) + 2 if is_text else widths[part]
            s = s.ljust(w)

        formatted_tokens.append(s)

    return formatted_tokens


def process(options: Any) -> None:
    """Process input and output as specified by the options."""
    format = parse_format(options.format)

    with open(options.input, mode="r", encoding="utf8") as file:
        lines = file.readlines()

    tokenized_lines, widths = parse_lines(lines)

    with ExitStack() as stack:
        if options.output is not None:
            stream = stack.enter_context(open(options.output, mode="w", encoding="utf8"))
        else:
            stream = sys.stdout

        for tokens in tokenized_lines:
            ts = format_tokens(tokens, widths, format, compact=options.compact)
            stream.write(",".join(ts))
            stream.write("\n")


def main(args: list[str]) -> None:
    """Run this tool."""
    parser = argparse.ArgumentParser(
        "reformat",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "-i", "--input",
        default="raw.txt",
        help="read from file"
    )
    parser.add_argument(
        "-o", "--output",
        help="write to file"
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="use compact format without spaces",
    )
    parser.add_argument(
        "-f", "--format",
        default="012",
        help="provide a format string using",
    )

    options = parser.parse_args(args)
    process(options)


if __name__ == "__main__":
    main(sys.argv[1:])
