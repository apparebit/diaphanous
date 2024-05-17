from pathlib import Path
from typing import Any, Iterator, NamedTuple

import numpy as np
import pandas as pd
import geopandas as geo  # type: ignore

from .frame_logger import FrameLogger, silent_logger


YEAR_LABELS = tuple(str(year) for year in range(2019, 2024))

REPORT_TOTALS = {
    '2019': 16_987_361,
    '2020': 21_751_085,
    '2021': 29_397_681,
    '2022': 32_059_029,
    '2023': 36_210_368,
}

_PROBLEMATIC_GEOMETRIES = set(['France', 'Kosovo', 'N. Cyprus', 'Norway', 'Somaliland'])


def read_reports(path: str | Path) -> pd.DataFrame:
    # Read data
    reports = pd.read_csv(path, thousands=',').drop(columns='country')

    # Validate data
    actual = reports.shape[0]
    if actual != 252:
        raise AssertionError(f'{actual:,d} instead of 250 rows in "{path}"')
    actual = reports['iso3'].isna().sum()
    if actual != 1:
        raise AssertionError(
            f'{actual:,d} instead of 1 row without ISO Alpha-3 code in "{path}"'
        )

    for year, expected_nulls in zip(YEAR_LABELS, (10, 7, 7, 5, 8)):
        actual_nulls = reports[year].isna().sum()
        if actual_nulls != expected_nulls:
            raise AssertionError(
                f'{year}: {actual_nulls:,d} instead of {expected_nulls:,d} countries '
                'with no reports'
            )

    # Clean up and reorganize data
    reports = (
        reports
        # NCMEC includes a line for reports without country in each disclosure
        # but adds them to USA's tally for analysis. We do the same.
        .assign(iso3=lambda df: df['iso3'].fillna('USA'))
        .fillna(0)
        .melt(
            id_vars=['iso3'],
            value_vars=YEAR_LABELS,
            var_name='year',
            value_name='reports',
        )
        .astype({'iso3': 'category', 'year': 'category', 'reports': 'int'})
        .groupby(['iso3', 'year'])
        .sum()
    )

    # 252 rows - 1 extra row formerly without ISO3 then USA - 1 extra row GUF
    actual = reports.index.get_level_values('iso3').nunique()
    if actual != 250:
        raise AssertionError(
            f'{actual:,d} instead of 250 ISO Alpha-3 codes with reports'
        )

    # Sum up reports.
    total_yearly_reports = reports.groupby(level='year')['reports'].sum()
    reports['reports_pct'] = reports['reports'] / total_yearly_reports * 100

    # Validate totals.
    for year, expected_total in REPORT_TOTALS.items():
        if year not in total_yearly_reports.index:
            continue
        actual_total = total_yearly_reports[year]
        if actual_total != expected_total:
            raise AssertionError(
                f'{year}: {actual_total:,d} instead of {expected_total:,d}'
                'total reports'
            )

    # Add column with percentage fractions.
    actual_pct = reports.groupby(level='year')['reports_pct'].sum()
    expected_pct = pd.Series([100.0] * len(YEAR_LABELS), index=YEAR_LABELS)
    if not actual_pct.equals(expected_pct):
        raise AssertionError(f'{actual_pct} instead of {expected_pct} report fractions')

    return reports


def read_populations(path: str | Path) -> pd.DataFrame:
    populations = (
        pd.read_csv(
            path,
            sep="|",
            usecols=['Iso3', 'VariantId', 'TimeLabel', 'SexId', 'Value'],
            dtype={'Iso3': 'category', 'TimeLabel': 'category', 'Value': 'int'},
        )
        .rename(columns={'Iso3': 'iso3', 'TimeLabel': 'year', 'Value': 'population'})
        .pipe(lambda df: df[(df['VariantId'] == 4) & (df['SexId'] == 3)])
        .drop(columns=['VariantId', 'SexId'])
        .set_index(['iso3', 'year'])
    )

    row_no = populations.shape[0]
    if row_no != 1_180:
        raise AssertionError(
            f'{row_no:,d} instead of 1,180 rows with population counts'
        )
    country_no = populations.index.get_level_values('iso3').nunique()
    if country_no != 236:
        raise AssertionError(
            f'{country_no:,d} instead of 236 countries with population counts'
        )

    # Compute total population per year and add column with percentage fraction.
    total_yearly_populations = populations.groupby(level='year')['population'].sum()
    populations['population_pct'] = (
        populations['population'] / total_yearly_populations * 100
    )

    actual_pct = populations.groupby(level='year')['population_pct'].sum()
    expected_pct = pd.Series([100.0] * len(YEAR_LABELS), index=YEAR_LABELS)
    if not actual_pct.equals(expected_pct):
        raise AssertionError(
            f'{actual_pct} instead of {expected_pct} population fractions'
        )

    return populations


