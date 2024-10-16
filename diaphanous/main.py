from collections.abc import Sequence
from functools import partial
from pathlib import Path
import sys
import traceback

import pandas as pd

from diaphanous import (
    ingest_reports_per_country,
    reports_per_capita_country_year,
    create_map,
    show_map,
    REPORTS_PER_PLATFORM,
    encode_reports_per_platform,
    YEAR_LABELS,
    show,
    to_schema,
    fetch_populations,
)


# ======================================================================================


def just_map() -> None:
    country_data = ingest_reports_per_country('./data')
    map_data = country_data.reports_per_capita.reset_index()
    map_data['labels'] = (
        map_data['country'].astype(str)
        + ':<br>'
        + map_data['reports_per_capita'].apply(lambda v: f'{v:.5f}')
        + ' ('
        + map_data['year'].astype(str)
        + ')'
    )
    fig = create_map(
        map_data,
        discretization=0,
        with_panels=True,
        with_antarctica=True,
    )
    fig.write_image(f'./figure/reports-per-capita.svg')


def reports_per_country(section: int = -1) -> None:
    # ----------------------------------------------------------------------------------

    def secnum(subsection: int) -> str:
        return '' if section == -1 else f'{section}.{subsection} '

    country_data = ingest_reports_per_country('../data')

    show(f'<h2>{secnum(2)}Regions Ranked by CSAM Reports</h2>')
    most_reports = (
        country_data.reports_per_capita.groupby(['year', 'region'])
        .sum(numeric_only=True)
        .sort_values(by='reports', ascending=False)
        .drop(columns=['arab_league'])
    )

    # Recompute reports per capita because adding countries' values most
    # certainly isn't the right thing to do...
    most_reports['reports_per_capita'] = (
        most_reports['reports'] / most_reports['population']
    )

    adjusted_reports = most_reports.sort_values('reports_per_capita', ascending=False)

    for year in YEAR_LABELS:
        show(f'<h3>{year}</h3>')
        show(
            most_reports[most_reports.index.get_level_values('year') == year],
            caption=f'Regions by CSAM Reports {year}',
            highlight_columns=['reports', 'reports_pct'],
        )
        show(
            adjusted_reports[adjusted_reports.index.get_level_values('year') == year],
            caption=f'Regions by Population-Adjusted CSAM Reports {year}',
            highlight_columns='reports_per_capita',
        )
        if year != YEAR_LABELS[-1]:
            show('<hr>')

    # ----------------------------------------------------------------------------------
    show(f'<h2>{secnum(3)}Countries Ranked by CSAM Reports per Capita</h2>')
    rpc_range = country_data.reports_per_capita.agg(
        {'reports_per_capita': ['min', 'max']}
    )
    show(rpc_range, caption='Range of Reports per Capita', margin_bottom=0)

    for year, year_data in reports_per_capita_country_year(country_data):
        top = year_data.head(30)
        rank = top.index[top['iso3'] == '\u262a'][0]
        show(
            top,
            caption=f'Reports per Capita and Country {year}',
            highlight_columns='reports_per_capita',
            highlight_rows=rank,
            margin_top=2,
            margin_bottom=0,
        )

        in_arab_league = top['arab_league'].sum()
        if year == '2022':
            assert top.tail(10)['arab_league'].sum() == 0

        show(
            f"""
            {in_arab_league} out of 20 countries with the most CSAM reports per
            capita in {year} are members of the Arab League. If the Arab League
            were a country, its rank would be {rank}.<br><br>
            """
        )

        if year != YEAR_LABELS[-1]:
            show('<hr>')

    show(
        """
        <p>Member countries of the Arab League feature unusually prominently
        when ranking countries by CSAM reports per capita. Notably, either Libya
        or the United Arab Emirates is the worst ranked country. The substantial
        differences between the two countries would seem to exclude wealth,
        political stability, and effective policing as likely causes and instead
        point to some shared cultural trait as likely reason.</p>

        <p>Note that such a shared cultural trait may be an actual trait or a
        perceived trait.</p>
        """
    )

    # ----------------------------------------------------------------------------------
    show(f'<h2>{secnum(4)}Mapping CSAM Reports per Capita and Year</h2>')
    map_data = country_data.reports_per_capita.copy()
    map_data = map_data.reset_index()
    show(map_data, show_schema=True, caption='map_data')

    # The text for hover labels (without clunky hover data)
    map_data['labels'] = (
        map_data['country'].astype(str)
        + ':<br>'
        + map_data['reports_per_capita'].apply(lambda v: f'{v:.5f}')
        + ' ('
        + map_data['year'].astype(str)
        + ')'
    )

    fig = create_map(
        map_data, with_panels=False, with_antarctica=True, with_animation=True
    )
    show_map(fig)

    fig = create_map(
        map_data,
        discretization=0,
        with_panels=True,
        with_albers=True,
        with_antarctica=True,
    )
    show_map(fig)
    fig.write_image(f'../figure/countries.svg')

# ======================================================================================


def logger(df: pd.DataFrame, caption: None | str = None) -> None:
    if caption is not None:
        title = f'Table "{caption}"'
        print(title)
        print(f'{"-" * len(title)}\n')
        print(to_schema(df).to_string())
        print('\n')


def _main(args: Sequence[str]) -> int:
    if "--fetch-populations" in args:
        fetch_populations("data/populations.csv")

    # Export platform data
    print('1. Exporting "data/ocse-reports-per-year-country-capita"\n')
    country_data = ingest_reports_per_country('./data', logger=logger)
    country_data.reports_per_capita.reset_index().to_csv(
        'data/ocse-reports-per-year-country-capita.csv',
        index=False,
        columns=[
            'year',
            'iso2',
            'iso3',
            'country',
            'reports',
            'reports_pct',
            'population',
            'population_pct',
            'reports_per_capita',
            'region',
            'superregion',
            'continent',
            'arab_league',
        ],
    )

    print('2. Exporting "data/ocse-reports-per-platform.json"')
    json_path = Path('data/ocse-reports-per-platform.json')
    tmp_path = json_path.with_suffix('.tmp.json')
    with open(tmp_path, mode='w', encoding='utf') as file:
        file.write('\n'.join(encode_reports_per_platform(REPORTS_PER_PLATFORM)))
    tmp_path.replace(json_path)
    print('Done!')
    return 0


def main(args: Sequence[str]) -> int:
    try:
        return _main(args)
    except Exception as x:
        traceback.print_exc(file=sys.stderr)
        return 1
