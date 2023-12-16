from skbio.diversity import beta_diversity
from dash.dependencies import Input, Output
from skbio.stats import ordination
from django_plotly_dash import DjangoDash
import pandas as pd
import plotly.express as px
from users.models import NanoporeRecord
import skbio.diversity
import dash_bootstrap_components as dbc
import dash_core_components as dcc
from dash import html
from dash_extensions import Lottie
from dash import dcc, html
from dash.dependencies import Input, Output
import dash_mantine_components as dmc
import dash_mantine_components as dmc
import dash_mantine_components as dmc
from dash import callback, html, Input, Output, dcc
from dash_mantine_components import MantineProvider


def create_colour_by_menu():
    return html.Div(
        [
            dmc.Menu(
                [
                    dmc.MenuTarget(dmc.Button("Colour by")),
                    dmc.MenuDropdown(
                        [
                            dmc.MenuItem("Project", id="project-button", n_clicks=0),
                            dmc.MenuItem("Subproject", id="subproject-button", n_clicks=0),
                            dmc.MenuItem("Sample Date", id="sample-date-button", n_clicks=0),  # New menu item

                            dmc.MenuItem("K-means Clustering", id="kmeans-button", n_clicks=0),
                            dmc.NumberInput(
                                id='kmeans-input',
                                label='Number of Clusters (k)',
                                value=3,  # Default value
                                min=1,
                                step=1,
                                style={'width': '100%'}
                            )
                        ]
                    ),
                ]
            )
        ]
    )


