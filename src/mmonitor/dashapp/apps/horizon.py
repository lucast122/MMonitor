from typing import Tuple, List, Any, Dict

import plotly.graph_objects as go
import numpy as np
import pandas as pd
from math import ceil, floor
from dash import dcc, html
from plotly.graph_objs import Figure

from mmonitor.dashapp.app import app
from mmonitor.dashapp.base_app import BaseApp
from mmonitor.database.mmonitor_db import MMonitorDBInterface


class Horizon(BaseApp):

    def __init__(self, sql: MMonitorDBInterface):
        super().__init__(sql)
        self._taxonomies = self._sql.get_unique_taxonomies()
        self._init_layout()
        self._init_callbacks()

    def _init_layout(self) -> None:
        graphs = [
            dcc.Graph(figure=fig)
            for fig in self._generate_figures()
        ]
        self.layout = html.Div(graphs)

    def _init_callbacks(self) -> None:
        pass

    def _generate_figures(self) -> list[Figure]:

        figs = []

        for taxonomy in self._taxonomies:

            # fetch data for each taxonomy in order to
            # avoid loading entire database at once
            df = self._sql.query_to_dataframe(
                f"SELECT abundance, sample_id FROM mmonitor WHERE taxonomy == '{taxonomy}'"
            )
            df = df.sort_values(by=['sample_id'])

            # median-center data
            median = df['abundance'].median()
            df['abundance'] = df['abundance'].apply(lambda x: x - median)

            # calculate median absolute derivation for band width
            mean = df['abundance'].mean()
            abs_derivation = df['abundance'].apply(lambda x: abs(x - mean))
            band_width = abs_derivation.median()

            # calculate number of upper and lower bands. After median-centering
            # data, there have to be both upper and lower bands
            num_upper_bands = ceil(max(df['abundance']) / band_width)
            num_lower_bands = abs(floor(min(df['abundance']) / band_width))

            # dataframe that has all the bands
            bands = list(range(num_lower_bands * -1, 0)) + list(range(1, num_upper_bands + 1))
            bands_df = pd.DataFrame(np.zeros((df.shape[0], len(bands))), columns=bands)

            # sort values into their corresponding bands
            # and fill in maxed out bands
            for i, (_, val) in enumerate(df['abundance'].iteritems()):
                modifier = -1 if val < 0 else 1
                diff = abs(val) - band_width
                band_num = modifier
                while diff > 0:
                    bands_df[band_num].iloc[i] = band_width
                    diff -= band_width
                    band_num += modifier
                bands_df[band_num].iloc[i] = diff + band_width

            # colors for the plot
            # bands stack over each other with opacity
            lower_band_color = f'rgba(255, 255, 0, {1.0 / num_lower_bands})'
            upper_band_color = f'rgba(0, 0, 255, {1.0 / num_upper_bands})'
            transparent = 'rgba(0, 0, 0, 0.0)'

            # generate figure with bands
            fig = go.Figure()
            for band in bands_df.columns:
                fillcolor = lower_band_color if band < 0 else upper_band_color
                fig.add_trace(
                    go.Scatter(x=df['sample_id'], y=bands_df[band], fillcolor=fillcolor,
                               fill='tozeroy', line={'color': transparent}, showlegend=False)
                )
            # https://plotly.com/python/legend/
            figs.append(fig)

        return figs
