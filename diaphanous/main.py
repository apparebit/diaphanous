from collections.abc import Sequence
import math
from pathlib import Path
import sys
import traceback

import pandas as pd

from diaphanous import (
    ingest_reports_per_country,
    reports_per_country_year,
    create_map,
    show_map,
    REPORTS_PER_PLATFORM,
    encode_reports_per_platform,
    YEAR_LABELS,
    show,
    to_schema,
    fetch_populations,
)

from diaphanous.tabulate import tabulate

# ======================================================================================


def just_map() -> None:
    country_data = ingest_reports_per_country('./data')
    map_data = country_data.reports_per_country.reset_index()
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


def reports_per_country_stats() -> tuple[pd.DataFrame, pd.DataFrame]:
    # ----------------------------------------------------------------------------------
    country_data = ingest_reports_per_country('../data')

    # Dropping N/A gets rid of 2019 because reports_per_accounts aren't
    # available for that year.
    frame = country_data.reports_per_country
    frame = frame[["reports_per_capita", "reports_per_accounts"]].dropna()

    from diaphanous.show import show
    show(frame, show_schema=True)

    f = frame.reset_index()
    f.loc[(f["year"] == "2024") & (f["iso3"] == "TKL")] = 0
    stats = f.agg({
        'reports_per_capita': ['min', 'median', 'mean', 'std', 'skew', 'max'],
        'reports_per_accounts': ['min', 'median', 'mean', 'std', 'skew', 'max'],
    })
    stats.insert(
        1,
        "multiplier",
        stats["reports_per_accounts"] / stats["reports_per_capita"],
    )

    show(f'<h2>Reports per Capita and Accounts Statistics</h2>')
    show(stats, caption='Range of Reports per Capita/Accounts')
    return stats, frame


