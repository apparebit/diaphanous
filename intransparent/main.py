from collections.abc import Sequence
from functools import partial
from pathlib import Path
import sys
import traceback

import pandas as pd

from intransparent import (
    ingest_reports_per_country,
    reports_per_capita_country_year,
    create_map,
    show_map,
    REPORTS_PER_PLATFORM,
    ingest_reports_per_platform,
    reshape_reports_per_platform,
    encode_reports_per_platform,
    compare_all_platform_reports,
    without_populations,
    YEAR_LABELS,
    show,
    to_schema,
)

import intransparent.meta as meta

# ======================================================================================

def just_map() -> None:
    country_data = ingest_reports_per_country('./data')
    map_data = country_data.reports_per_capita.reset_index()
    map_data['labels'] = (
        map_data['country'].astype(str) + ':<br>' +
        map_data['reports_per_capita'].apply(lambda v: f'{v:.5f}') + ' (' +
        map_data['year'].astype(str) + ')'
    )
    fig = create_map(
        map_data,
        discretization=0,
        with_panels=True,
        with_antarctica=True,
    )
    fig.write_image(f'csam-reports-per-capita.svg')


def reports_per_country(section: int) -> None:
    show(f'<h1>{section}.  CSAM Reports per Country</h1>')
    show(f'<h2>{section}.1 Data Schemas</h2>')

    logger = partial(show, show_schema=True, margin_bottom=2)
    country_data = ingest_reports_per_country('./data', logger=logger)

    countries_without, reports_without = (
        without_populations(country_data.reports, country_data.populations))
    show(f'{countries_without.shape[0]} countries have reports but not population '
        'statistics. They also account for very few reports.')
    show(reports_without, caption='Reports for Countries<br>w/o Population Stats')

    # ----------------------------------------------------------------------------------
    show(f'<h2>{section}.2 Regions Ranked by CSAM Reports</h2>')
    most_reports = (
        country_data.reports_per_capita
        .groupby(['year', 'region'])
        .sum(numeric_only=True)
        .sort_values(by='reports', ascending=False)
        .drop(columns=['arab_league'])
    )
    for year in YEAR_LABELS:
        top20 = most_reports.query(f'year == "{year}"').head(20)
        show(
            top20,
            caption=f'Regions by CSAM Reports {year}',
            highlight_columns=['reports', 'reports_pct'],
        )

    # ----------------------------------------------------------------------------------
    show(f'<h2>{section}.3 Countries Ranked by CSAM Reports per Capita</h2>')
    rpc_range = country_data.reports_per_capita.agg(
        {'reports_per_capita': ['min', 'max']})
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

        show(f"""
            {in_arab_league} out of 20 countries with the most CSAM reports per
            capita in {year} are members of the Arab League. If the Arab League
            were a country, its rank would be {rank}.<br><br>
        """)

    show("""
        <p>Member countries of the Arab League feature unusually prominently
        when ranking countries by CSAM reports per capita. Notably, Libya and
        the United Arab Emirates each rank worst for two out of four years
        2019–2022. The substantial differences between the two countries would
        seem to exclude wealth, political stability, and effective policing as
        likely cause and instead point to some shared cultural trait as likely
        reason.</p>

        <p>However, we cannot tell whether such a shared cultural trait is
        internal or external to the population, e.g., reflects an actual
        difference in attitudes towards CSAM or is the result of biases in
        content moderation. In either case, the data for 2022 shows that other
        countries are rapidly closing the gap in CSAM reports per capita.
    """)

    # ----------------------------------------------------------------------------------
    show(f'<h2>{section}.4 Mapping CSAM Reports per Capita and Year</h2>')
    map_data = country_data.reports_per_capita.copy()
    map_data = map_data.reset_index()
    show(map_data, show_schema=True, caption='map_data')

    # The text for hover labels (without clunky hover data)
    map_data['labels'] = (
        map_data['country'].astype(str) + ':<br>' +
        map_data['reports_per_capita'].apply(lambda v: f'{v:.5f}') + ' (' +
        map_data['year'].astype(str) + ')'
    )

    fig = create_map(
        map_data,
        with_panels=False,
        with_antarctica=True,
        with_animation=True
    )
    show_map(fig)

    fig = create_map(
        map_data,
        discretization=0,
        with_panels=True,
        with_antarctica=True,
    )
    fig.write_image(f'csam-reports-per-capita.svg')
    show_map(fig)


