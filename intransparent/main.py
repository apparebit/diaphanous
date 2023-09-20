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
    encode_reports_per_platform,
    compare_all_platform_reports,
    without_populations,
    YEAR_LABELS,
    show,
    to_schema,
)

import intransparent.meta as meta

# ======================================================================================

def reports_per_country(section: int) -> None:
    show(f'<h1>{section}. CSAM Reports per Country</h1>')
    show(f'<h2>{section}.1 The Raw Data</h2>')

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
        top = year_data.head(30 if year == '2022' else 21)
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
        <p>Both Libya and the United Arab Emirates each rank first for two of
        four years. The two countries differ significantly in wealth and
        political stability, suggesting that neither is a primary causal factor.
        They both also are members of the Arab League. In fact, between 9 and 12
        countries amongst each year's top 20 are members of the Arab League.
        That's far too many to be some random effect and suggests shared
        cultural factors as a primary cause. Such skew could arise, for example,
        if a large number of people in the region viewed some borderline
        material as acceptable, whereas US companies and law do not.</p>

        <p>Irrespective of cause(s),</p>

        <ul>
            <li>the number of Arab League countries in the top 20 is shrinking;

            <li>the number of reports per capita for Arab League countries is
            shrinking;

            <li>the number of reports per capita for other countries is clearly
            growing.
        </ul>

        <p>Notably, that third category clearly includes the United States. If
        these trends persist for a few more years, Arab League countries won't
        stand out anymore because most other countries saw huge increases in
        reports per capita.</p>
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

    fig = create_map(map_data, with_panels=False, with_antarctica=True, with_animation=True)
    show_map(fig)

    fig = create_map(map_data, with_panels=True, with_antarctica=True)
    fig.write_image(f'csam-reports-per-capita.svg')
    show_map(fig)


def reports_per_platform(section: int) -> dict[str, pd.DataFrame]:
    # ----------------------------------------------------------------------------------
    show(f'<h1>{section}. CSAM Reports per Platform</h1>')
    disclosures = ingest_reports_per_platform(
        REPORTS_PER_PLATFORM, include_redundant=True)
    comparisons = compare_all_platform_reports(disclosures)

    show(f"""
        Out of {len(disclosures) - 2} companies and brands, only
        {len(comparisons)} disclose the number of CSAM reports made to NCMEC.
        Since NCMEC also discloses the number CSAM reports made by each
        platform, the availability of the same metric from sender and receiver
        enables a direct comparison. Alas, the results aren’t exactly
        encouraging...
        """)

    for platform, data in comparisons.items():
        show(data, caption=platform)

    return disclosures


def meta_disclosures(section: int, disclosures: dict[str, pd.DataFrame]) -> None:
    # ----------------------------------------------------------------------------------
    show(f'<h1>{section}. Meta’s Troublesome Transparency</h1>')
    show(f'<h2>{section}.1 Meta is a “Hotbed of CSAM”</h2>')

    ncmec_disclosures = disclosures['NCMEC']
    show(ncmec_disclosures, show_schema=True, caption='NCMEC')
    meta_reports = meta.csam_reports(ncmec_disclosures)
    show(meta_reports, caption="Meta's Share of CSAM Reports", margin_bottom=0)

    show("""
        <p>Meta does not disclose the number of CSAM reports made to NCMEC, only
        CSAM pieces and, like its other transparency disclosures, only for
        Facebook and Instagram. At the same time, Meta is responsible for the
        vast majority of all CSAM reports. With Meta employees serving as NCMEC
        trustees, Meta must be well aware of its status as most prolific filer
        of reports, NCMEC only disclosing report counts, and NCMEC disclosing
        report counts for WhatsApp too. Still, it has not adjusted its reporting
        practices.</p>

        <p>While Meta makes no disclosures about WhatsApp, NCMEC started
        breaking down its counts of reports received by Facebook, Instagram,
        <em>and</em> WhatsApp. While WhatsApp consistently has the smallest
        count of Meta's three social networks, that’s still over 1 million CSAM
        reports per year.</p>

        <p>As the above table shows, the <strong>total number of CSAM reports to
        NCMEC almost doubled from less than 17 million reports in 2019 to less
        than 32 million reports in 2022</strong>. That clearly is the wrong
        trend.</p>
        """)

    # ----------------------------------------------------------------------------------
    show(f'<h2>{section}.2 Meta Rewrites History</h2>')
    show("""
        It gets worse: When I ported a spreadsheet with initial analysis to
        Python with Pandas, some results turned out different. Careful review of
        all formulae and code ended with the discovery that Meta has been
        changing historical datapoints over several quarters. The counts shown
        below may be undercounts because Meta also is the only social media firm
        that rounds transparency data. That may hide small-ish updates to
        historical values.
        """)
    meta_disclosures = meta.read_all('data')
    meta_differences = meta.diff_all(meta_disclosures)

    for p1, delta in meta_differences.items():
        p2 = p1 + 1

        show(f'<h2>Δ(Q{p2.quarter}-{p2.year} / Q{p1.quarter}-{p1.year})</h2>')
        show(meta.age_of_divergence(delta), margin_bottom=0)

        show(meta.descriptors_of_divergence(delta))

    show(f'<h2>Quarterly rate of divergence</h2>')
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
