"""
Support for exporting LaTeX to Word's docx format with pandoc.

This script cleans up the bibliography as well as the LaTeX sources. Tables and
figures are removed as well.
"""
import re

BIBCITE = re.compile(r'\\bibcite\{([^}]+)\}')
DOUBLE_CURLY_OPEN = re.compile(r'\{\{(?=[A-Za-z])')
DOUBLE_CURLY_CLOSE = re.compile(r'(?<=[A-Za-z])\}\}')
FIGURE1 = re.compile(r'\\ref\{fig:reports\}')
FIGURE2 = re.compile(r'\\ref\{fig:meta\}')
FIGURE3 = re.compile(r'\\ref\{fig:reports-audit\}')
TABLE = re.compile(r'\\ref\{tab:survey\}')
VEE = re.compile(r'\\V\{([A-Z0-9&\\]+)\}')

def process_bibtex(bib: str, aux: str, out: str) -> None:
    print("Preparing citations for export")

    with open(aux, mode="r", encoding="utf8") as fd:
        citations = BIBCITE.findall(fd.read())

    entries = {}
    with open(bib, mode="r", encoding="utf8") as fd:
        while (line := fd.readline()):
            if not line.startswith("@"):
                continue
            start = line.index("{")
            stop = line.index(",")
            key = line[start + 1 : stop]

            value = [line]
            line = fd.readline()
            while not line.startswith("}"):
                value.append(line)
                line = fd.readline()
            value.append(line)

            entries[key] = value

    with open(out, mode="w", encoding="utf8") as fd:
        for index, citation in enumerate(citations):
            if index != 0:
                print("", file=fd)
            lines = entries[citation]
            for line in lines:
                if not line.startswith(" "):
                    print(line, end="", file=fd)
                    continue

                key, _, _ = line.partition("=")
                key = key.strip()
                if key in ("file", "issn", "langid", "urldate"):
                    continue

                if key == "type":
                    line = DOUBLE_CURLY_OPEN.sub("", line)
                    line = DOUBLE_CURLY_CLOSE.sub("", line)

                if key.strip() not in ("urldata", "langid", "file"):
                    print(line, end="", file=fd)


def process_latex(input: str, output: str) -> None:
    print("Preparing LaTeX source for export")

    with (
        open(input, mode="r", encoding="utf8") as fd_in,
        open(output, mode="w", encoding="utf8") as fd_out,
    ):
        while (line := fd_in.readline()):
            if line.startswith("\\begin{table}"):
                while not line.startswith("\\end{table}"):
                    line = fd_in.readline()
                continue
            if line.startswith("\\begin{figure}"):
                while not line.startswith("\\end{figure}"):
                    line = fd_in.readline()
                continue
            if line.startswith("\\begin{anonsuppress}"):
                while not line.startswith("\\end{anonsuppress}"):
                    line = fd_in.readline()
                continue
            if line.startswith("\\ifdefined\\ToWordProcessor\\else"):
                while not line.startswith("\\fi"):
                    line = fd_in.readline()
                continue
            if line.startswith("\\ifdefined\\ToWordProcessor"):
                print(line, end="", file=fd_out)
                line = fd_in.readline()
                while not line.startswith("\\else"):
                    print(line, end="", file=fd_out)
                    line = fd_in.readline()
                while not line.startswith("\\fi"):
                    line = fd_in.readline()
                print(line, end="", file=fd_out)
                continue

            line = TABLE.sub("1", line)
            line = FIGURE1.sub("1", line)
            line = FIGURE2.sub("2", line)
            line = FIGURE3.sub("3", line)
            line = VEE.sub(r"\1", line)
            print(line, end="", file=fd_out)

if __name__ == "__main__":
    process_bibtex("bibliography.bib", "report.aux", "export.bib")
    process_latex("report.tex", "export-main.tex")
