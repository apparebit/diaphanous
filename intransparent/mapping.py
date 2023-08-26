from typing import Any
import numpy as np
import pandas as pd
import plotly.express as px  # type: ignore[import]


def create_map(
    frame: pd.DataFrame,
    with_panels: bool = True,
    with_equal_earth: bool = True,
    with_animation: bool = False,  # Forced to False if with_panels
    with_antarctica: bool = True,  # Forced to True if with_equal_earth
) -> Any:
    # -------------------- Adjust options
    if with_panels:
        with_animation = False
    if with_equal_earth:
        with_antarctica = True

    # -------------------- Collect arguments for choropleth constructor
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
    if with_equal_earth:
        kwargs |= dict(
            projection='equal earth'
        )
    if with_panels:
        kwargs |= dict(
            facet_row='year',
            facet_row_spacing=0.005,
        )
    if with_animation:
        kwargs |= dict(
            animation_frame='year',
        )

    fig = px.choropleth(frame, **kwargs)

    # -------------------- Update overall appearance
    fig.update_traces(
        marker_line_width=0.4, # See "countrywidth" below
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
        # Color of countries that have no data
        landcolor='#c5c5c6',
    )

    # -------------------- Maybe crop Antarctica
    if not with_antarctica:
        fig.update_geos(lataxis_range=[-58, 90])

    # -------------------- Adjust display of legend
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
        kwargs = dict(
            margin=dict(t=40, r=0, b=0, l=0),
            #paper_bgcolor='#000', # Can be helpful when debugging size issues
        )
        if with_animation:
            kwargs |= dict(
                coloraxis_colorbar_len=1.1 if with_antarctica else 0.9
            )
        else:
            kwargs |= dict(
                coloraxis_colorbar_len=0.8 if with_antarctica else 0.7
            )

        fig.update_layout(**kwargs)

    # -------------------- Add year label to each panel
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

            y = domain.y[0] + 0.01
            if with_antarctica and not with_equal_earth:
                y += 0.005

            a.update(
                text=year,
                textangle=0,
                x=0.01,
                xanchor='left',
                y=y,
                yanchor='bottom',
                font_size=18,
            )

            if with_antarctica and not with_equal_earth:
                a.update(
                    bgcolor='#ffffff',
                    borderpad=2,
                )

        fig.for_each_annotation(format_annotation)

    return fig