def reports_per_platform(section: int) -> dict[str, pd.DataFrame]:
    # ----------------------------------------------------------------------------------
    disclosures = ingest_reports_per_platform(
        REPORTS_PER_PLATFORM, include_redundant=True
    )
    comparisons = compare_all_platform_reports(disclosures)

    show(f'<h1>{section}.  CSAM Reports per Platform</h1>')
    show(f'<h2>{section}.1 Ranking of Social Media Firms</h2>')

    reshaped = reshape_reports_per_platform(disclosures)
    for year in YEAR_LABELS:
        yearly = reshaped.query(f'year == {year}').copy()
        total = yearly.at['Total', 'reports']
        yearly['reports_pct'] = yearly['reports'] / total * 100
        show(
            yearly.drop(columns='year'),
            caption=f'Social Media by Reports Filed in {year}'
        )

    # ----------------------------------------------------------------------------------
    show(f'<h2>{section}.2 Transparency Data Quality per Social Medium</h2>')
    show(f"""
        Out of {len(disclosures) - 2} companies and brands, only
        {len(comparisons)} disclose the number of CSAM reports made to NCMEC.
    """)

    for platform, data in comparisons.items():
        show(data, caption=platform)

    return disclosures


_TDB_URL = (
    'https://www.thedailybeast.com/facebook-a-hotbed-of-child-sexual-abuse-material-'
    'with-203-million-reports-far-more-than-pornhub'
)


def meta_disclosures(section: int, disclosures: dict[str, pd.DataFrame]) -> None:
    # ----------------------------------------------------------------------------------
    show(f'<h1>{section}.  Meta’s Troublesome Transparency</h1>')
    show(f'<h2>{section}.1 Meta is a “<a href="{_TDB_URL}">Hotbed of CSAM</a>”</h2>')

    show("""
        Meta does not disclose the number of CSAM reports made to NCMEC, only
        CSAM pieces. That is surprising given that from 2020 onward two Meta
        employees have been serving as NCMEC directors. Furthermore, Meta makes
        no transparency disclosures for WhatsApp. In contrast, NCMEC started
        distinguishing between Facebook, Instagram, and WhatsApp in its own
        disclosures in 2021. Also see Section 2.1 above.
    """)

    meta_reports = meta.csam_reports(disclosures['NCMEC'])
    show(
        meta_reports,
        caption="Meta's Share of CSAM Reports",
        highlight_columns=['%', '% Meta'],
        margin_bottom=0
    )

    # ----------------------------------------------------------------------------------
    show(f'<h2>{section}.2 Meta Rewrites History</h2>')
    show("""
        While testing an update to my data analysis code, I discovered that Meta
        had changed seemingly arbitrary entries for previously disclosed
        transparency statistics. This section tracks the extent of these
        unacknowledged and unexplained changes by comparing Meta's CSV files
        quarter over quarter.
    """)

    meta_disclosures = meta.read_all('data')
    meta_differences = meta.diff_all(meta_disclosures)

    for p1, delta in meta_differences.items():
        p2 = p1 + 1

        show(f'<h2>Δ(Q{p2.quarter}-{p2.year} / Q{p1.quarter}-{p1.year})</h2>')
        show(meta.age_of_divergence(delta), margin_bottom=0)
        show(meta.descriptors_of_divergence(delta))

    # ----------------------------------------------------------------------------------
    show(f'<h3>{section}.2.1 Quarterly rate of divergence</h3>')
    show(meta.rate_of_divergence(meta_disclosures, meta_differences))
    show("""
        For each quarter, the table shows the number of entries in that
        quarter's data that are <em>changed</em> from the previous quarter's
        <em>total</em> number of entries. The rate of divergence simply is the
        percentage fraction of changed over total entries.
    """)

# ======================================================================================

def logger(df: pd.DataFrame, caption: None | str = None) -> None:
    if caption is not None:
        title = f'Table "{caption}"'
        print(title)
        print(f'{"-" * len(title)}\n')
        print(to_schema(df).to_string())
        print('\n')

def _main(args: Sequence[str]) -> int:
    if 'map' in args:
        just_map()
        return 0

    # Export platform data
    print('1. Exporting "data/csam-reports-per-year-country-capita"\n')
    country_data = ingest_reports_per_country('./data', logger=logger)
    country_data.reports_per_capita.reset_index().to_csv(
        'data/csam-reports-per-year-country-capita.csv',
        index=False,
        columns=[
            'year', 'iso2', 'iso3', 'country',
            'reports', 'reports_pct',
            'population', 'population_pct',
            'reports_per_capita',
            'region', 'superregion', 'continent',
            'arab_league',
        ],
    )

    print('2. Exporting "data/csam-reports-per-platform.json"')
    json_path = Path('data/csam-reports-per-platform.json')
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
