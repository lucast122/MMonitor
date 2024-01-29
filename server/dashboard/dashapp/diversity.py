import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_mantine_components as dmc
import numpy as np
import pandas as pd
import skbio.diversity
from dash import html, dcc
from django_plotly_dash import DjangoDash
from skbio.diversity import beta_diversity


from skbio import DistanceMatrix


from skbio.stats import ordination




import skbio.diversity
import dash_bootstrap_components as dbc
from dash_extensions import Lottie
from dash import dcc, html
import dash_mantine_components as dmc
import dash_mantine_components as dmc
import dash_mantine_components as dmc
from dash import html, Output, dcc



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


def calculate_normalized_counts(self):
    counts_df = pd.DataFrame.from_records(NanoporeRecord.objects.filter(user_id=self.user_id).values())
    stats_df = pd.DataFrame.from_records(SequencingStatistics.objects.filter(user_id=self.user_id).values())

    # Merge the counts and stats dataframes on sample_id
    merged_df = pd.merge(counts_df, stats_df, left_on='sample_id', right_on="sample_name")

    # Calculate normalized counts by dividing each count by the numebr of bases sequenced and then multiplying by
    # 1 million to make normalized counts more similar to normal counts in value range
    merged_df['normalized_count'] = (merged_df['count'] / merged_df['total_bases_sequenced']) * 10000000

    # Selecting only necessary columns for the final DataFrame
    normalized_counts_df = merged_df[['sample_id', 'taxonomy', 'abundance', 'count', 'normalized_count']]
    return normalized_counts_df


