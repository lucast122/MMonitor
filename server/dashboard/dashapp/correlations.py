from typing import Any, List, Union

import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
import dash_mantine_components as dmc
import numpy as np
import pandas as pd
import plotly.graph_objs as go
from dash_iconify import DashIconify
from dash_table import DataTable
from django_plotly_dash import DjangoDash

from users.models import NanoporeRecord, Metadata


class Correlations:
    """
    App to display correlations between abundance and metadata and their probabilities.
    The graph and data table are independent.
    The data table content may be downloaded in csv format.

    WARNING: - correlations can only be calculated for complete and sanitized data
             - bootstrapping is slow
    """

    def __init__(self, user_id):
        self.text_style = 'text-primary my-2'
        self.user_id = user_id
        self.app = DjangoDash('correlations', add_bootstrap_links=True)
        self.correlation_matrix = None

        def get_data():
            records = NanoporeRecord.objects.filter(user_id=self.user_id)
            # meta = Meta.objects.filter(user_id=self.user_id)
            self.records = records

            if not records.exists():
                return pd.DataFrame()  # Return an empty DataFrame if no records are found
            df = pd.DataFrame.from_records(records.values())
            self._taxonomies = df['taxonomy'].unique()
            # print(self._taxonomies)
            return df

        self.nanopore_df = get_data()
        self.meta_df = self.get_all_meta()
        self.corr_method = 'pearson'
        self.correlation_scores = self.compute_correlations_for_taxonomies(self.nanopore_df, self.meta_df,
                                                                           self.corr_method, 'taxonomy')
        # print(self.correlation_scores)

        self._methods = [
            'Pearson',
            'Spearman',
            'Kendall',
        ]
        self._tests = [
            'T-Test',
            'Bootstrap',
            'Fisher Z Transform',
        ]
        self._table_df = None

        self._init_layout()

    def _init_layout(self) -> None:

        corr_heatmap_dend = dcc.Graph(id='heatmap-dendrogram')

        notification_placeholder = html.Div(id='notification-output')

        """
        Correlations layout consists of
            - Graphs containing correlation and test scores
            - Data table containing correlations and test scores
        """
        title = dmc.Center(dmc.Title("Upload a csv with metadata to perform correlation analysis for your metagenomes",
                                     className=self.text_style,
                                     style={'font-weight': 'bold'}))
        download_template_button = dmc.Center(dmc.Group([dmc.Space(h=10),
                                                         dmc.Button('Download Metadata CSV Template',
                                                                    id='download-csv-button',
                                                                    leftIcon=DashIconify(
                                                                        icon="foundation:page-export-csv")),
                                                         ]))

        download_correlations_button = dmc.Center(dmc.Group([dmc.Space(h=10),
                                                             dmc.Button('Download Taxonomy-Metadata correlations',
                                                                        id='btn-download-corr',
                                                                        leftIcon=DashIconify(
                                                                            icon="foundation:page-export-csv")),
                                                             ]))

        download_template_component = dcc.Download(id='download-metadata-csv')

        download_correlations_component = dcc.Download(id="download-corr-csv")

        upload_component = dcc.Upload(
            id='upload-data',
            children=html.Div([
                dmc.Space(bottom=100),

                dmc.Text('Drag and Drop, or Select Files', weight=500, size='lg')
            ]),
            style={
                'width': '100%',
                'height': '300px',

                'borderWidth': '1px',
                'borderStyle': 'dashed',
                'borderRadius': '5px',
                'textAlign': 'center',
                'margin': '10px'
            },
            # Allow multiple files to be uploaded
            multiple=True
        )

        # graph dropdown menus in a flex box
        header_corr = dmc.Header(dmc.Text('Correlations of abundances and metadata'), height=100)
        taxonomy_dd = dcc.Dropdown(
            id='taxonomy-dd',
            options=[{'label': t, 'value': t} for t in self._taxonomies],
            value=self._taxonomies,
            style={'flex-grow': '1'},
            clearable=False,
        )
        methods_dd = dcc.Dropdown(
            id='methods-dd',
            options=[{'label': m, 'value': m} for m in self._methods],
            value=self._methods[0],
            style={'flex-grow': '1'},
            clearable=False,
        )
        tests_dd = dcc.Dropdown(
            id='tests-dd',
            options=[{'label': t, 'value': t} for t in self._tests],
            value=self._tests[0],
            style={'flex-grow': '1'},
            clearable=False,
        )
        dropdowns = html.Div(
            [dmc.Space(h=20), taxonomy_dd, methods_dd, tests_dd],
            style={'display': 'flex', 'justify-content': 'space-between'}
        )

        # graphs

        graph_container = html.Div(
            [
                # First row with two graphs
                html.Div(
                    [
                        # Score graph
                        html.Div(
                            [
                                dcc.Graph(
                                    id='graph-score',
                                    figure={
                                        'data': [],  # Replace with your data
                                        'layout': {
                                            'clickmode': 'event+select',
                                            # Add the rest of your layout properties here...
                                        }
                                    },
                                    style={"border": "2px solid black"}  # Add a border here
                                ),
                                html.Div(
                                    dcc.Markdown("**Figure 1**: Correlation score of the selected taxon"),
                                    style={"textAlign": "center", "margin-top": "1px"}  # Adjust "10px" as needed
                                )
                            ], style={'width': '50%', "padding": "5px"}
                        ),

                        # Test graph
                        html.Div(
                            [
                                dcc.Graph(
                                    id='graph-test',
                                    figure={
                                        'data': []  # Replace with your data
                                    },
                                    style={"border": "2px solid black"}  # Add a border here
                                ),
                                html.Div(
                                    dcc.Markdown("**Figure 2**: P-value of the test scores of the selected taxon"),
                                    style={"textAlign": "center", "margin-top": "1px"}  # Adjust "10px" as needed
                                )
                            ], style={'width': '50%', "padding": "5px"}
                        ),
                    ],
                    style={'display': 'flex'}
                ),

                # Heatmap graph with padding and margin like the other plots
                html.Div(
                    [
                        dcc.Graph(
                            id='heatmap-graph',
                            figure={'data': []},  # Replace with your heatmap data
                            style={"border": "2px solid black"}
                        ),
                        html.Div(
                            dcc.Markdown("**Figure 3**: Heatmap showing the selected correlation method of all taxa"),
                            style={"textAlign": "center", "margin-top": "1px"}  # Adjust "10px" as needed
                        )
                    ],
                    style={"padding": "5px"}
                )
            ]
        )

        # data table dropdown menus in a flexbox
        header_tb = html.H2('Select correlation data and export')
        taxonomy_dd_tb = dcc.Dropdown(
            id='taxonomy-dd-tb',
            options=[{'label': t, 'value': t} for t in self._taxonomies],
            value=self._taxonomies,
            style={'flex-grow': '1'},
            clearable=False,
            multi=True,
        )
        methods_dd_tb = dcc.Dropdown(
            id='methods-dd-tb',
            options=[{'label': m, 'value': m} for m in self._methods],
            value=self._methods[0],
            style={'flex-grow': '1'},
            clearable=False,
            multi=True,
        )
        tests_dd_tb = dcc.Dropdown(
            id='tests-dd-tb',
            options=[{'label': t, 'value': t} for t in self._tests],
            value=[],
            style={'flex-grow': '1'},
            clearable=False,
            multi=True,
        )
        dropdowns_tb = html.Div(
            [taxonomy_dd_tb, methods_dd_tb, tests_dd_tb],
            style={'display': 'flex', 'justify-content': 'space-between'}
        )

        # table interaction buttons in flexbox
        apply_btn_tb = dbc.Button(
            'Apply',
            id='apply-btn-tb',
            style={'margin': '5px'}
        )
        select_all_btn_tb = dbc.Button(
            'Select All',
            id='select-all-btn-tb',
            style={'margin': '5px'}
        )
        clear_selection_btn_tb = dbc.Button(
            'Clear Selection',
            id='clear-selection-btn-tb',
            style={'margin': '5px'}
        )
        export_btn_tb = dbc.Button(
            'Export',
            id='export-btn-tb',
            style={'margin': '5px'}
        )
        selections_tb = html.Div(
            [apply_btn_tb, select_all_btn_tb, clear_selection_btn_tb, export_btn_tb],
            style={'display': 'flex', 'padding': '10px'}
        )

        # data table and its download element
        correlations_tb = DataTable(id='table-correlations', data=[], columns=[])
        download_tb = dcc.Download(id='download-tb')

        bottom_text = dmc.Center(dmc.Text("Press left button to download template. Fill it out and upload it."
                                          " After successful upload click right button to download Correlations.",
                                          className=self.text_style))

        corr_heatmap_dend = dmc.Center(dcc.Graph(
            id='heatmap-dendrogram',
            figure=self.create_heatmap()  # Call the function to generate the heatmap figure
        ))

        download_buttons = dmc.Center(dmc.Group([download_template_button, download_correlations_button]))
        container = html.Div(
            [title, upload_component, download_correlations_component, download_buttons, notification_placeholder,
             corr_heatmap_dend,
             bottom_text
             # ,dropdowns, corr_heatmap_dend, header_tb, dropdowns_tb,
             # selections_tb, correlations_tb, download_tb, download_template_component
             ])

        self.app.layout = dmc.MantineProvider(
            dmc.NotificationsProvider([
                container
            ], position='top-right')
        )

    def compute_correlations_for_taxonomies(self, taxonomy_df, metadata_df, method, taxonomic_level='taxonomy'):
        taxonomy_df = taxonomy_df.drop_duplicates(subset=['sample_id', 'taxonomy'])

        if metadata_df.empty or taxonomy_df.empty:
            print("No metadata or taxonomy data found")
            return pd.DataFrame()

        # Merging the DataFrames
        merged_df = pd.merge(taxonomy_df, metadata_df, on=['sample_id', 'user_id'], how='right')

        # Extract metadata keys from 'data' column
        first_valid_dict = next((item for item in merged_df['data'] if isinstance(item, dict)), None)
        if first_valid_dict is None:
            print("No valid metadata found in 'data' column")
            return pd.DataFrame()
        metadata_keys = list(first_valid_dict.keys())

        # Extract metadata keys into separate columns
        for key in metadata_keys:
            merged_df[key] = merged_df['data'].apply(lambda x: x.get(key) if isinstance(x, dict) else None)

        # Initialize a list to collect correlation data
        correlation_data = []

        # Calculate correlation for each taxonomy
        unique_taxonomies = merged_df[taxonomic_level].unique()
        for taxonomy in unique_taxonomies:
            # Select abundance for the current taxonomy, fill NaN with 0
            taxonomy_abundance = merged_df[merged_df[taxonomic_level] == taxonomy]['abundance'].fillna(0)
            row = {'taxonomy': taxonomy}
            for meta_key in metadata_keys:
                if pd.api.types.is_numeric_dtype(merged_df[meta_key]):
                    # Check if there is variance in the data
                    if taxonomy_abundance.std() != 0:
                        row[meta_key] = taxonomy_abundance.corr(merged_df[meta_key], method=method)
                    else:
                        row[meta_key] = 0  # Assign 0 for zero variance
                else:
                    row[meta_key] = np.nan
            correlation_data.append(row)

        # Create a DataFrame from the collected data
        correlation_matrix = pd.DataFrame(correlation_data)
        self.correlation_matrix = correlation_matrix

        return correlation_matrix

    def get_all_meta(self):
        meta = Metadata.objects.filter(user_id=self.user_id)
        if not meta.exists():
            print(f"Found no metadata for user id {self.user_id}")
            return pd.DataFrame()  # Return an empty DataFrame if no records are found
        meta_df = pd.DataFrame.from_records(meta.values())
        return meta_df

    def create_heatmap(self):
        if self.correlation_matrix is None or self.correlation_matrix.empty:
            return go.Figure()  # Return an empty figure if no data is available

        # Check the shape of the correlation matrix
        print(f"Correlation Matrix Shape: {self.correlation_matrix.shape}")
        print(f"Taxonomies: {len(self.correlation_matrix['taxonomy'])}")

        print(self.correlation_matrix)
        matrix_for_hetmap = self.correlation_matrix.set_index('taxonomy')
        fig = go.Figure(
            data=go.Heatmap(z=matrix_for_hetmap.values, x=matrix_for_hetmap.columns, y=matrix_for_hetmap.index,
                            colorscale='Portland'))
        fig.update_layout(
            xaxis=dict(type='category'),
            yaxis=dict(type='category'),
            height=len(self._taxonomies) * 10,
            width=len(self.meta_df.columns) * 100 + 200,
            title='Heatmap of taxonomy-metadata correlations',
            xaxis_title='Metadata',
            yaxis_title='Taxonomy',
            legend_title=f'{self.corr_method} correlation'

        )
        return fig


def _force_list(x: Union[Any, List]) -> List[Any]:
    """
    Force object into a list if object is not a list.
    """

    return x if isinstance(x, list) else [x]
