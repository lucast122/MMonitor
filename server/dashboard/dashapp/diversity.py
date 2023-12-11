from django_plotly_dash import DjangoDash
import pandas as pd
import plotly.express as px
from users.models import NanoporeRecord
import skbio.diversity
import dash_bootstrap_components as dbc
import dash_core_components as dcc
from dash import html

class Diversity:
    """
    App to display the abundances of taxonomies in various formats.
    """

    def get_data(self):

        records = NanoporeRecord.objects.filter(user_id=self.user_id)
        self.records = records
        if not records.exists():
            return pd.DataFrame()  # Return an empty DataFrame if no records are found

        return pd.DataFrame.from_records(records.values())


    def __init__(self,user_id):
        self.records = None
        self.user_id = user_id
        dbc_css = ("https://cdn.jsdelivr.net/gh/AnnMarieW/dash-bootstrap-templates@V1.0.2/dbc.min.css")
        self.app = DjangoDash('diversity', external_stylesheets=[dbc.themes.BOOTSTRAP, dbc_css])
        self.unique_sample_ids = None
        self.unique_samples = None
        self.unique_counts = None
        self.unique_species = None
        self.df_full_for_diversity = None
        self.shannon_diversity = None
        self.simpson_diversity = None
        self.df = pd.DataFrame()
        # Convert the QuerySet to a DataFrame
        self.df = self.get_data()
        self.abundance_lists = None

        if not self.df.empty:
            self.unique_sample_ids = self.records.values('sample_id').distinct()
            # Convert QuerySet to a list
            self.unique_sample_ids = [item['sample_id'] for item in self.unique_sample_ids]
            self.unique_samples = NanoporeRecord.objects.filter(user_id=self.user_id).values('sample_id').distinct()
            self.unique_projects_ids = NanoporeRecord.objects.filter(user_id=self.user_id).values(
                'project_id').distinct()
            self.unique_projects_ids = [item['project_id'] for item in self.unique_projects_ids]

            self.unique_subprojects = NanoporeRecord.objects.filter(user_id=self.user_id).values(
                'subproject').distinct()
            self.unique_subprojects = [item['subproject'] for item in self.unique_subprojects]
            self.unique_species = self.df['taxonomy'].unique()
            self.unique_species = self.df['taxonomy'].unique()
            self.df_full_for_diversity = self.df.pivot_table(index='sample_id',
                                                             columns='taxonomy',
                                                             values='abundance',
                                                             fill_value=0)

            sample_project_mapping = self.records.values('sample_id', 'project_id')
            self.sample_to_project_dict = {item['sample_id']: item['project_id'] for item in sample_project_mapping}

            # self.df_full_for_diversity.columns = self.df_full_for_diversity.columns.droplevel(0)

            self.df_sorted = self.df.sort_values(by=["sample_id", "abundance"], ascending=[True, False])

            # Get the number of unique values in each column
            # get number of unique taxonomies for creation of slider. limit max taxa to plot to 100
            self.unique_counts = min(self.df.nunique()[1], 500)

        self.calculate_alpha_diversity()
        self._init_layout()


    def _init_layout(self) -> None:
        metric_label = dbc.Label("Alpha diversity metric:", html_for='diversity_metric_dropdown')
        diversity_metric_selector = dbc.Col(
            [

                dcc.Dropdown(
                    id='diversity_metric_dropdown',
                    options=[
                        {'label': 'Shannon', 'value': 'Shannon'},
                        {'label': 'Simpson', 'value': 'Simpson'}
                    ],
                    value='Shannon',
                    style={'width': '100%'}
                )
            ],
            # You can adjust this width as per your layout requirement
            width=4
        )

        graph_container = html.Div(
            [
                # graph elements
                html.Div(
                    [
                        dcc.Graph(
                            id='alpha_diversities_plot1',
                            figure={
                                'data': [],  # Replace with your data
                                'layout': {
                                    'clickmode': 'event+select'


                                    # Add the rest of your layout properties here...
                                }
                            },
                            style={"border": "2px solid black"}  # Add a border here
                        ),
                        html.Div(


                        )
                    ], style={'width': '100%', "padding": "5px"}
                ),

                html.Div(
                    [
                        dcc.Graph(
                            id='alpha_diversities_plot2',
                            figure={
                                'data': []  # Replace with your data
                            },
                            style={"border": "2px solid black"}  # Add a border here
                        )

                    ], style={'width': '100%', "padding": "5px"}
                ),
            ]

        )

        dropdown_container = dbc.Container([
            dbc.Row([
                dbc.Col(
                    [
                        dbc.Label("Samples to plot:", html_for='sample_select_value', id='sample_select_text',
                                  style={'width': '100%'}),
                        dcc.Dropdown(
                            id='sample_select_value',
                            options=[{'label': i, 'value': i} for i in
                                     self.unique_sample_ids] if self.unique_sample_ids else [
                                {'label': 'Default', 'value': 'Default'}],
                            multi=True,
                            style={'width': '100%', 'margin-bottom': '5px'},
                            value=self.unique_sample_ids
                        ),
                    ]

                ),

                dbc.Col(
                    [
                        dbc.Label("Select Samples by project:", html_for='project-dropdown', id='project-dropdown-text',
                                  style={'width': '100%'}),
                        dcc.Dropdown(
                            id='project-dropdown',
                            options=[{'label': 'All Projects', 'value': 'ALL'}] +
                                    [{'label': project, 'value': project} for project in self.unique_projects_ids],

                            value=None,
                            style={'width': '100%', 'margin-bottom': '5px'}

                        ),
                    ],
                    width=2
                ),

                dbc.Col(
                    [
                        dbc.Label("Select Samples by subproject:", html_for='subproject-dropdown',
                                  id='subproject-dropdown-text'),
                        dcc.Dropdown(
                            id='subproject-dropdown',
                            options=[{'label': 'All Subprojects', 'value': 'ALL'}] +
                                    [{'label': subproject, 'value': subproject} for subproject in
                                     self.unique_subprojects],

                            value=None

                        ),
                    ],
                    width=2
                )
            ])
        ],fluid=True, style={'backgroundColor': '#F5F5F5'}, className="dbc dbc-ag-grid")

        download_button = dbc.Col(
            dbc.Button("Download Diversities as CSV", id="btn-download-diversity"),
            # Adjust this width too as per your requirement
            width=4
        )

        download_component = dcc.Download(id="download-diversity-csv")

        # Wrapping in a row
        selection_row = dbc.Row([diversity_metric_selector, download_button])

        # Adjusting the main container
        container = dbc.Container([metric_label,selection_row, download_component, graph_container, dropdown_container],
                                  fluid=True, style={'backgroundColor': '#F5F5F5'}, className="dbc dbc-ag-grid")

        self.app.layout = container

    def calculate_alpha_diversity(self):
        abundance_lists = self.df_full_for_diversity

        self.simpson_diversity = skbio.diversity.alpha_diversity(metric="simpson", counts=abundance_lists,
                                                            ids=self.unique_sample_ids)
        self.shannon_diversity = skbio.diversity.alpha_diversity(metric="shannon", counts=abundance_lists,
                                                            ids=self.unique_sample_ids)
        print(f"simpson diversity: {self.simpson_diversity}")
        print(f"shannon diversity: {self.shannon_diversity}")
