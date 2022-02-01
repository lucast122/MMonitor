import uuid

import dash_html_components as html
import dash_core_components as dcc
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
from flask import send_from_directory

from mmonitor.calculations.horizon_r import generate_image
from mmonitor.config import images_path
from mmonitor.dashapp.app import app
from mmonitor.dashapp.base_app import BaseApp
from mmonitor.database.mmonitor_db import MMonitorDBInterface


@app.server.route('/horizon.png<cache_bust>')
def serve_image(cache_bust):
    """
    Allows dash to display png images from  ../resources/images/

    The cache_bust is a way to make the url unique.
    This is necessary to force the browser to reload the
    presumably 'static' image file that it had previously cached.
    """
    return send_from_directory(images_path, 'horizon.png')


class Horizon(BaseApp):
    """
    App to display the taxonomy abundances in a horizon plot.
    Calls an R script and uploads the generated image.
    """

    def __init__(self, sql: MMonitorDBInterface):
        super().__init__(sql)
        self._init_layout()
        self._init_callbacks()

    def _init_layout(self) -> None:
        header = html.H1("Horizon plot of taxonomy abundances")
        width_label = html.Label('Width: ')
        width_input = dcc.Input(
            id='width-input',
            type='text',
        )
        height_label = html.Label('Height: ')
        height_input = dcc.Input(
            id='height-input',
            type='text',
        )
        confirm = html.Button(
            'Generate',
            id='confirm',
            style={'padding': '5px'}
        )
        input_container = html.Div([
            width_label,
            width_input,
            height_label,
            height_input,
            confirm
        ])

        image = html.Img(
            id='horizon-plot',
            alt='Please generate a Horizon Plot',
            style={'display': 'block', 'margin-left': 'auto', 'margin-right': 'auto', 'padding': '20px'}
        )
        container = html.Div([header, input_container, image])

        self.layout = container

    def _init_callbacks(self) -> None:
        @app.callback(
            Output('horizon-plot', 'src'),
            Input('confirm', 'n_clicks'),
            State('width-input', 'value'),
            State('height-input', 'value'),
        )
        def generate_plot(b, width, height):

            if width is None or height is None:
                raise PreventUpdate
            try:
                width = int(width)
                height = int(height)
            except (ValueError, TypeError):
                raise PreventUpdate

            print('generating image')
            q = 'SELECT sample_id, taxonomy, abundance FROM mmonitor'
            df = self._sql.query_to_dataframe(q)
            generate_image(df, width, height)

            # append cache_bust to the source url (see 'serve_image')
            return '/horizon.png' + '__v__={version}'.format(version=uuid.uuid1())