def read_online(path: str | Path) -> pd.DataFrame:
    online = (
        pd.
        read_csv(
            path,
            usecols=['iso3', 'year', 'online'],
            dtype={'iso3': 'category', 'year': 'category', 'online': 'int'},
        )
        .set_index(['iso3', 'year'])
    )

    total_yearly_online = online.groupby(level='year')['online'].sum()
    online['online_pct'] = online['online'] / total_yearly_online * 100

    if len(online) != 6_406:
        raise AssertionError(
            f'{len(online)} instead of 6,406 rows for online populations'
        )

    return online


def read_countries(path: str | Path) -> pd.DataFrame:
    countries = pd.read_csv(path, index_col='iso3', dtype='category', na_filter=False)
    if countries.at['NAM', 'iso2'] != 'NA':
        raise AssertionError("Namibia's ISO2 code (NA) is *not* null")
    return countries


def read_regions(path: str | Path) -> pd.DataFrame:
    regions = (
        (rs := pd.read_csv(path))
        .merge(
            rs,
            how='left',
            left_on='superregion',
            right_on='region',
            suffixes=('', '2'),
        )
        .assign(continent=lambda df: df['superregion2'].fillna(df['superregion']))
        .drop(columns=['superregion2', 'region2'])
        .astype('category')
    )
    return regions


def read_arab_league(path: str | Path) -> pd.DataFrame:
    arab_league = pd.read_csv(path).drop(columns=['country']).astype('category')
    assert arab_league.shape[0] == 22
    return arab_league


def read_geometries(path: str | Path) -> pd.DataFrame:
    # https://github.com/geopandas/geopandas/blob/04c2dee547777d9e87f9df4c85cc372a03b29f93/geopandas/datasets/naturalearth_creation.py#L87
    geometries = (
        geo.read_file(path)
        .rename(columns={'ISO_A3': 'iso3', 'NAME': 'name'})
        .loc[:, ['iso3', 'name', 'geometry']]
    )

    # Check that countries with missing ISO Alpha-3 codes are the expected five.
    # North Cyprus and Somaliland are not internationally recognized and we
    # treat them as part of Cyprus and Somalia, respectively.
    missing_iso3 = set(geometries.query('iso3 == "-99"')['name'].to_list())
    if missing_iso3 != _PROBLEMATIC_GEOMETRIES:
        raise AssertionError(
            f'geometries for {missing_iso3} instead of {_PROBLEMATIC_GEOMETRIES} '
            'without ISO Alpha-3 code'
        )

    country = geometries['name']
    geometries.loc[country == 'France', 'iso3'] = 'FRA'
    geometries.loc[country == 'Kosovo', 'iso3'] = 'XKX'
    geometries.loc[country == 'N. Cyprus', 'iso3'] = 'CYP'
    geometries.loc[country == 'Norway', 'iso3'] = 'NOR'
    geometries.loc[country == 'Somaliland', 'iso3'] = 'SOM'

    geometries = (
        geometries.drop(columns=['name']).astype({'iso3': 'category'}).set_index('iso3')
    )

    # There are two fewer countries thanks to N. Cyprus and Somaliland.
    actual = geometries.shape[0]
    if actual != 177:
        raise AssertionError(f'{actual:,d} instead of 177 geometries')
    actual = geometries.index.nunique()
    if actual != 175:
        raise AssertionError(f'{actual:,d} instead of 175 countries with geometries')

    geometries = geometries.dissolve(by='iso3')
    actual = geometries.shape[0]
    if actual != 175:
        raise AssertionError(f'{actual:,d} instead of 175 geometries after dissolution')

    return geometries


