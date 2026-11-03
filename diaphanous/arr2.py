from io import StringIO
import os
import re
import shutil
import subprocess
from typing import Literal

import polars as pl

# The minimal R library for emitting results that need to be communicated back
# to the Python process. It supports text, horizontal rules, and data frames.
# The source code of the library breaks apart the result markers to avoid
# unintended matches in the output. The markers are printed before formatting
# the result to avoid missing any output.
_LIBR = """
emit_text <- function(value = NULL, section = "TEXT") {
    cat("#", "#", "#", " BEGIN-SECTION ", section, " #", "#", "#", "\\n", sep="")

    if (is.null(value)) {
        cat()
    } else if (is.character(value)) {
        cat(value, "\\n", sep="")
    } else if (is.data.frame(value)) {
        write.csv(value, file="", row.names=FALSE)
    } else {
        lines <- capture.output(print(value))
        lines <- gsub("\\t", "    ", lines)
        for (line in lines) {
            cat(line, "\\n", sep="")
        }
    }

    cat("#", "#", "#", " END-SECTION ", section, " #", "#", "#", "\\n", sep="")
}

emit_rule <- function(weight = 1) {
    if (weight == 0) {
        emit_text("────────────────────────────────────────────────────────────────────────────────")
    } else if (weight == 1) {
        emit_text("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    } else if (weight == 2) {
        emit_test("════════════════════════════════════════════════════════════════════════════════")
    }
}

# Return a data table provided either as a data frame or as vectors with the row data
emit_data <- function(...) {
    args <- list(...)

    if (length(args) == 1 && do.call(is.data.frame, args)) {
        emit_text(args[[1]], section = "DATA")
    } else {
        emit_text(
            paste0(
                map(
                    list(...),
                    \\(row) paste0(format(row, trim=TRUE, justify="none"), collapse=",")
                ),
                collapse="\\n"
            ),
            section = "DATA"
        )
    }
}
"""

_MARKER_REGEX = re.compile(
    r"### BEGIN-SECTION ([A-Z]+) ###(.*?)### END-SECTION ([A-Z]+) ###",
    re.DOTALL,
)
_WIDTH, _ = shutil.get_terminal_size()
_IS_DEBUG = bool(os.getenv("DEBUG"))

def run_r(data: pl.DataFrame, template: str) -> tuple[list[str], list[pl.DataFrame]]:
    if len(data) == 1:
        values = data.row(0)
    elif len(data.columns) == 1:
        values = data.get_column(data.columns[0]).to_list()
    else:
        values = None

    if values is not None:
        input = template.format(VECTOR_DATA=", ".join((str(v) for v in values)))
    else:
        buffer = StringIO()
        data.write_csv(buffer)
        input = template.format(CSV_DATA=buffer.getvalue())

    if _IS_DEBUG:
        print_heading("R Input", weight = "light")
        print(input)

    completion = subprocess.run(["R", "--vanilla"],
        input=_LIBR + input,
        encoding="utf8",
        stderr=subprocess.STDOUT,
        stdout=subprocess.PIPE,
    )
    output = completion.stdout

    if _IS_DEBUG:
        print_heading("R Output", weight = "light")
        print(output)

    if completion.returncode != 0:
        raise ValueError(f"R exited due to error:\n{output}")

    sections = _MARKER_REGEX.findall(output)
    if not sections:
        raise ValueError(f"R did not produce an output section: {output}")

    text_sections = []
    data_sections = []
    for (label, fragment, label_too) in sections:
        if label != label_too:
            raise ValueError(
                f"output section starts with {label} but ends with {label_too}"
            )

        fragment = fragment.strip() + "\n"
        if label == "TEXT":
            text_sections.append(fragment)
        elif label == "DATA":
            data_sections.append(pl.read_csv(StringIO(fragment)))
        else:
            raise ValueError(f"unknown output section {label}")

    return text_sections, data_sections


def print_heading(
    title: None | str = None, weight: Literal["light", "heavy", "double"] = "double",
) -> None:
    if weight == "light":
        dash = "─"
    elif weight == "heavy":
        dash = "━"
    else:
        dash = "═"

    if title is None:
        title = ""
    else:
        title = f" {title} "

    print(f"\n\n{dash * 4}{title}{dash * (_WIDTH - 4 - len(title))}\n")