def rarefy_sample(sample, depth):
    # print(sample)
    if sum(sample) >= depth:
        return np.random.choice(np.where(sample > 0)[0], size=depth, replace=False, p=sample / sum(sample))
    else:
        raise ValueError("Sample size is less than the specified rarefaction depth.")
    return sample


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

        self.alpha_label = dmc.Center(dmc.Title("Alpha diversity plots", className='text-primary my-2',
                                     style={'font-weight': 'bold'}))
        self.beta_label = dmc.Center(dmc.Title("Beta diversity plots", className='text-primary my-2',
                                                style={'font-weight': 'bold'}))

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

            self.df_full_for_diversity = self.df.pivot_table(index='sample_id',
                                                             columns='taxonomy',
                                                             values='count',
                                                             fill_value=0)
            self.df_normalized_counts = self.calculate_normalized_counts()
            # self.df_normalized_counts_full = self.df_normalized_counts.pivot_table(index='sample_id',
            #                                                  columns='taxonomy',
            #                                                  values='normalized_count',
            #                                                  fill_value=0)

            # print(f"df_full_for_diversirt (pivot table of taxonomies) {self.df_full_for_diversity}")



            # self.df_full_for_diversity.columns = self.df_full_for_diversity.columns.droplevel(0)

            self.df_sorted = self.df.sort_values(by=["sample_id", "abundance"], ascending=[True, False])

            # Get the number of unique values in each column
            # get number of unique taxonomies for creation of slider. limit max taxa to plot to 100
            self.unique_counts = min(self.df.nunique()[1], 500)

        self._init_layout()
        self.calculate_alpha_diversity(use_normalized_counts=False)

        self.pcoa_results, self.beta_diversity_matrix, self.samples_with_valid_distances = self.calculate_beta_diversity()

        self.sample_project_mapping = self.records.values('sample_id', 'project_id')
        self.sample_to_project_dict = {item['sample_id']: item['project_id'] for item in
                                       self.sample_project_mapping}

        self.sample_subproject_mapping = self.records.values('sample_id', 'subproject')
        self.sample_to_subproject_dict = {item['sample_id']: item['subproject']
                                          for item in self.sample_subproject_mapping}

        self.sample_date_mapping = self.records.values('sample_id', 'date')
        self.sample_to_date_dict = {item['sample_id']: item['date'] for item in
                                    self.sample_date_mapping}

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
            fluid=True, style={'padding-left': 0}, className="dbc dbc-ag-grid"
        )

        download_button = dbc.Button("Download as CSV", id="btn-download-diversity", style={'margin-top': '20px','margin-left': '20px'})
        download_component = dcc.Download(id="download-diversity-csv")

        sample_select_dropdown = dbc.Col([dmc.Text("Samples to plot:", className='text-primary my-2', id='sample_select_text',
                                 style={'width': '100%'}),dcc.Dropdown(
            id='sample_select_value',
            options=[{'label': i, 'value': i} for i in self.unique_sample_ids] if self.unique_sample_ids else [
                {'label': 'Default', 'value': 'Default'}],
            multi=True,
            style={'width': '100%', 'margin-bottom': '5px', 'margin-top': '10px', 'margin-bot': '5px'},
            value=self.unique_sample_ids
        )],style={"padding-left": "0px"})

        # Main container
        container = dbc.Container(
            [sample_select_dropdown,
             dropdown_container,
             download_button,
             download_component,

             graph_container,
             create_colour_by_menu()

             ],
            fluid=True, style={}, className="dbc dbc-ag-grid"
        )

        self.app.layout = container

    """Randomly subsample a sample to a specified depth."""

    def calculate_alpha_diversity(self,use_rarefaction=False,use_normalized_counts=False):

        abundance_lists = self.df_full_for_diversity
        # Rarefaction
        if use_rarefaction:
            min_sample_size = min(abundance_lists.sum(axis=1))
            rarefied_counts = []
            for sample in abundance_lists:
                # print(sample)
                rarefied_sample = np.zeros_like(sample)
                subsampled_indices = rarefy_sample(sample, min_sample_size)
                for idx in subsampled_indices:
                    rarefied_sample[idx] += 1
                rarefied_counts.append(rarefied_sample)
            abundance_lists = np.array(rarefied_counts)
        if use_normalized_counts:
            normalized_counts_df = self.calculate_normalized_counts()
            # print("normalized_counts_df")
            # print(normalized_counts_df)
            # print("unique sample_ids in normalized_counts_df")
            # print(normalized_counts_df['sample_id'].nunique())
            # Pivot the DataFrame similar to self.df_full_for_diversity
            abundance_lists = normalized_counts_df.pivot_table(index='sample_id',
                                                               columns='taxonomy',
                                                               values='normalized_count',
                                                               fill_value=0)
        else:
            abundance_lists = self.df_full_for_diversity

        print("Number of unique sample IDs:", len(self.unique_sample_ids))
        print("Number of rows in abundance lists:", abundance_lists.shape[0])

        # Check if the length of unique_sample_ids matches the number of rows in abundance_lists
        if len(self.unique_sample_ids) != abundance_lists.shape[0]:
            raise ValueError("Mismatch in the number of samples and abundance rows")

        self.simpson_diversity = skbio.diversity.alpha_diversity(metric="simpson", counts=abundance_lists,
                                                                 ids=self.unique_sample_ids)
        self.shannon_diversity = skbio.diversity.alpha_diversity(metric="shannon", counts=abundance_lists,
                                                                 ids=self.unique_sample_ids)
        # print(f"simpson diversity: {self.simpson_diversity}")
        # print(f"shannon diversity: {self.shannon_diversity}")

    def calculate_beta_diversity(self):
        # calculate bray curtis index
        self.beta_diversity_matrix = beta_diversity("braycurtis", self.df_full_for_diversity, self.unique_sample_ids)
        self.pcoa_results = ordination.pcoa(self.beta_diversity_matrix)
        dm = beta_diversity("braycurtis", self.df_full_for_diversity, self.unique_sample_ids)
        df = dm.to_data_frame()
        print(f"dm after conversion: {dm}")
        print(f"df after conversion: {df}")

        rows_to_drop = df.index[df.isna().any(axis=1)]
        print(f"rows to drop: {rows_to_drop}")
        cols_to_drop = df.columns[df.isna().any(axis=0)]
        print(f"cols to drop: {cols_to_drop}")
        # Finding intersecting set of indices to keep
        print(f"df.index: {df.index}")
        print(f"rows to drop: {rows_to_drop}")
        indices_to_keep = set(df.index) - set(rows_to_drop)

        indices_to_keep = indices_to_keep.intersection(set(df.columns) - set(cols_to_drop))

        print(f"indices to keep {indices_to_keep}")
        # Dropping rows and columns outside the intersecting set
        df_clean = df.loc[list(indices_to_keep), list(indices_to_keep)]
        # Rebuilding the DistanceMatrix
        clean_dm = DistanceMatrix(df_clean.values, ids=list(indices_to_keep))
        print(f"clean_dm: {clean_dm}")
        pcoa_results = ordination.pcoa(clean_dm)
        return pcoa_results, clean_dm, indices_to_keep


    def create_dropdown(self, dropdown_id, options, label_text, value=None, multi_select=False):
        """ Helper function to create dropdown elements. """
        label = dmc.Text(label_text, className='text-primary my-2')

        # Handling no options provided
        if not options:
            options_formatted = [{'label': 'Default', 'value': 'Default'}]
        else:
            options_formatted = [{'label': 'All Projects', 'value': 'ALL'}]
            if isinstance(options[0], tuple):
                options_formatted += [{'label': name, 'value': val} for val, name in options]
            else:
                options_formatted += [{'label': val, 'value': val} for val in options]

        dropdown_style = {'width': '100%'}
        if multi_select:
            dropdown_style['margin-bottom'] = '5px'

        dropdown = dcc.Dropdown(
            id=dropdown_id,
            options=options_formatted,
            style=dropdown_style,
            value=value,
            multi=multi_select
        )
        return dbc.Col([label, dropdown], style={'padding-left': 0}, width=12)

    def get_data(self):

        records = NanoporeRecord.objects.filter(user_id=self.user_id)
        self.records = records
        if not records.exists():
            return pd.DataFrame()  # Return an empty DataFrame if no records are found

        return pd.DataFrame.from_records(records.values())

    def calculate_normalized_counts(self):
        counts_df = pd.DataFrame.from_records(NanoporeRecord.objects.filter(user_id=self.user_id).values())
        stats_df = pd.DataFrame.from_records(SequencingStatistics.objects.filter(user_id=self.user_id).values())


        # Merge the counts and stats dataframes on sample_id
        merged_df = pd.merge(counts_df, stats_df, left_on='sample_id', right_on="sample_name")

        # Calculate normalized counts by dividing each count by the numebr of bases sequenced and then multiplying by
        # 1 million to make normalized counts more similar to normal counts in value range
        merged_df['normalized_count'] = (merged_df['count'] / merged_df['total_bases_sequenced']) * 10000000

        # Selecting only necessary columns for the final DataFrame
        normalized_counts_df = merged_df[['sample_id', 'taxonomy', 'abundance', 'count', 'normalized_count']]
        return normalized_counts_df
