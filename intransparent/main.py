from collections.abc import Sequence
from argparse import ArgumentParser, BooleanOptionalAction
import os
from pathlib import Path
import sys

import pandas as pd

from intransparent import (
    ingest_reports_per_country,
    reports_per_capita_country_year,
    REPORTS_PER_PLATFORM,
    ingest_reports_per_platform,
    encode_reports_per_platform,
    compare_all_platform_reports,
    format_table,
    format_latex,
    sgr,
)


def create_parser() -> ArgumentParser:
    parser = ArgumentParser(__package__)
    parser.add_argument(
        "--export-platform-data",
        action="store_true",
        help="Export platform data to \"data/csam-reports-per-platform.json\"",
    )
    format = parser.add_argument_group("output format")
    format.add_argument(
        "--latex", action="store_true", help="emit LaTeX instead of text"
    )
    format.add_argument(
        "--color", action=BooleanOptionalAction, help="force (no) color in output"
    )
    format.add_argument(
        "-v", "--verbose", action="store_true", help="enable verbose mode"
    )
    return parser


def _main(args: Sequence[str]) -> None:
    parser = create_parser()
    options = parser.parse_args(args[1:])

    if options.latex:
        term_width = 140
        heavy_rule = f"% {'=' * (term_width - 2)}"
        light_rule = f"% {'-' * (term_width - 2)}"

        def print_table(
            table: pd.DataFrame, *, title: str, highlights: None | str = None
        ) -> None:
            print(heavy_rule)
            print("%", title)
            print(light_rule)
            print(format_latex(table))
            print()

    else:
        isatty = sys.stderr.isatty()
        if options.color is None:
            options.color = isatty
        term_width, _ = os.get_terminal_size() if isatty else (80, None)
        heavy_rule = "━" * term_width
        light_rule = "─" * term_width

        def print_table(
            table: pd.DataFrame, *, title: str, highlights: None | str = None
        ) -> None:
            print(heavy_rule)
            print(
                format_table(
                    table,
                    title=title,
                    use_sgr=options.color,
                    highlights=highlights,
                )
            )
            print()

    if options.export_platform_data:
        json_path = Path('data/csam-reports-per-platform.json')
        tmp_path = json_path.with_suffix('.tmp.json')
        with open(tmp_path, mode='w', encoding='utf') as file:
            file.write('\n'.join(encode_reports_per_platform(REPORTS_PER_PLATFORM)))
        tmp_path.replace(json_path)

    disclosures = ingest_reports_per_platform(
        REPORTS_PER_PLATFORM,
    )
    comparisons = compare_all_platform_reports(disclosures)

    for platform, data in comparisons.items():
        print_table(data, title=platform)

    country_data = ingest_reports_per_country('data')
    for year, data in reports_per_capita_country_year(country_data):
        print_table(
            data.head(20),
            title=f'CSAM reports per capita per country {year}',
            highlights='reports_per_capita',
        )


def main(args: Sequence[str]) -> int:
    try:
        _main(args)
        return 0
    except Exception as x:
        print(x, file=sys.stderr)
        return 1
