from typing import NamedTuple

import pandas as pd


class ReportContents(NamedTuple):
    pieces: pd.DataFrame
    violations: pd.DataFrame
    relationships: pd.DataFrame


def report_contents(data: pd.DataFrame) -> ReportContents:
    totals = (
        data.query('category == "reports" and entry == "reports"')
        .drop(columns=['category', 'entry'])
        .set_index('year')['quantity']
    )

    # • • • • • • • • • • • • • • • • • • • • • • • • • • • • • • • • • • • • • • • • •

    pieces = (
        data.query('category == "attachments"')
        .drop(columns='category')
        .pivot(index='year', columns='entry', values='quantity')
    )

    pieces['reports'] = totals
    pieces['pieces'] = pieces['photos'] + pieces['videos']
    pieces['unique pieces'] = pieces['unique photos'] + pieces['unique videos']
    pieces['similar pieces'] = pieces['similar photos'] + pieces['similar videos']
    pieces['π(⏵)'] = pieces['pieces'] / totals
    pieces['π(⏴)'] = pieces['pieces'] / pieces['unique pieces']
    pieces['π(⏴⏴)'] = pieces['pieces'] / pieces['similar pieces']
    pieces = pieces[
        [
            'reports',
            'π(⏵)',
            'pieces',
            'π(⏴)',
            'unique pieces',
            'π(⏴⏴)',
            'similar pieces',
        ]
    ]

    # • • • • • • • • • • • • • • • • • • • • • • • • • • • • • • • • • • • • • • • • •

    prep = (
        data.query('category == "kind of exploitation"')
        .drop(columns='category')
        .pivot(index='entry', columns='year', values='quantity')
    )
    assert totals.equals(prep.sum())

    violations = pd.DataFrame(index=prep.index)
    for year, entries in prep.items():
        violations[year] = entries
        violations[f'{year} %'] = entries / totals[year] * 100

    # • • • • • • • • • • • • • • • • • • • • • • • • • • • • • • • • • • • • • • • • •

    rel = (
        pd.read_csv('./data/csam-pieces-by-relationship-to-victim.csv', thousands=',')
        .drop(columns=['2020 Pieces', '2021 Pieces', '2022 Pieces'])
        .rename(
            columns={
                '2020 Unique Pieces': '2020',
                '2021 Unique Pieces': '2021',
                '2022 Unique Pieces': '2022',
            }
        )
        .set_index('Relationship')
    )

    piece_totals = rel.sum()

    relationships = pd.DataFrame(index=rel.index)
    for year, entries in rel.items():
        relationships[year] = entries
        relationships[f'{year} %'] = entries / piece_totals[year] * 100

    relationships.loc[
        ['Online Enticement/Self & Offender Produced', 'Trafficking', 'Stranger'],
        ['Distance'],
    ] = 'Remote'
    relationships.loc[
        [
            'Babysitter, Mentor, Coach, Teacher',
            'Neighbor/Family friend',
            'Photographer',
        ],
        ['Distance'],
    ] = 'Socially Close'
    relationships.loc[relationships['Distance'].isnull(), 'Distance'] = 'Family'

    # • • • • • • • • • • • • • • • • • • • • • • • • • • • • • • • • • • • • • • • • •

    return ReportContents(pieces, violations, relationships)
