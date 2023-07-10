from argparse import ArgumentParser, BooleanOptionalAction
from collections.abc import Sequence
from functools import partial
from pathlib import Path
import sys
import traceback
from typing import Any

import numpy as np
import pandas as pd
import plotly.express as px  # type: ignore[import]

from intransparent import (
    ingest_reports_per_country,
    reports_per_capita_country_year,
    REPORTS_PER_PLATFORM,
    ingest_reports_per_platform,
    encode_reports_per_platform,
    compare_all_platform_reports,
    without_populations,
    YEAR_LABELS,
    show,
)

import intransparent.meta as meta


def choropleth_plotly(frame: pd.DataFrame, with_panels: bool, with_antarctica: bool) -> Any:
    kwargs = dict(
        title='CSAM Reports per Capita and Country',
        locations='iso3',
        color='reports_per_capita',
        color_continuous_scale=px.colors.sequential.Plasma_r,
        range_color=(0, 0.042), # Extra 0.002 helps offset ticks from label
        #hover_name='labels',
        #hover_data={'iso3': False, 'reports_per_capita': False, 'year': False},
        labels={'reports_per_capita': 'Reports<br>per Capita'},
    )
    if with_panels:
        kwargs = kwargs | dict(
            facet_row='year',
            facet_row_spacing=0.005,
        )
    else:
        kwargs = kwargs | dict(
            animation_frame='year',
        )

    fig = px.choropleth(frame, **kwargs)

    # Also see "countrywidth" under update_geos() below
    fig.update_traces(
        marker_line_width=0.4,
        selector=dict(
            type='choropleth',
        ),
    )

    fig.update_geos(
        resolution=110, # 50 is too much detail
        showframe=False,
        showlakes=False,
        showocean=True,
        oceancolor='#eaeaec',
        showcoastlines=True,
        coastlinewidth=0.4,
        # Also see "marker_line_width" under update_traces() above
        countrywidth=0.4,
        landcolor='#00ffff',
    )
    if not with_antarctica:
        fig.update_geos(lataxis_range=[-58, 90])

    fig.update_layout(
        coloraxis_colorbar_tickformat='.3f',
    )

    if with_panels:
        fig.update_layout(
            margin=dict(t=30, r=10, b=10, l=10),
            width=640,
            height=1100 if with_antarctica else 960,
            coloraxis_colorbar_len=0.3,
            title=dict(
                font_size=20,
                x=0,
                xanchor='left',
                xref='paper',
                yanchor='middle',
            ),
            #coloraxis_showscale=False,
        )
    else:
        fig.update_layout(
            margin=dict(t=40, r=0, b=0, l=0),
            coloraxis_colorbar_len=1.1 if with_antarctica else 0.9
            #paper_bgcolor='#000', # Can be helpful when debugging size issues
        )

    if with_panels:
        # Heuristically determine the effective mapping from year to geo axis.
        trace_by_year = {}
        for obj in fig.data:
            # It takes just one option, facet_row, to produce four choropleths.
            # But sadly, Plotly just won't tell me what's what.
            year = None
            trace = obj.geo

            # Heuristic: When created WITH hover_name and hover_data.
            if isinstance(obj.customdata, np.ndarray):
                year = obj.customdata[0][2]

            # Heuristic: When created WITHOUT hover_name and hover_data
            elif isinstance(obj.hovertemplate, str):
                if obj.hovertemplate.startswith('year=20'):
                    year = obj.hovertemplate[5:9]

            # We really need that mapping!
            if year is None:
                raise ValueError(
                    f'could not match {trace} with year, need another heuristic')

            trace_by_year[year] = trace

        def format_annotation(a: Any) -> None:
            # For facet rows, Plotly places titles on right side, rotated by 90º.
            # Put it into lower left corner of map instead.
            year = a.text.split('=')[-1]
            domain = fig.layout[trace_by_year[year]].domain

            a.update(
                text=year,
                textangle=0,
                x=0.01,
                xanchor='left',
                y=domain.y[0] + 0.01 + (0.005 if with_antarctica else 0),
                yanchor='bottom',
                font_size=18,
            )

            if with_antarctica:
                a.update(
                    bgcolor='#ffffff',
                    borderpad=2,
                )

        fig.for_each_annotation(format_annotation)

    return fig

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
        top20 = year_data.head(20)
        show(
            top20,
            caption=f'Reports per Capita and Country {year}',
            highlight_columns='reports_per_capita',
            margin_top=2,
            margin_bottom=0,
        )

        in_arab_league = top20['arab_league'].sum()
        show(f'{in_arab_league} out of 20 countries with the most CSAM reports '
             f'per capita in {year} are members of the Arab League.<br><br>')

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

    fig = choropleth_plotly(map_data, with_panels=False, with_antarctica=False)
    fig.show()

    fig = choropleth_plotly(map_data, with_panels=True, with_antarctica=False)
    fig.write_image(f'csam-reports-per-capita.svg')
    fig.show()


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
    meta_reports = meta.fraction_of_reports(ncmec_disclosures)
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
    meta_disclosures = meta.read_all('data', '2022q2', '2023q1')
    meta_differences = meta.diff_all(meta_disclosures)

    for p1, delta in meta_differences.items():
        divergent = (
            delta
            .groupby('period')
            .size()
            .to_frame()
            .rename(columns={0: 'divergent'})
        )
        p2 = p1 + 1

        show(f'<h2>Δ(Q{p2.quarter}-{p2.year} / Q{p1.quarter}-{p1.year})</h2>')
        show(divergent, margin_bottom=0)

        show(meta.divergent_descriptors(delta))

# ======================================================================================

def create_parser() -> ArgumentParser:
    parser = ArgumentParser(__package__)
    parser.add_argument(
        "--export-platform-data",
        action="store_true",
        help="Export platform data to \"data/csam-reports-per-platform.json\"",
    )
    format = parser.add_argument_group("output format")
    # format.add_argument(
    #     "--latex", action="store_true", help="emit LaTeX instead of text"
    # )
    format.add_argument(
        "--color", action=BooleanOptionalAction, help="force (no) color in output"
    )
    return parser


def _main(args: Sequence[str]) -> int:
    # Parse command line arguments
    parser = create_parser()
    options = parser.parse_args(args[1:])

    # Export platform data
    if options.export_platform_data:
        json_path = Path('data/csam-reports-per-platform.json')
        tmp_path = json_path.with_suffix('.tmp.json')
        with open(tmp_path, mode='w', encoding='utf') as file:
            file.write('\n'.join(encode_reports_per_platform(REPORTS_PER_PLATFORM)))
        tmp_path.replace(json_path)

    # Analyze dataset
    reports_per_country(section=1)
    disclosures = reports_per_platform(section=2)
    meta_disclosures(section=3, disclosures=disclosures)
    return 0


def main(args: Sequence[str]) -> int:
    try:
        return _main(args)
    except Exception as x:
        traceback.print_exc(file=sys.stderr)
        return 1
