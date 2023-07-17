# Import necessary modules
import dash
from dash import html
from dash import dcc
from dash.dependencies import Input, Output, State
import dash_bio as dashbio
import pandas as pd

from mmonitor.calculations.stats import scipy_correlation
from mmonitor.dashapp.app import app
from mmonitor.dashapp.base_app import BaseApp
from mmonitor.database.mmonitor_db import MMonitorDBInterface


class GenomeBrowser(BaseApp):

    def __init__(self, sql: MMonitorDBInterface):
        super().__init__(sql)
        self._init_layout()
        # self._init_callbacks()

    def _init_layout(self) -> None:
        # Define the layout

        upload = dcc.Upload(
            id='upload-data',
            children=html.Div([
                'Drag and Drop or ',
                html.A('Select Reference Genome')
            ]),
            style={
                'width': '100%',
                'height': '60px',
                'lineHeight': '60px',
                'borderWidth': '1px',
                'borderStyle': 'dashed',
                'borderRadius': '5px',
                'textAlign': 'center',
                'margin': '10px'
            },
            # Allow multiple files to be uploaded
            multiple=True
        )
        upload_div = html.Div(id='output-data-upload')
        browser_div = html.Div(id='genome-browser')

        CONTENT_STYLE = {

            "margin-right": "2rem",
            "padding": "2rem 1rem",
            'margin-bottom': '200px',
            'font-size': '21px'
        }

        container = html.Div(
            [upload,upload_div,browser_div],
            style=CONTENT_STYLE)

        self.layout = container


def parse_contents(contents, filename):
    content_type, content_string = contents.split(',')

    if 'gb' in filename:
        # Assume that user uploaded a genbank file
        df = pd.read_csv(filename, sep='\t')
        return df


@app.callback(Output('genome-browser', 'children'),
              Input('upload-data', 'contents'),
              State('upload-data', 'filename'))
def update_output(list_of_contents, list_of_names):
    if list_of_contents is not None:
        children = []
        for contents, name in zip(list_of_contents, list_of_names):
            df = parse_contents(contents, name)
            children.append(dashbio.Igv(
                id='my-dashbio-igv',
                genome=dict(
                    id='Prokka',
                    fastaURL='/path/to/fasta/file',
                    indexURL='/path/to/fasta/index',
                    cytobandURL='/path/to/cytoband/file',
                    tracks=[
                        dict(
                            name='Genes',
                            url='/path/to/genes/file',
                            format='bed',
                            indexed=False
                        ),
                    ]
                )
            ))
        return children
