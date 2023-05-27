import os.path
import sys

if sys.version_info < (3, 10):
    print(f"{__package__} requires at least Python 3.10!")
    sys.exit(1)

from collections.abc import Sequence
from argparse import ArgumentParser, BooleanOptionalAction
import os

from intransparent import (
    REPORTS_PER_PLATFORM,
    ingest_reports_per_platform,
    export_reports_per_platform,
    compare_all_platform_reports,
    format_latex,
    format_text,
)


def create_parser() -> ArgumentParser:
    parser = ArgumentParser(__package__)
    parser.add_argument(
        "--export-json",
        action="store_true",
        help="export original data in JSON",
    )
    parser.add_argument(
        "--include-redundant",
        action="store_true",
        help="include redundant data rows",
    )
    parser.add_argument(
        "--print-dataset",
        action="store_true",
        help="print the full dataset after ingestion",
    )
    parser.add_argument("--latex", action="store_true", help="emit LaTeX")
    parser.add_argument(
        "--color",
        action=BooleanOptionalAction,
        help="do not colorize output",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="enable quiet mode",
    )
    group.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="enable verbose mode",
    )
    return parser


def main(args: Sequence[str]) -> None:
    parser = create_parser()
    options = parser.parse_args(args[1:])

    isatty = sys.stderr.isatty()
    if options.color is None:
        options.color = isatty

    if options.export_json:
        path = "./data/csam-reports-per-platform.json"
        if options.verbose:
            print('Writing dataset to "{path}"', file=sys.stderr)
        with open(path, mode="w", encoding="utf") as file:
            file.write(export_reports_per_platform(REPORTS_PER_PLATFORM))

    term_width, _ = os.get_terminal_size() if isatty else (80, None)
    heavy_rule = "━" * term_width
    light_rule = "─" * term_width

    def print_platform(name: str) -> None:
        if not options.color:
            print(("% " if options.latex else "# ") + name + ":", file=sys.stderr)
        else:
            print(heavy_rule, file=sys.stderr)
            print(name, file=sys.stderr)
            print(light_rule, file=sys.stderr)

    disclosures = ingest_reports_per_platform(
        REPORTS_PER_PLATFORM,
        verbose=options.verbose
    )
    if options.print_dataset:
        for platform, data in disclosures.items():
            print_platform(platform)
            print(data, file=sys.stderr)
            print(file=sys.stderr)

    comparisons = compare_all_platform_reports(disclosures)
    if not options.quiet:
        for platform, data in comparisons.items():
            print_platform(platform)
            if options.latex:
                fmt = format_latex
            else:
                fmt = lambda p, d: format_text(p, d, use_sgr=options.color)
            print(fmt(platform, data), file=sys.stderr)
            print(file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv)
