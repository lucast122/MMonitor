import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_mantine_components as dmc
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import skbio.diversity
from dash import html, dcc
from dash_iconify import DashIconify
from django_plotly_dash import DjangoDash
from skbio import DistanceMatrix
from skbio.diversity import beta_diversity
from skbio.stats import ordination
from skbio.stats.ordination import pcoa

from users.models import NanoporeRecord, SequencingStatistics


# Convert DistanceMatrix to DataFrame for heatmap plotting
def distance_matrix_to_dataframe(distance_matrix):
    # Convert to a square matrix and then to a DataFrame
    matrix_df = pd.DataFrame(distance_matrix.data,
                             index=distance_matrix.ids,
                             columns=distance_matrix.ids)
    return matrix_df


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
        self.alpha_fig1 = None
        self.alpha_fig2 = None
        self.beta_fig1 = None
        self.beta_fig2 = None

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
        self.plot_ids = ['alpha_diversities_plot1', 'alpha_diversities_plot2', 'beta_diversity_heatmap',
                         'pcoa_plot_container']

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
        self.diversity_metric = None
        self._init_layout()

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

                 dcc.Graph(id='beta_diversity_heatmap',
                           figure=self.create_beta_diversity_heatmap(self.unique_sample_ids)),
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

        download_button = dmc.Button("Download alpha diversity CSV", id="btn-download-diversity",
                                     style={'margin-top': '20px', 'margin-left': '20px'},
                                     leftIcon=DashIconify(icon="foundation:page-export-csv"))

        svg_download_button = dmc.Button("Download all plots as SVG", id="btn-download-svg-diversity",
                                         style={'margin-top': '20px', 'margin-left': '10px'},
                                         leftIcon=DashIconify(icon="bi:filetype-svg"))
        svg_download_component = dcc.Download(id="download-svg-diversity")

        download_component = dcc.Download(id="download-diversity-csv")

        sample_select_dropdown = dbc.Col(
            [dmc.Text("Samples to plot:", className='text-primary my-2', id='sample_select_text',
                      style={'width': '100%'}), dcc.Dropdown(
                id='sample_select_value',
                options=[{'label': i, 'value': i} for i in self.unique_sample_ids] if self.unique_sample_ids else [
                    {'label': 'Default', 'value': 'Default'}],
                multi=True,
                style={'width': '100%', 'margin-bottom': '5px', 'margin-top': '10px', 'margin-bot': '5px'},
                value=self.unique_sample_ids
            )], style={"padding-left": "0px"})

        # Main container

        container = dbc.Container(
            [sample_select_dropdown,
             dropdown_container,
             download_button,
             svg_download_button,
             svg_download_component,
             download_component,

             graph_container,
             create_colour_by_menu()

             ],
            fluid=True, style={}, className="dbc dbc-ag-grid"
        )
        self.app.layout = container

    """Randomly subsample a sample to a specified depth."""

    def calculate_alpha_diversity(self, use_rarefaction=False, use_normalized_counts=False):

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
        dm = beta_diversity("braycurtis", self.df_full_for_diversity, sorted(self.unique_sample_ids))
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
        # print(f"clean_dm: {clean_dm}")
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
        df = pd.DataFrame.from_records(records.values())
        df_sorted = df.sort_values(by=['project_id', 'subproject', 'sample_id'])
        return df_sorted

    def calculate_normalized_counts(self):
        counts_df = pd.DataFrame.from_records(NanoporeRecord.objects.filter(user_id=self.user_id).values())
        stats_df = pd.DataFrame.from_records(SequencingStatistics.objects.filter(user_id=self.user_id).values())
        print(f"stats_df {stats_df}")

        # Merge the counts and stats dataframes on sample_id
        merged_df = pd.merge(counts_df, stats_df, left_on='sample_id', right_on="sample_name")

        # Calculate normalized counts by dividing each count by the numebr of bases sequenced and then multiplying by
        # 1 million to make normalized counts more similar to normal counts in value range
        merged_df['normalized_count'] = (merged_df['count'] / merged_df['total_bases_sequenced']) * 10000000

        # Selecting only necessary columns for the final DataFrame
        normalized_counts_df = merged_df[['sample_id', 'taxonomy', 'abundance', 'count', 'normalized_count']]
        return normalized_counts_df

    def create_alpha_diversity_plots(self, sample_select_value, alpha_diversity_metric):
        if alpha_diversity_metric == "Simpson":
            diversity_df = self.simpson_diversity.reset_index()
            diversity_df_without_categories = self.simpson_diversity.reset_index()
        else:
            diversity_df = self.shannon_diversity.reset_index()
            diversity_df_without_categories = self.shannon_diversity.reset_index()
        diversity_df.columns = ['sample_id', f"{alpha_diversity_metric}Diversity"]
        diversity_df_without_categories.columns = ['sample_id', f"{alpha_diversity_metric}Diversity"]
        # print(diversity_df_without_categories)
        diversity_df_selected = diversity_df_without_categories[
            diversity_df_without_categories['sample_id'].astype(str).isin(sample_select_value)]
        diversity_df['Project'] = diversity_df['sample_id'].map(self.sample_to_project_dict)

        fig = px.box(diversity_df, x='Project', y=f"{alpha_diversity_metric}Diversity",
                     title=f'Alpha Diversity ({alpha_diversity_metric} Index) across Sample Categories')

        fig2 = px.line(diversity_df_selected, x="sample_id", y=f"{alpha_diversity_metric}Diversity",
                       title=f'Alpha Diversity ({alpha_diversity_metric} Index) across selected samples')
        self.diversity_metric = alpha_diversity_metric
        fig['layout']['plot_bgcolor'] = 'rgba(0,0,0,0)'
        fig2['layout']['plot_bgcolor'] = 'rgba(0,0,0,0)'
        layout = dict(
            xaxis=dict(tickfont=dict(size=14)),  # Adjust font size if needed
            yaxis=dict(tickmode='array', tickfont=dict(size=14)),
        )
        fig.update_layout(layout)
        fig2.update_layout(layout)

        self.alpha_fig1, self.alpha_fig2 = fig, fig2

        return fig, fig2

    def create_beta_pcoa_figure(self, selected_samples, toggle_3d, project_clicks, subproject_clicks, kmeans_clicks,
                                sample_date_clicks, k_value):
        # Default n_clicks to 0 if they are None
        project_clicks = project_clicks or 0
        subproject_clicks = subproject_clicks or 0
        kmeans_clicks = kmeans_clicks or 0
        sample_date_clicks = sample_date_clicks or 0

        dimensions = 3 if toggle_3d else 2
        # Convert the DistanceMatrix to a DataFrame if necessary
        distance_matrix_df = pd.DataFrame(
            self.beta_diversity_matrix.data,
            index=self.beta_diversity_matrix.ids,
            columns=self.beta_diversity_matrix.ids
        )
        if selected_samples:
            distance_matrix_df = distance_matrix_df.loc[selected_samples, selected_samples]

        # Now perform PCoA with skbio - this needs to be done after each filter operation if the samples change
        pcoa_results = pcoa(distance_matrix_df)

        # Extract the PCoA scores
        pcoa_scores = pcoa_results.samples

        text_data = distance_matrix_df.columns

        # Determine coloring based on the last button clicked

        selected_sample_to_project_dict = {item['sample_id']: item['project_id'] for item in
                                           self.sample_project_mapping}

        selected_sample_to_subproject_dict = {item['sample_id']: item['subproject']
                                              for item in self.sample_subproject_mapping}

        # include only selected samples
        selected_sample_to_project_dict = {k: v for k, v in selected_sample_to_project_dict.items() if
                                           k in selected_samples}
        selected_sample_to_subproject_dict = {k: v for k, v in selected_sample_to_subproject_dict.items() if
                                              k in selected_samples}

        if (kmeans_clicks > project_clicks and kmeans_clicks > subproject_clicks and kmeans_clicks >
                sample_date_clicks):
            # Perform K-means clustering
            kmeans = KMeans(n_clusters=k_value, random_state=0).fit(pcoa_scores.iloc[:, :dimensions])
            pcoa_scores['ColorCategory'] = kmeans.labels_
            color = 'ColorCategory'
        elif project_clicks > subproject_clicks and project_clicks > sample_date_clicks:
            color = selected_sample_to_project_dict
        elif subproject_clicks > sample_date_clicks:
            color = selected_sample_to_subproject_dict
        else:
            color = self.sample_to_date_dict

        # Select the appropriate number of dimensions
        if dimensions == 3:
            fig = px.scatter_3d(
                pcoa_scores,
                x='PC1',
                y='PC2',
                z='PC3',
                text=text_data,  # Add sample names as hover text
                labels={'PC1': 'PC1', 'PC2': 'PC2', 'PC3': 'PC3'},
                title="3D PCoA Plot of inter sample beta diversity",
                color=color
            )
        else:  # Default to 2D
            fig = px.scatter(
                pcoa_scores,
                x='PC1',
                y='PC2',
                text=text_data,  # Add sample names as hover text
                labels={'PC1': 'PC1', 'PC2': 'PC2'},
                title="2D PCoA Plot of inter sample beta diversity",
                color=color
            )

        # Customize the figure as needed
        fig.update_traces(marker=dict(size=10), textposition="top center",
                          selector=dict(mode='markers+text'))  # Adjust marker size as needed
        fig.update_layout(margin=dict(l=0, r=0, b=0, t=100))
        fig.update_layout(width=1600, height=1000, font=dict(size=14))
        fig['layout']['plot_bgcolor'] = 'rgba(0,0,0,0)'
        self.beta_fig2 = fig
        return fig

    def create_beta_diversity_heatmap(self, selected_samples):
        # Convert the DistanceMatrix to a DataFrame first
        beta_matrix_df = distance_matrix_to_dataframe(self.beta_diversity_matrix)

        # Now you can use .loc since beta_matrix_df is a DataFrame
        if selected_samples:
            # Filter the DataFrame based on selected samples
            filtered_matrix = beta_matrix_df.loc[selected_samples, selected_samples]
        else:
            filtered_matrix = beta_matrix_df  # Use the full DataFrame if no samples are selected

        # Create the heatmap
        fig = go.Figure(data=go.Heatmap(
            z=filtered_matrix,
            # labels=dict(x="Sample", y="Sample", color="Beta Diversity"),
            x=filtered_matrix.columns,
            y=[f'{elem} ' for elem in filtered_matrix.columns],
            hoverongaps=False,
            colorscale='Balance'
        ))

        # Update layout for better readability and aesthetics
        fig.update_layout(
            title="Beta Diversity Heatmap",
            xaxis=dict(tickangle=-90, tickfont=dict(size=14)),  # Adjust font size if needed
            yaxis=dict(type='category', automargin=True, tickfont=dict(size=14)),
            # Adjust font size if needed
            coloraxis_colorbar=dict(title="Diversity Score"),
            width=1600,  # Adjust the width
            height=1300,  # Adjust the height
            margin=dict(l=50, r=50, b=50, t=50)
        )
        self.beta_fig1 = fig
        return fig