class Diversity:
    """
    App to display the abundances of taxonomies in various formats.
    """

    def __init__(self, user_id):
        dbc_css = ("https://cdn.jsdelivr.net/gh/AnnMarieW/dash-bootstrap-templates@V1.0.2/dbc.min.css")
        self.app = DjangoDash('diversity', external_stylesheets=[dbc.themes.BOOTSTRAP, dbc_css])

        self.records = None
        self.user_id = user_id

        self.unique_sample_ids = None
        self.unique_samples = None
        self.unique_counts = None
        self.unique_species = None
        self.beta_diversity_matrix = None
        self.df_full_for_diversity = None
        self.shannon_diversity = None
        self.pcoa_results = None
        self.simpson_diversity = None
        self.df = pd.DataFrame()
        # Convert the QuerySet to a DataFrame
        self.df = self.get_data()
        self.abundance_lists = None

        self.alpha_label = html.Label("Alpha diversity plots", className='text-primary my-2',
                                      style={'font-weight': 'bold'})
        self.beta_label = html.Label("Beta diversity plots", className='text-primary my-2',
                                     style={'font-weight': 'bold'})

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

            self.sample_project_mapping = self.records.values('sample_id', 'project_id')
            self.sample_to_project_dict = {item['sample_id']: item['project_id'] for item in
                                           self.sample_project_mapping}

            self.sample_subproject_mapping = self.records.values('sample_id', 'subproject')
            self.sample_to_subproject_dict = {item['sample_id']: item['subproject']
                                              for item in self.sample_subproject_mapping}

            self.sample_date_mapping = self.records.values('sample_id', 'date')
            self.sample_to_date_dict = {item['sample_id']: item['date'] for item in
                                        self.sample_date_mapping}

            # self.df_full_for_diversity.columns = self.df_full_for_diversity.columns.droplevel(0)

            self.df_sorted = self.df.sort_values(by=["sample_id", "abundance"], ascending=[True, False])

            # Get the number of unique values in each column
            # get number of unique taxonomies for creation of slider. limit max taxa to plot to 100
            self.unique_counts = min(self.df.nunique()[1], 500)

        self._init_layout()
        self.calculate_alpha_diversity()
        self.calculate_beta_diversity()

    def _init_layout(self) -> None:

        graph_container = html.Div(

            [self.alpha_label,
             # Flex container for alpha diversity plots
             html.Div(
                 [
                     html.Div(
                         dcc.Graph(id='alpha_diversities_plot1'),
                         style={'flex': '1', "padding": "5px"}
                     ),
                     html.Div(
                         dcc.Graph(id='alpha_diversities_plot2'),
                         style={'flex': '1', "padding": "5px"}
                     ),
                 ],
                 style={'display': 'flex', 'flex-direction': 'row', 'justify-content': 'space-between'}
             ),
             self.beta_label,

             # Beta diversity heatmap section
             html.Div(

                 dcc.Graph(id='beta_diversity_heatmap'),
                 style={"padding": "5px"}
             ),
             # PCoA plot container
             html.Div(
                 dcc.Graph(id='pcoa_plot_container'),
                 style={"padding": "5px"
                        }
             ),
             # Checkbox for 3D PCoA plot
             html.Div([
                 dmc.Switch(
                     size="lg",
                     radius="sm",
                     id="toggle-3d",
                     label="Toggle 3D",
                     checked=False
                 ),
                 dmc.Space(h=10),
                 dmc.Text(id="toggle-3d-text")],

                 # dbc.Checkbox(id='toggle-3d', value=False, label='Show 3D Plot'),
                 # style={"padding": "5px"}
             ),
             ],
            style={"padding": "5px"}
        )

        # Dropdowns and buttons
        project_dropdown = self.create_dropdown('project-dropdown', self.unique_projects_ids,
                                                'Select Samples by project:')
        subproject_dropdown = self.create_dropdown('subproject-dropdown', self.unique_subprojects,
                                                   'Select Samples by subproject:')
        diversity_metric_selector = self.create_dropdown('diversity_metric_dropdown',
                                                         [('Shannon', 'Shannon'), ('Simpson', 'Simpson')],
                                                         'Alpha diversity metric:', "Shannon")

        dropdown_container = dbc.Container(
            dbc.Row([dbc.Col(item, width=4) for item in
                     [diversity_metric_selector, project_dropdown, subproject_dropdown]]),
            fluid=True, style={'backgroundColor': '#F5F5F5'}, className="dbc dbc-ag-grid"
        )

        download_button = dbc.Button("Download as CSV", id="btn-download-diversity", style={'margin-top': '20px'})
        download_component = dcc.Download(id="download-diversity-csv")

        sample_select_dropdown = dcc.Dropdown(
            id='sample_select_value',
            options=[{'label': i, 'value': i} for i in self.unique_sample_ids] if self.unique_sample_ids else [
                {'label': 'Default', 'value': 'Default'}],
            multi=True,
            style={'width': '100%', 'margin-bottom': '5px', 'margin-top': '10px', 'margin-bot': '5px'},
            value=self.unique_sample_ids
        )

        # Main container
        container = dbc.Container(
            [sample_select_dropdown,
             dropdown_container,
             download_button,
             download_component,

             graph_container,
             create_colour_by_menu()

             ],
            fluid=True, style={'backgroundColor': '#F5F5F5'}, className="dbc dbc-ag-grid"
        )

        self.app.layout = container

    def calculate_alpha_diversity(self):
        abundance_lists = self.df_full_for_diversity

        self.simpson_diversity = skbio.diversity.alpha_diversity(metric="simpson", counts=abundance_lists,
                                                                 ids=self.unique_sample_ids)
        self.shannon_diversity = skbio.diversity.alpha_diversity(metric="shannon", counts=abundance_lists,
                                                                 ids=self.unique_sample_ids)
        print(f"simpson diversity: {self.simpson_diversity}")
        print(f"shannon diversity: {self.shannon_diversity}")

    def calculate_beta_diversity(self):
        # Bray-Curtis is a common choice for beta diversity, but you can choose other metrics
        self.beta_diversity_matrix = beta_diversity("braycurtis", self.df_full_for_diversity, self.unique_sample_ids)
        self.pcoa_results = ordination.pcoa(self.beta_diversity_matrix)

    def create_dropdown(self, dropdown_id, options, label_text, value=None):
        """ Helper function to create dropdown elements. """
        # label = dbc.Label(label_text, html_for=dropdown_id)
        label = html.Label(label_text, className='text-primary my-2', style={'font-weight': 'bold'})

        options_formatted = [{'label': name, 'value': value} for value, name in options] if isinstance(options[0],
                                                                                                       tuple) else [
            {'label': value, 'value': value} for value in options]
        dropdown = dcc.Dropdown(
            id=dropdown_id,
            options=options_formatted,
            style={'width': '100%'},
            value=value
        )
        return dbc.Col([label, dropdown])

    def get_data(self):

        records = NanoporeRecord.objects.filter(user_id=self.user_id)
        self.records = records
        if not records.exists():
            return pd.DataFrame()  # Return an empty DataFrame if no records are found

        return pd.DataFrame.from_records(records.values())
