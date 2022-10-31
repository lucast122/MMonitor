import base64
import glob

import dash
from dash import dcc
from dash import html

from mmonitor.dashapp.app import app
from mmonitor.dashapp.base_app import BaseApp


class Kegg(BaseApp):

    def __init__(self):
        self._init_layout()
        self._init_callbacks()

    # @app.server.route('/horizon.png<cache_bust>')
    # def serve_image(cache_bust):
    #     """
    #     Allows dash to display png images from  ../resources/images/
    #
    #     The cache_bust is a way to make the url unique.
    #     This is necessary to force the browser to reload the
    #     presumably 'static' image file that it had previously cached.
    #     """
    #     return send_from_directory(images_path, 'horizon.png')

    def _init_layout(self) -> None:
        self._static_image_route = "/static/"
        self._samples = glob.glob("/Users/timolucas/PycharmProjects/MMonitor/desktop/src/resources/pipeline_out/*/")
        print(self._samples)
        header = html.H1("Functional mapping of annotated genomes to KEGG pathways")
        print(self._samples)
        sample_dropdown = dcc.Dropdown(id="sample-dropdown", options=[{'label': t, 'value': t} for t in self._samples],
                                       value=self._samples[0])
        pathway_dropdown = dcc.Dropdown(id="pathway-dropdown")
        dd = html.Div(id='dd-output-container')

        dropdowns = html.Div(
            [sample_dropdown, pathway_dropdown]
        )

        image = html.Img(
            id='kegg-plot',
            alt='Please select a kegg plot',
            style={'display': 'block', 'margin-left': 'auto', 'margin-right': 'auto', 'padding': '20px'}
        )

        container = html.Div([header, dropdowns, dd, image])

        self._layout = container

    def _init_callbacks(self) -> None:
        @app.callback(
            dash.dependencies.Output('pathway-dropdown', 'options'),
            [dash.dependencies.Input('sample-dropdown', 'value')]
        )
        def update_pathway_dropdown(sample):
            return [{'label': i.split("/")[-1].removesuffix(".png"), 'value': i} for i in glob.glob(f"{sample}/*.png")]

        @app.callback(
            dash.dependencies.Output('kegg-plot', 'src'),
            dash.dependencies.Input('pathway-dropdown', 'value')
        )
        def update_image_src(image_path):
            print('current image_path = {}'.format(image_path))
            encoded_image = base64.b64encode(open(image_path, 'rb').read())
            return 'data:image/png;base64,{}'.format(encoded_image.decode())

            return value
