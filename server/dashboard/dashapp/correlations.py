import json
from json import loads
from typing import Any, List, Union

import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
import dash_mantine_components as dmc
import pandas as pd
from dash_iconify import DashIconify
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import pandas as pd
import numpy as np
import seaborn as sns
import plotly.express as px
from scipy.cluster import hierarchy
from scipy.spatial import distance

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
        self.correlation_scores = self.compute_correlations_for_taxonomies(self.nanopore_df, self.meta_df)
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
                dmc.Text('Drag and Drop, or Select Files',weight=500, size='xl')
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
                               " Then refresh and Click right button to download Correlations.", className=self.text_style))

        download_buttons = dmc.Center(dmc.Group([download_template_button, download_correlations_button]))
        container = html.Div(
            [title, upload_component, download_correlations_component, download_buttons, notification_placeholder,
             bottom_text
             # ,dropdowns, corr_heatmap_dend, header_tb, dropdowns_tb,
             # selections_tb, correlations_tb, download_tb, download_template_component
             ])

        self.app.layout = dmc.MantineProvider(
            dmc.NotificationsProvider([
                container
            ], position='top-right')
        )

    # def _init_callbacks(self) -> None:
    #     @self.app.callback(
    #         Output('graph-score', 'figure'),
    #         Output('graph-test', 'figure'),
    #         Input('taxonomy-dd', 'value'),
    #         Input('methods-dd', 'value'),
    #         Input('tests-dd', 'value')
    #     )
    #     def _update_graphs(taxonomy: str, method: str, test: str) -> Tuple[Figure, Figure]:
    #         """
    #         Populate the correlations and probability graphs
    #         according to dropdown selections.
    #         """
    #
    #         # request data from database and filter columns containing metadata
    #         # abundance and metadata tables are joined to align entries by their sample_ids
    #         df = self._db.get_abundance_meta_by_taxonomy(taxonomy)
    #         meta_cols = [col for col in df.columns if col not in ['sample_id', 'abundance', 'meta_id', 'project_id']]
    #
    #         # for each metadata calculate the correlation and probability
    #         # transpose the list of tuples and extract each a correlation and a probability list:
    #         # [(c1, p1), (c2, p2), (c3, p3), ...] -> [c1, c2, c3, ...], [p1, p2, p3, ...]
    #         y_axis_tuple = [scipy_correlation(df['abundance'], df[meta], test, method) for meta in meta_cols]
    #         y_axis_score, y_axis_test = zip(*y_axis_tuple)
    #         y_axis_test = [xs[test] for xs in y_axis_test]
    #
    #         # generate plots
    #         fig_score = px.scatter(x=meta_cols, y=y_axis_score, labels={'x': 'Metric', 'y': f'{method} Score'})
    #         fig_test = px.scatter(x=meta_cols, y=y_axis_test, labels={'x': 'Metric', 'y': f'{test} Score'})
    #
    #         return fig_score, fig_test
    #
    #     @self.app.callback(
    #         Output('table-correlations', 'columns'),
    #         Output('table-correlations', 'data'),
    #         Output('taxonomy-dd-tb', 'value'),
    #         Input('apply-btn-tb', 'n_clicks'),
    #         Input('select-all-btn-tb', 'n_clicks'),
    #         Input('clear-selection-btn-tb', 'n_clicks'),
    #         State('taxonomy-dd-tb', 'value'),
    #         State('methods-dd-tb', 'value'),
    #         State('tests-dd-tb', 'value'),
    #         State('table-correlations', 'columns'),
    #         State('table-correlations', 'data'),
    #     )
    #     def _update_table(x: int, y: int, z: int,
    #                       taxonomies: Union[str, List[str]],
    #                       methods: Union[str, List[str]],
    #                       tests: Union[str, List[str]],
    #                       tb_columns: Any,
    #                       tb_data: Any,
    #                       ) -> Tuple[Iterable, Dict, List]:
    #         """
    #         Populate the data table with correlation scores and their probabilities
    #         according to the dropdown selections. This table contains data more suited
    #         for higher dimensions, but in order to keep it displayable and exportable
    #         it is complexly condensed into two dimensions.
    #
    #         The final dataframe/table will have this form:
    #
    #         Taxonomy  | Method or Test    | Meta1  | Meta2  | Meta3  | ...
    #         ---------------------------------------------------------------
    #         taxonomy1 | Pearson           | score1 | score2 | score3 | ...
    #         taxonomy1 | Pearson T-Test    | score1 | score2 | score3 | ...
    #         taxonomy1 | Pearson Bootstrap | score1 | score2 | score3 | ...
    #         taxonomy1 | Kendall           | score1 | score2 | score3 | ...
    #         taxonomy1 | Kendall T-Test    | score1 | score2 | score3 | ...
    #         taxonomy1 | Kendall Bootstrap | score1 | score2 | score3 | ...
    #         taxonomy2 | Pearson           | score1 | score2 | score3 | ...
    #         taxonomy2 | Pearson T-Test    | score1 | score2 | score3 | ...
    #         taxonomy2 | Pearson Bootstrap | score1 | score2 | score3 | ...
    #         taxonomy2 | Kendall           | score1 | score2 | score3 | ...
    #         taxonomy2 | Kendall T-Test    | score1 | score2 | score3 | ...
    #         taxonomy2 | Kendall Bootstrap | score1 | score2 | score3 | ...
    #         ...
    #         """
    #
    #         # figure out which button was clicked
    #         # default behaviour is 'apply'
    #         ctx = dash.callback_context
    #         button_id = 'apply-btn-tb'
    #         if ctx.triggered:
    #             button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    #
    #         # keep table, adjust selection in taxonomies dropdown menu
    #         if button_id == 'select-all-btn-tb':
    #             return tb_columns, tb_data, self._taxonomies
    #         elif button_id == 'clear-selection-btn-tb':
    #             return tb_columns, tb_data, []
    #
    #         # format dropdown selections and eject if selections are invalid
    #         taxonomies: List[str] = _force_list(taxonomies)
    #         methods: List[str] = _force_list(methods)
    #         tests: List[str] = _force_list(tests)
    #         if len(taxonomies) == 0 or len(methods) == 0:
    #             raise PreventUpdate
    #
    #         # request data from database and filter for metadata columns
    #         meta_df = self.get_all_meta()
    #         meta_cols = [meta for meta in meta_df.columns if meta not in ['sample_id', 'meta_id', 'project_id']]
    #
    #         # prepare the resulting dataframe/table
    #         columns = ['Taxonomy', 'Method or Test', *meta_cols]
    #         df = DataFrame(columns=columns, index=None)
    #
    #         # for each selected taxonomy
    #         for taxonomy in taxonomies:
    #
    #             # request corresponding abundances from database
    #             tax_df = self._db.get_abundance_by_taxonomy(taxonomy)
    #
    #             # for each selected method
    #             for method in methods:
    #
    #                 # prepare the row containing correlation scores per metadata
    #                 # and the rows containing the corresponding probabilities
    #                 # of the correlation score per metadata according to the selected tests
    #                 score_row = {'Taxonomy': taxonomy, 'Method or Test': method}
    #                 test_rows = {t: {'Taxonomy': taxonomy, 'Method or Test': ' '.join([method, t])} for t in tests}
    #
    #                 # for each metadata available in the database
    #                 for meta in meta_cols:
    #
    #                     # calculate the correlation score and its probability
    #                     # according to the selected tests
    #                     score, test_scores = scipy_correlation(tax_df['abundance'], meta_df[meta], tests, method)
    #
    #                     # populate the row containing correlation scores per metadata
    #                     score_row[meta] = score
    #
    #                     # then populate the rows containing the corresponding probabilities
    #                     # of the correlation score per metadata according to the selected tests
    #                     for test, test_score in test_scores.items():
    #                         test_rows[test][meta] = test_score
    #
    #                 # finally append the correlation row and the probability rows the the dataframe
    #                 df = df.append(score_row, ignore_index=True)
    #                 for test in tests:
    #                     df = df.append(test_rows[test], ignore_index=True)
    #
    #         # return data for the dash data table according to
    #         # https://dash.plotly.com/datatable
    #         self._table_df = df
    #         return [{"name": i, "id": i} for i in df.columns], df.to_dict('records'), taxonomies
    #
    #     @self.app.callback(
    #         Output('download-tb', 'data'),
    #         Input('export-btn-tb', 'n_clicks'),
    #     )
    #     def _export_table(n_clicks) -> Dict[Any, str]:
    #         """
    #         Download data table content.
    #         """
    #
    #         if n_clicks is None:
    #             raise PreventUpdate
    #         return dict(content=self._table_df.to_csv(index=False), filename='correlations.csv')

    def compute_correlations_for_taxonomies(self, taxonomy_df, metadata_df, taxonomic_level='taxonomy'):
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
                        row[meta_key] = taxonomy_abundance.corr(merged_df[meta_key])
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


def _force_list(x: Union[Any, List]) -> List[Any]:
    """
    Force object into a list if object is not a list.
    """

    return x if isinstance(x, list) else [x]