def without_populations(
    reports: pd.DataFrame, populations: pd.DataFrame, countries: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    countries_without = (
        reports.index
        .get_level_values('iso3')
        .difference(populations.index.get_level_values('iso3'))
        .to_frame()
        .drop(columns='iso3')
        .merge(countries, how='left', on='iso3')
        .drop(columns='iso2')
    )

    reports_without = (
        reports[reports.index.get_level_values('iso3').isin(countries_without.index)]
        .groupby('year')
        .sum()
    )

    expected = [28, 97, 243, 117, 58]
    actual = reports_without['reports']
    if not np.array_equal(actual, expected):
        raise AssertionError(
            'reports for countries without population'
            f' {",".join(str(n) for n in actual)} does not match expected '
            f' {",".join(str(n) for n in expected)}'
        )

    return countries_without, reports_without


def merge_reports_per_country(
    reports: pd.DataFrame,
    populations: pd.DataFrame,
    online: pd.DataFrame,
    countries: pd.DataFrame,
    regions: pd.DataFrame,
    arab_league: pd.DataFrame,
) -> pd.DataFrame:
    df = (
        reports.merge(populations, how='inner', left_index=True, right_index=True)
        # index is (iso3, year)
        .merge(online, how='left', on=['iso3', 'year'])
        # index still is (iso3, year)
        .reset_index(level='year')
        # index is iso3
        .merge(countries, how='left', on='iso3')
        .reset_index()
        # index is row number
        .merge(regions, how='left', on='region')
        .astype({'region': 'category'})  # Restore category lost on merge
    )
    df.insert(4, 'reports_per_capita', df['reports'] / df['population'])
    df['arab_league'] = df['iso3'].isin(arab_league['iso3'])
    df = df.set_index(['iso3', 'year'])

    expected_rows = populations.shape[0]
    actual_rows = df.shape[0]
    if actual_rows != expected_rows:
        raise AssertionError(
            f'{actual_rows:,d} instead of {expected_rows:,d} rows in merged table'
        )

    return df


def summarize_arab_league(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []

    for year in YEAR_LABELS:
        year_in_league = frame.query(f'year == "{year}" and arab_league == True')
        reports = year_in_league['reports'].sum()
        population = year_in_league['population'].sum()
        rows.append(
            {
                'iso3': '\u262A',
                'year': year,
                'reports': reports,
                'reports_pct': year_in_league['reports_pct'].sum(),
                'reports_per_capita': reports / population,
                'population': population,
                'population_pct': year_in_league['population_pct'].sum(),
                'country': 'Arab League',
                'iso2': '\u262A',
                'region': None,
                'superregion': None,
                'continent': None,
                'arab_league': False,  # Only True for members, not a synthetic summary
            }
        )

    addendum = pd.DataFrame(rows).set_index(['iso3', 'year'])
    return pd.concat([frame, addendum])


class ReportsPerCountry(NamedTuple):
    reports_per_capita: pd.DataFrame
    reports: pd.DataFrame
    populations: pd.DataFrame
    online: pd.DataFrame
    countries: pd.DataFrame
    regions: pd.DataFrame
    arab_league: pd.DataFrame
    geometries: None | pd.DataFrame


def ingest_reports_per_country(
    path: str | Path,
    *,
    logger: None | FrameLogger = None,
    load_geometries: bool = False,
) -> ReportsPerCountry:
    path = Path(path)

    if logger is None:
        logger = silent_logger

    reports = read_reports(path / 'ocse-reports-per-country.csv')
    logger(reports, caption='reports')

    populations = read_populations(path / 'populations.csv')
    logger(populations, caption='populations')

    online = read_online(path / 'internet-users.csv')
    logger(online, caption='online')

    countries = read_countries(path / 'countries.csv')
    logger(countries, caption='countries')

    regions = read_regions(path / 'regions.csv')
    logger(regions, caption='regions')

    arab_league = read_arab_league(path / 'arab-league.csv')
    logger(arab_league, caption='arab_league')

    geometries = None
    if load_geometries:
        geometries = read_geometries(
            path / 'naturalearth/ne_110m_admin_0_countries.shp'
        )
        logger(geometries, caption='geometries')

    reports_per_capita = merge_reports_per_country(
        reports, populations, online, countries, regions, arab_league
    )
    logger(reports_per_capita, caption='reports per capita')

    reports_per_capita = summarize_arab_league(reports_per_capita)

    return ReportsPerCountry(
        reports_per_capita,
        reports,
        populations,
        online,
        countries,
        regions,
        arab_league,
        geometries,
    )


def reports_per_capita_country_year(
    reports_per_country: ReportsPerCountry,
) -> Iterator[Any]:
    """
    Create an iterator over the year and reports per capita per country, with
    the entries sorted in descending order by reports per capita. The index is a
    country's rank.
    """
    sorted_and_grouped = (
        reports_per_country.reports_per_capita.drop(
            columns=['region', 'superregion', 'continent']
        )
        .sort_values('reports_per_capita', ascending=False)
        .groupby('year')
    )

    for year, group in sorted_and_grouped:
        group = group.reset_index()
        group.index = group.index + 1
        group.index.name = 'rank'

        yield year, group
