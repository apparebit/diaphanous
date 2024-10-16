from enum import StrEnum
from typing import Any, assert_never

from IPython.display import display, HTML
import numpy as np
import pandas as pd
import plotly.express as px  # type: ignore[import]
import plotly.io as pio  # type: ignore[import]


def create_map(
    frame: pd.DataFrame,
    # 0 disables discretization, a positive number results in as many quantiles,
    # a negative number results in as many equal-sized intervals as its
    # magnitude. Clever.
    discretization: int = 0,
    with_panels: bool = True,
    with_albers: bool = False,
    with_equal_earth: bool = False,
    with_animation: bool = False,  # Forced to False if with_panels
    with_antarctica: bool = True,  # Forced to True if with_albers or with_equal_earth
) -> Any:
    # -------------------- Adjust options
    if with_panels:
        with_animation = False
    if with_albers:
        with_equal_earth = False
    if with_albers or with_equal_earth:
        with_antarctica = True

    # -------------------- Discretization
    # Prepare reports_per_capita:
    if discretization == 0:
        color_column = 'reports_per_capita'
        color_range = (0, 0.042)  # Extra 0.002 to offset top tick from label
    else:
        bins = abs(int(discretization))
        color_column = 'color_data'
        color_range = (0, abs(bins))
        if discretization < 0:
            color_data = pd.cut(
                frame['reports_per_capita'],
                bins=bins,
                labels=False,
            )
        else:
            color_data = pd.qcut(
                frame['reports_per_capita'],
                q=bins,
                labels=False,
            )
        frame[color_column] = color_data

    # -------------------- Collect arguments for choropleth constructor
    kwargs = dict(
        # title='<b>CSAM Reports per Capita, Country, Year</b>',
        locations='iso3',
        color=color_column,
        color_continuous_scale=px.colors.sequential.Hot_r,  # Plasma_r,
        range_color=color_range,
        # hover_name='labels',
        # hover_data={'iso3': False, 'reports_per_capita': False, 'year': False},
        labels={'reports_per_capita': 'Reports<br>per Capita'},
    )
    if with_albers:
        kwargs |= dict(projection='albers')
    elif with_equal_earth:
        kwargs |= dict(projection='equal earth')
    if with_panels:
        kwargs |= dict(
            facet_col='year',
            facet_col_wrap=2,
        )
    if with_panels and with_albers:
        kwargs |= dict(
            facet_row_spacing=0.0001,  # must be larger than zero to have effect
            facet_col_spacing=0.005,
        )
    if with_animation:
        kwargs |= dict(
            animation_frame='year',
        )

    fig = px.choropleth(frame, **kwargs)

    # -------------------- Update overall appearance
    fig.update_traces(
        marker_line_width=0.3,  # See "countrywidth" below
        selector=dict(
            type='choropleth',
        ),
    )

    fig.update_geos(
        resolution=110,  # 50 is too much detail
        showframe=False,
        showlakes=False,
        showocean=True,
        oceancolor='#eaeaec',
        showcoastlines=True,
        coastlinewidth=0.3,
        # Also see "marker_line_width" under update_traces() above
        countrywidth=0.3,
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
            margin=dict(t=0, r=0, b=0, l=0),
            #width=640,
            #height=1100 if with_antarctica else 960,
            coloraxis_colorbar_len=0,
            # title=dict(
            #     text='<i>CSAM Reports per Capita, Country, and Year</i>',
            #     font_size=22,
            #     x=0.5,
            #     xanchor='center',
            #     xref='paper',
            #     # pad=dict(t=20, b=20),
            # ),
            # coloraxis_showscale=False,
        )
    else:
        kwargs = dict(
            margin=dict(t=40, r=0, b=0, l=0),
            # paper_bgcolor='#000', # Can be helpful when debugging size issues
        )
        if with_animation:
            kwargs |= dict(coloraxis_colorbar_len=1.1 if with_antarctica else 0.9)
        else:
            kwargs |= dict(coloraxis_colorbar_len=0.8 if with_antarctica else 0.7)

        fig.update_layout(**kwargs)

    fig.update_layout(coloraxis_showscale=False)

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
                    f'could not match {trace} with year, need another heuristic'
                )

            trace_by_year[year] = trace

        def format_annotation(a: Any) -> None:
            # For facet rows, Plotly places titles on right side, rotated by 90º.
            # Put it into lower left corner of map instead.
            year = a.text.split('=')[-1]
            domain = fig.layout[trace_by_year[year]].domain

            if with_albers:
                x = 0.53 if int(year) % 2 == 0 else 0.03
                y = domain.y[0] + 0.28
            else:
                x = 0.57 if int(year) % 2 == 0 else 0.06
                y = domain.y[0] + 0.12

            a.update(
                text=year,
                textangle=0,
                x=x,
                xanchor='left',
                y=y,
                yanchor='bottom',
                font_size=12,
            )

            #if with_antarctica and not with_equal_earth:
            a.update(
                bgcolor='#ffffff',
                borderpad=2,
            )

        fig.for_each_annotation(format_annotation)

    return fig


class DisplayMethod(StrEnum):
    # I started exploring alternative display methods when Visual Studio Code
    # remotely accessing my main machine didn't render Plotly graphs. With
    # remote access, IO_TO_HTML delivered results whereas FIG_DOT_SHOW did not.
    # However, when I tried the same on that main machine locally, the exact
    # opposite was the case, with FIG_DOT_SHOW working and IO_TO_HTML failing.
    # Fun times!

    FIG_DOT_SHOW = 'FIG_DOT_SHOW'
    IO_TO_HTML = 'IO_TO_HTML'
    SVG_FILE = 'SVG_FILE'

    def render(self, fig: Any) -> None:
        if self == self.FIG_DOT_SHOW:
            fig.show()
        elif self == self.IO_TO_HTML:
            display(HTML(pio.to_html(fig)))
        elif self == self.SVG_FILE:
            # So that each rendered figure has its own SVG, we must store the
            # counter somewhere. Using a global counter, however, is not
            # thread-safe
            count = getattr(self, '_count', 0) + 1
            setattr(self, '_count', count)
            fig.write_image(f'figure-{count}.svg')
        else:
            assert_never(self)


def show_map(fig: Any) -> None:
    DisplayMethod.FIG_DOT_SHOW.render(fig)
