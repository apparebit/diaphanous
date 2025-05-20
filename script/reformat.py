import re

PATTERN = re.compile(
    r"""
        ^
        (?P<country>[-A-Za-z,'/ ()]+)
        (?P<n1>[0-9,]+) [ ]+
        (?P<n2>[0-9,]+) [ ]+
        (?P<n3>[0-9,]+)
        $
    """,
    re.VERBOSE
)


def format_value(value):
    if value == "0":
        return ","
    elif "," in value:
        return f',"{value}"'
    else:
        return f',{value}'


def format_line(line, out):
    match = PATTERN.match(line)
    assert match is not None

    country = f'{match.group("country").strip()}'
    n1 = format_value(match.group("n1"))
    n2 = format_value(match.group("n2"))

    out.write(f'{country:<50}{n1:<15}{n2:<15}\n')


def process():
    with open("raw.txt", mode="r", encoding="utf8") as file:
        lines = file.readlines()

    with open("formatted.txt", mode="w", encoding="utf8") as file:
        for line in lines:
            format_line(line, file)


if __name__ == "__main__":
    process()