def reports_per_country(
    section: int = -1, capita_mean: float = math.nan, accounts_mean: float = math.nan
) -> None:
    # ----------------------------------------------------------------------------------

    def secnum(subsection: int) -> str:
        return '' if section == -1 else f'{section}.{subsection} '

    country_data = ingest_reports_per_country('../data')

    show(f'<h2>{secnum(1)}Regions Ranked by CSAM Reports</h2>')
    most_reports = (
        country_data.reports_per_country.groupby(['year', 'region'], observed=False)
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
    show(f'<h2>{secnum(2)}Countries Ranked by CSAM Reports per Capita</h2>')
    rpc_range = country_data.reports_per_country.agg(
        {'reports_per_capita': ['min', 'max']}
    )
    show(rpc_range, caption='Range of Reports per Capita', margin_bottom=0)

    arab_league = {}

    for year, year_data in reports_per_country_year(country_data):
        rank = year_data.index[year_data['iso3'] == '\u262a'][0]
        top_size = 30 + (1 if rank <= 30 else 0)

        top = year_data.head(top_size)
        show(
            top,
            caption=f'Reports per Capita and Country {year}',
            highlight_columns='reports_per_capita',
            highlight_rows=rank,
            margin_top=2,
            margin_bottom=0,
        )

        deu_rank = year_data[year_data['iso3'] == 'DEU']
        usa_rank = year_data[year_data['iso3'] == 'USA']
        show(
            f"""
            <p>Germany has a rate of
            {deu_rank['reports_per_capita'].iloc[0] * 1000:.1f}
            reports per 1,000 capita, ranking {deu_rank.index[0]}.

            <p>The US has a rate of
            {usa_rank['reports_per_capita'].iloc[0] * 1000:.1f}
            reports per 1,000 capita, ranking {usa_rank.index[0]}.
            """
        )

        in_arab_league = top['arab_league'].sum()
        if year != "2019":
            arab_league.setdefault("year", []).append(year)
            arab_league.setdefault("capita", []).append(in_arab_league)

        if year == '2022':
            assert top.tail(10)['arab_league'].sum() == 0

        show(
            f"""
            {in_arab_league} out of 30 countries with the most CSAM reports per
            capita in {year} are members of the Arab League. If the Arab League
            were a country, its rank would rank {rank}.<br><br>
            """
        )

        show(
            f"""
            {len(year_data[year_data["reports_per_capita"] <= capita_mean])} out of
            {len(year_data)} countries
            ({len(year_data[year_data["reports_per_capita"] <= capita_mean])
               / len(year_data) * 100:.1f}%)
            have a rate that is
            at most {capita_mean * 1000:.1f}
            reports per 1,000 capita.<br>

            {len(year_data[year_data["reports_per_capita"] <= 0.008])} out of
            {len(year_data)} countries
            ({len(year_data[year_data["reports_per_capita"] <= 0.008])
               / len(year_data) * 100:.1f}%)
            have a rate that is at most 8
            reports per 1,000 capita.<br>

            {len(year_data[year_data["reports_per_capita"] <= 0.016])} out of
            {len(year_data)} countries
            ({len(year_data[year_data["reports_per_capita"] <= 0.016])
               / len(year_data) * 100:.1f}%)
            have a rate that is at most 16
            reports per 1,000 capita.
            """
        )

        if year != YEAR_LABELS[-1]:
            show('<hr>')

    # ----------------------------------------------------------------------------------
    show(f'<h2>{secnum(3)}Countries Ranked by CSAM Reports per Social Accounts</h2>')
    rpc_range = country_data.reports_per_country.agg(
        {'reports_per_accounts': ['min', 'max']}
    )
    show(rpc_range, caption='Range of Reports per Accounts', margin_bottom=0)

    for year, year_data in reports_per_country_year(
        country_data, column='reports_per_accounts'
    ):
        if year == "2019":
            continue

        rpa = year_data['reports_per_accounts']
        year_data['pct_rate_diff'] = (rpa - rpa.shift(1)) / rpa

        top = year_data.head(30)
        # rank = top.index[top['iso3'] == '\u262a'][0]
        show(
            top,
            caption=f'Reports per Social Media Accounts and Country {year}',
            highlight_columns='reports_per_accounts',
            # highlight_rows=rank,
            margin_top=2,
            margin_bottom=0,
        )

        deu_rank = year_data[year_data['iso3'] == 'DEU']
        usa_rank = year_data[year_data['iso3'] == 'USA']
        show(
            f"""
            <p>Germany has a rate of
            {deu_rank['reports_per_accounts'].iloc[0] * 1000:.1f}
            reports per 1,000 social media accounts, ranking {deu_rank.index[0]}.

            <p>The US has a rate of
            {usa_rank['reports_per_accounts'].iloc[0] * 1000:.1f}
            reports per 1,000 social media accounts, ranking {usa_rank.index[0]}.
            """
        )

        in_arab_league = top['arab_league'].sum()
        arab_league.setdefault("accounts", []).append(in_arab_league)
        index = arab_league["year"].index(year)
        show(
            f"""
            {in_arab_league} out of 30 countries with the most CSAM reports per
            accounts in {year} compared to {arab_league["capita"][index]} for reports
            per capita are members of the Arab League.<br><br>
            """
        )

        show(
            f"""
            {len(year_data[year_data["reports_per_accounts"] <= accounts_mean])} out of
            {len(year_data)} countries
            ({len(year_data[year_data["reports_per_accounts"] <= accounts_mean])
              / len(year_data)*100:.1f}%)
            have a rate that is
            at most {accounts_mean * 1000:.1f}
            reports per 1,000 social media accounts.<br>

            {len(year_data[year_data["reports_per_accounts"] <= 0.008])} out of
            {len(year_data)} countries
            ({len(year_data[year_data["reports_per_accounts"] <= 0.008])
              / len(year_data)*100:.1f}%)
            have a rate that is at most 8
            reports per 1,000 social media accounts.<br>

            {len(year_data[year_data["reports_per_accounts"] <= 0.016])} out of
            {len(year_data)} countries
            ({len(year_data[year_data["reports_per_accounts"] <= 0.016])
              / len(year_data)*100:.1f}%)
            have a rate that is at most 16
            reports per 1,000 social media accounts.
            """
        )

        if year != YEAR_LABELS[-1]:
            show('<hr>')

    show(pd.DataFrame(arab_league).describe())

    # ----------------------------------------------------------------------------------
    show(f'<h2>{secnum(4)}Mapping CSAM Reports per Capita and Year</h2>')
    map_data = country_data.reports_per_country.copy()
    map_data = map_data.reset_index()
    show(map_data, show_schema=True, caption='map_data')

    # Exclude extreme outlier for 2024
    map_data = map_data[(map_data['iso3'] != 'TKL') | (map_data['year'] != "2024")]

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
        map_data,
        with_panels=False,
        with_antarctica=True,
        with_animation=True,
        with_equal_earth=True,
    )
    show_map(fig)

    fig = create_map(
        map_data,
        discretization=0,
        with_legend=True,
        with_panels=True,
        with_antarctica=True,
        with_equal_earth=True,
    )
    show_map(fig)
    fig.write_image(f'../figure/capita-countries.svg')

    for year in YEAR_LABELS:
        show(f"<h2>{year}</h2>")
        fig = create_map(
            map_data[map_data["year"] == year],
            discretization=0,
            with_legend=True,
            with_antarctica=True,
            with_equal_earth=True,
        )
        show_map(fig)
        fig.write_image(f'../figure/capita-countries-{year}.svg')

    # ----------------------------------------------------------------------------------
    show(f'<h2>{secnum(5)}Mapping CSAM Reports per Social Accounts and Year</h2>')
    map_data = country_data.reports_per_country.copy()
    map_data = map_data.reset_index()
    show(map_data, show_schema=True, caption='map_data')

    # The text for hover labels (without clunky hover data)
    map_data['labels'] = (
        map_data['country'].astype(str)
        + ':<br>'
        + map_data['reports_per_accounts'].apply(
            lambda v: f'{v:.5f}' if not pd.isnull(v) else "NA"
        ) + ' ('
        + map_data['year'].astype(str)
        + ')'
    )

    fig = create_map(
        map_data,
        with_panels=False,
        with_antarctica=True,
        with_animation=True,
        with_accounts=True,
        with_equal_earth=True,
    )
    show_map(fig)

    fig = create_map(
        map_data,
        discretization=0,
        with_legend=True,
        with_panels=True,
        with_antarctica=True,
        with_accounts=True,
        with_equal_earth=True,
    )
    show_map(fig)
    fig.write_image(f'../figure/account-countries.svg')

    for year in YEAR_LABELS[1:]:
        show(f"<h2>{year}</h2>")
        fig = create_map(
            map_data[map_data["year"] == year],
            discretization=0,
            with_legend=True,
            with_antarctica=True,
            with_equal_earth=True,
            with_accounts=True,
            with_range=120 if year == "2021" else None
        )
        show_map(fig)
        fig.write_image(f'../figure/account-countries-{year}.svg')


# ======================================================================================


def logger(frame: pd.DataFrame, caption: None | str = None) -> None:
    if caption is not None:
        title = f'Table "{caption}"'
        print(title)
        print(f'{"-" * len(title)}\n')
        print(to_schema(frame).to_string())
        print('\n')


def _main(args: Sequence[str]) -> int:
    if "--fetch-populations" in args:
        fetch_populations("data/populations.csv")

    # Export platform data
    print('1. Exporting "data/ocse-reports-per-year-country-capita"\n')
    country_data = ingest_reports_per_country('./data', logger=logger)
    country_data.reports_per_country.reset_index().to_csv(
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
            'accounts_per_capita',
            'reports_per_accounts',
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

    print('3. Exporing "data/ocse-reports-per-platform.csv"')
    tabulate().write_csv("data/ocse-reports-per-platform.csv")

    print('Done!')
    return 0


def main(args: Sequence[str]) -> int:
    try:
        return _main(args)
    except Exception as x:
        traceback.print_exc(file=sys.stderr)
        return 1
