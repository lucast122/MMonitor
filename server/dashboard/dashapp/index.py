import base64
import json
import re
import sqlite3
import tempfile
from io import StringIO
from json import loads
from typing import Tuple, Any, List, Iterable, Dict, Union
from skbio.stats.ordination import pcoa
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash_extensions import Lottie
from dash import dcc, html
from dash.dependencies import Input, Output

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
from dash_bootstrap_templates import load_figure_template
from dash_extensions import WebSocket
from django_plotly_dash import DjangoDash
from natsort import natsorted
from pandas import DataFrame
from plotly.graph_objects import Figure
from scipy.ndimage.filters import gaussian_filter
from scipy.stats import zscore
from statsmodels.nonparametric.smoothers_lowess import lowess

from users.models import NanoporeRecord
from users.models import SequencingStatistics
from . import taxonomy, correlations, qc, diversity, horizon
from .calculations.stats import scipy_correlation


# def _init_mysql(user_id):



def _explode_metadata(df):
    return pd.concat([df, df['data'].apply(_parse_dict)], axis=1).drop(columns='data')

def _parse_dict(x):
    return pd.Series(loads(x))



class Index:
    """
    Landing page of the dash application.
    Contains navigation to the various application pages.
    """

    def __init__(self, user_id):
        self.user_id = user_id
        self.sample_ids = None
        print(user_id)
        self.app = DjangoDash('Index', add_bootstrap_links=True)
        color_map = plt.get_cmap('tab20')  # 'tab20' is a colormap with 20 distinct colors
        colors = color_map.colors
        self.colors = colors

        self.taxonomy_app = taxonomy.Taxonomy(user_id)
        self.diversity_app = diversity.Diversity(user_id)
        self.correlations_app = correlations.Correlations()
        self.horizon_app = horizon.Horizon(user_id)


        self.qc_app = qc.QC(user_id)
        self.diversity_metric = None

        pd.set_option('display.max_columns', None)
        pd.set_option('display.max_rows', None)

        # Get the session key from the cookie
        # session_key = flask.request.cookies.get(settings.SESSION_COOKIE_NAME)

        # Get the session
        # session = Session.objects.get(session_key=session_key)

        # Get the user ID from the session
        user_id=self.user_id
        # user_id = session.get_decoded().get('_auth_user_id')

        self._heatmap_df = None
        self._table_df = None
        records = NanoporeRecord.objects.filter(user_id=user_id)

        # bootstrap templates for styling plots
        templates = [
            "bootstrap",
            "minty",
            "pulse",
            "flatly",
            "quartz",
            "cyborg",
            "darkly",
            "vapor",
        ]

        load_figure_template(templates)

        self.df = pd.DataFrame.from_records(records.values())
        self.df.replace("Not available", np.nan, inplace=True)
        self.df.dropna(inplace=True)

        self.meta_df = self.correlations_app.get_all_meta()
        self.df['sample_id'] = self.df['sample_id'].astype(str)

        self.meta_df['sample_id'] = self.meta_df['sample_id'].astype(str)
        self.df_merged = self.df.merge(self.meta_df, on="sample_id", how="left")

        self.metadata_columns = self.meta_df.columns.tolist()

        self.hover_data = {column: True for column in self.metadata_columns}
        self.metadata_columns.pop(0)
        self.unique_sample_ids = records.values('sample_id').distinct()
        self.unique_sample_ids = [item['sample_id'] for item in self.unique_sample_ids]
        # Initialize apps

        # simple_app = simple.SimpleApp()
        # kraken_app = kraken.Kraken()



        self._apps = {
        '/dashapp/taxonomy': {
                'name': 'Taxonomy',
                'app': self.taxonomy_app.app,
                'instance': self.taxonomy_app
            },
        # '/dashapp/horizon': {
        #     'name': 'Horizon',
        #     'app': self.horizon_app.app,
        #     'instance': self.horizon_app
        # },

            '/dashapp/diversity': {
                'name': 'Diversity',
                'app': self.diversity_app.app,
                'instance': self.diversity_app
            },
            '/dashapp/correlations': {
                'name': 'Correlations',
                'app': self.correlations_app.app,
                'instance': self.correlations_app
            },
            '/dashapp/qc': {
                'name': 'QC',
                'app': self.qc_app.app,
                'instance': self.qc_app
            }


            # '/dashapp/kegg': {
            #     'name': 'Metabolic Maps',
            #     'app': correlations_app.app,
            #     'instance': correlations_app
            # },
            #     '/dashapp/kraken': {
            #     'name': 'Kraken Taxonomy',
            #     'app': kraken_app.app,
            #     'instance': kraken_app
            # },
        }

        # Initialize Index layout
        self._init_layout()
        self.app.layout = self.layout
        print("Initialized Index layout")
        self.taxonomy_app._init_layout()
        

        # Initialize callbacks for each app
        # for app_info in self._apps.values():
        #     print(f"Initializing callbacks for {app_info['name']} app")
        #     app_info['instance']


        # Initialize Index callbacks
        self._init_callbacks()
        print("Initialized Index callbacks")



    # def _init_apps(self) -> None:
    #     """
    #     Register apps by their urls, names and instances.
    #     This is the only place you need to add an app.
    #     """
        


    def _init_layout(self) -> None:
        """
        The index page's layout consists of the app navigation and
        the currently selected app's page content.
        """

        location = dcc.Location(id='url', refresh=True)
        navigation = html.Div([
            dcc.Link(values['name'], href=url, style={'padding': '15px 25px', 'font-size': "16px", 'color':'white'})
            for url, values in self._apps.items()
        ], className="row",style={'margin-left': '0px','backgroundColor':'#15242B'})
        page_content = html.Div(id='page-content', children=[],style={'backgroundColor':'#f5f7fa'})
        # graph1 = dcc.Graph(id='graph1', figure={'data': []})



        container = html.Div([location, navigation, page_content], style={'backgroundColor': '#f5f7fa'},
                             className="dbc dbc-ag-grid")

        self.layout = container

    """
    Taxonomy app helper functions
    """

    def plot_pseudo_horizon(self,df):
        # Create gaussian filtered data to imitate horizonplot look
        smooth_data = gaussian_filter(df['abundance'], sigma=1)

        # Create the heatmap
        heatmap = go.Heatmap(
            z=smooth_data,
            x=df['sample_id'],
            colorscale='RdYlBu',
        )
        return heatmap

    def plot_stacked_bar(self, df, use_date_value, taxonomic_rank):
        # Group and sum the data based on the x-axis and the taxonomic rank
        if use_date_value:
            x_axis = "date"
        else:
            x_axis = "sample_id"

        grouped_df = df.groupby([x_axis, taxonomic_rank])['abundance'].sum().reset_index()

        # Plotting the data
        if use_date_value:
            fig1 = px.bar(grouped_df, x="date", y="abundance", color=taxonomic_rank, barmode="stack",

                          category_orders={"date": sorted(df["date"].unique())})
        else:
            fig1 = px.bar(grouped_df, x="sample_id", y="abundance", color=taxonomic_rank, barmode="stack",
                          template='bootstrap',

                          category_orders={"sample_id": sorted(df["sample_id"].unique(), key=self.split_alphanumeric)})

        fig1 = go.Figure(fig1)
        # Set the customdata attribute for each trace (modify as needed to include the correct taxonomy information)
        # for trace in fig1.data:
        #     trace['customdata'] = df['taxonomy']

        fig1.update_layout(
            legend=dict(
                orientation="v",
                y=1,
                x=1.1
            ),
                clickmode='event+select',
            dragmode='lasso',

            margin=dict(
                l=100,  # Add left margin to accommodate the legend
                r=100,  # Add right margin to accommodate the legend
                b=100,  # Add bottom margin
                t=100  # Add top margin
            ),
            autosize=True
            
        )

        fig2_style = {'display': 'None'}
        markdown_style = {'display': 'none'}
        # fig2 = px.bar(df, x="taxonomy", y="abundance", color="sample_id", barmode="stack",hover_data=self.hover_data)
        return fig1

    def plot_heatmap(self, df, use_date_value, taxonomic_rank):
        x_axis = "date" if use_date_value else "sample_id"
        grouped_df = df.groupby([x_axis, taxonomic_rank])['abundance'].sum().reset_index()

        fig = go.Figure(data=go.Heatmap(
            z=grouped_df['abundance'],
            x=grouped_df[x_axis],
            y=grouped_df[taxonomic_rank],
            colorscale='Viridis'))

        return fig

    def plot_line(self, df, use_date_value, taxonomic_rank):
        x_axis = "date" if use_date_value else "sample_id"
        grouped_df = df.groupby([x_axis, taxonomic_rank])['abundance'].sum().reset_index()
        fig1 = px.line(grouped_df, x=x_axis, y="abundance", color=taxonomic_rank, template='bootstrap'
                       )
        return fig1


    def plot_grouped_bar(self, df, use_date_value, taxonomic_rank):
        x_axis = "date" if use_date_value else "sample_id"
        grouped_df = df.groupby([x_axis, taxonomic_rank])['abundance'].sum().reset_index()
        fig1 = px.bar(grouped_df, x=x_axis, y="abundance", color=taxonomic_rank, template='bootstrap')
        return fig1

    def plot_scatter(self, df, use_date_value, taxonomic_rank):
        x_axis = "date" if use_date_value else "sample_id"
        grouped_df = df.groupby([x_axis, taxonomic_rank])['abundance'].sum().reset_index()
        fig1 = px.scatter(grouped_df, x=x_axis, y="abundance", size="abundance", color=taxonomic_rank
                          )
        return fig1

    def plot_area(self, df, use_date_value, taxonomic_rank):
        x_axis = "date" if use_date_value else "sample_id"
        grouped_df = df.groupby([x_axis, taxonomic_rank])['abundance'].sum().reset_index()
        fig1 = px.area(grouped_df, x=x_axis, y="abundance", color=taxonomic_rank, line_group=taxonomic_rank,
                       template='bootstrap')
        return fig1

    def plot_scatter_3d(self, df, taxonomic_rank):
        # Plotting code for scatter 3D goes here...
        fig1 = px.scatter_3d(df, x='taxonomy', y='abundance', z='sample_id', color=taxonomic_rank, template='bootstrap')
        # fig2 = px.scatter_3d(df, x='abundance', y='taxonomy', z='sample_id', color='abundance',hover_data=self.hover_data)
        return fig1

    def plot_pie(self, df, sample_value_piechart, taxonomic_rank):
        filtered_df = df[df["sample_id"] == sample_value_piechart]
        aggregated_df = filtered_df.groupby(taxonomic_rank)['abundance'].sum().reset_index()
        fig1 = px.pie(aggregated_df, values='abundance', names=taxonomic_rank,
                      title=f'Pie chart of bioreactor taxonomy of sample {sample_value_piechart}')
        piechart_style = {'display': 'block'}
        return fig1, piechart_style

    def split_alphanumeric(self,text):
        matches = re.findall(r'(\d+|\D+)', text)
        numbers = [int(m) for m in matches if m.isdigit()]
        non_numbers = [m for m in matches if not m.isdigit()]
        number = numbers[0] if numbers else float('inf')
        non_number = non_numbers[0] if non_numbers else ''
        return (number, non_number)

    """
    ---------- Index callback index callback ---------------------
    """

    def _init_callbacks(self) -> None:
        @self.app.callback(
            Output('page-content', 'children'),
            Input('url', 'pathname')
        )
        def display_page(pathname) -> html:

            """
            Change page content to the selected app
            if the url is valid.
            """

            # empty urls have no effect
            if pathname is None or pathname == '/':
                raise PreventUpdate
            # attempt to change to selected app
            if pathname in self._apps:
                app = self._apps[pathname]['instance']

                app._init_layout()  # ensure layout is initialized
                # app._init_callbacks()  # ensure callbacks are registered
                return app.app.layout
            # otherwise it's page not found
            else:
                return "Please select an app from the menu above."
                #
            @self.app.callback(
            Output('graph1', 'figure'),
            Input('group-selection-dropdown', 'value'),
            Input('group-storage', 'data'),
            State('graph1', 'figure')
            )
            def update_plot(selected_group, data, figure):
                if selected_group is None or data is None or figure is None or figure['data'] is None:
                    raise PreventUpdate

                if selected_group not in data:
                    raise PreventUpdate

                selected_taxa = data[selected_group]

                # Update the plot to show only the selected taxa
                figure['data'] = [trace for trace in figure['data'] if 'customdata' in trace and trace['customdata'] and trace['customdata'][0] in selected_taxa]

                return figure



        # UPLOAD SQLITE CALLBACK
        @self.app.callback(
            Output('sample_select_value', 'children'),
            # You can define an output to display a message or feedback to the user
            Input('upload-sqlite', 'contents'),
            State('upload-sqlite', 'filename')
        )
        def upload_sqlite(contents, filename):
            print("Sqlite3 file uploaded")
            if contents is None:
                return

            content_type, content_string = contents.split(',')
            decoded = base64.b64decode(content_string)

            # Write the decoded contents to a temporary file
            with tempfile.NamedTemporaryFile(delete=True) as temp_file:
                temp_file.write(decoded)
                temp_file.flush()

                # Connect to the temporary SQLite database file
                with sqlite3.connect(temp_file.name) as conn:
                    df = pd.read_sql_query("SELECT * FROM mmonitor", conn)

                    # Convert the DataFrame to NanoporeRecord instances
                    for _, row in df.iterrows():
                        record = NanoporeRecord(
                            taxonomy=row['taxonomy'],
                            abundance=row['abundance'],
                            sample_id=row['sample_id'],
                            project_id=row['project_id'],
                            user_id=self.user_id  # Assuming you've the user_id stored in the Index class
                        )
                        record.save()

                return f"File {filename} processed successfully."

        """
TAXONOMY callbacks -----  Taxonomy callbacks ----- Taxonomy callbacks ----- Taxonomy callbacks ----- Taxonomy callbacks ----- 
        """

        from dash_bootstrap_templates import ThemeChangerAIO
        @self.app.callback(
            Output("sample_select_value", "value"),
            [Input("project-dropdown", "value"),
             Input("subproject-dropdown", "value")]
        )
        def select_samples_by_project_and_subproject(selected_project, selected_subproject):
            global trigger_id
            ctx = dash.callback_context

            if not ctx.triggered:
                return self.unique_sample_ids
            else:
                trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

            if trigger_id == "project-dropdown":
                if selected_project == "ALL":
                    # If 'All Projects' is selected, don't filter by project_id
                    filtered_df = self.df_merged
                else:
                    filtered_df = self.df_merged[self.df_merged['project_id'] == selected_project]

            elif trigger_id == "subproject-dropdown":
                if selected_subproject == "ALL":
                    # If 'All Subprojects' is selected, don't filter by subproject
                    filtered_df = self.df_merged
                else:
                    filtered_df = self.df_merged[self.df_merged['subproject'] == selected_subproject]

            else:
                return []

            unique_sample_ids = filtered_df['sample_id'].unique().tolist()
            return unique_sample_ids

        @self.app.callback(
            Output('graph1', 'figure'),
            Output('number_input_piechart', 'style'),
            # Output('markdown-caption','style'),
            Input('dropdown', 'value'),
            Input('tax_rank_dropdown', 'value'),
            Input('number_input_piechart', 'value'),
            Input('slider', 'value'),
            Input('sample_select_value', 'value'),
            Input('use_date_value', 'value')
        )
        def plot_selected_taxonomy(value, taxonomic_rank, sample_value_piechart, slider_value, sample_select_value,
                                 use_date_value):
            # Simplified initialization
            fig1 = {'data': []}
            piechart_style = {'display': 'none'}
            self.df_merged.needs_processing = True
            # Check if sorting and duplicate removal is necessary
            if self.df_merged.needs_processing:  # Replace with appropriate condition
                self.df_merged.drop_duplicates(
                    subset=['sample_id', 'abundance', 'taxonomy', 'project_id', 'subproject', 'user_id', 'date'],
                    inplace=True)
                sorted_sample_ids = natsorted(self.df_merged['sample_id'].unique(), key=self.split_alphanumeric)
                self.sample_ids = sorted_sample_ids
                self.df_sorted = self.df_merged.set_index('sample_id').loc[sorted_sample_ids].reset_index()
                self.df_merged.needs_processing = False  # Flag to prevent reprocessing

            # Efficient grouping and filtering
            self.df_selected = self.df_sorted[self.df_sorted['sample_id'].astype(str).isin(sample_select_value)]
            self.df_selected = self.df_selected.groupby('sample_id').head(slider_value).reset_index(drop=True)

            # Mapping of plot types to functions
            plot_functions = {
                'stackedbar': self.plot_stacked_bar,
                'line': self.plot_line,
                'groupedbar': self.plot_grouped_bar,
                'scatter': self.plot_scatter,
                'area': self.plot_area,
                'scatter3d': self.plot_scatter_3d,
                'pie': self.plot_pie,
                'horizon': self.plot_pseudo_horizon,
                'heatmap': self.plot_heatmap
            }

            # Select and execute the plotting function
            if value in plot_functions:
                fig1 = plot_functions[value](self.df_selected, use_date_value, taxonomic_rank) if value != 'pie' \
                    else plot_functions[value](self.result_df, sample_value_piechart, taxonomic_rank)[0]
                if value == 'pie':
                    piechart_style = {'display': 'block'}

            return fig1, piechart_style






        # Add a new callback that updates the header's style based on the dropdown's value
        @self.app.callback(
            Output('header_pie_chart_sample_select_dbc', 'style'),
            Input('dropdown', 'value')
        )
        def show_hide_element(value):
            if value == "pie":
                return {'display': 'block'}  # Show the header if 'pie' is selected
            else:
                return {'display': 'none'}  # Hide the header for other options

        @self.app.callback(
            Output("download-csv", "data"),
            [Input("btn-download", "n_clicks")]
        )
        def download_csv(n_clicks):
            if n_clicks is not None:
                # Create a sample DataFrame for demonstration

                # Convert DataFrame to CSV string
                csv_string = self.df_sorted.to_csv(index=False)

                # Create a BytesIO object to hold the CSV data
                csv_bytes = StringIO()
                csv_bytes.write(csv_string)

                # Seek to the beginning of the BytesIO stream
                csv_bytes.seek(0)

                # Base64 encode the CSV data
                csv_base64 = base64.b64encode(csv_bytes.read().encode()).decode()

                # Construct the download link
                csv_href = f"data:text/csv;base64,{csv_base64}"

                # Specify the filename for the download
                filename = "data.csv"

                # Return the download link and filename

                return dcc.send_data_frame(self.df_sorted.to_csv, filename=filename)

        @self.app.callback(
            Output("download-counts", "data"),
            [Input("btn-download-counts", "n_clicks")]
        )
        def download_counts(n_clicks):
            if n_clicks is not None:
                # Create a sample DataFrame for demonstration

                # Convert DataFrame to CSV string
                counts_df = self.taxonomy_app.calculate_normalized_counts()
                csv_string = counts_df.to_csv(index=False)
                # Create a BytesIO object to hold the CSV data
                csv_bytes = StringIO()
                csv_bytes.write(csv_string)
                # Seek to the beginning of the BytesIO stream
                csv_bytes.seek(0)
                # Base64 encode the CSV data
                csv_base64 = base64.b64encode(csv_bytes.read().encode()).decode()

                # Construct the download link
                csv_href = f"data:text/csv;base64,{csv_base64}"

                # Specify the filename for the download
                filename = "counts.csv"

                # Return the download link and filename
                return dcc.send_data_frame(counts_df.to_csv, filename=filename)

        # @self.app.callback(

        # Output('graph3', 'figure'),
        # Input('sample_select_value', 'value')
        # )
        # def update_diversity_graph(sample_select_value):
        #     # A list of all sample_ids to iterate over
        #     sample_ids = self.df_sorted['sample_id'].unique()

        #     # Values to hold calculated results
        #     richness_values = []
        #     evenness_values = []
        #     shannon_values = []

        #     for sample_id in self.taxonomy_app.unique_sample_ids:
        #         df_sample = self.df_sorted.loc[self.df_sorted['sample_id'] == sample_id]
                
        #         # calculating diversity measures
        #         richness_values.append(richness(df_sample))
        #         evenness_values.append(evenness(df_sample))
        #         shannon_values.append(shannon_diversity(df_sample))

        #     # creating figure
        #     fig = go.Figure()

        #     fig.add_trace(go.Scatter(x=sample_ids, y=richness_values, mode='lines', name='Richness'))
        #     fig.add_trace(go.Scatter(x=sample_ids, y=evenness_values, mode='lines', name='Evenness'))
        #     fig.add_trace(go.Scatter(x=sample_ids, y=shannon_values, mode='lines', name='Shannon Diversity'))

        #     fig.update_layout(
        #         title="Diversity Measures Across Samples",
        #         xaxis_title="Sample IDs",
        #         yaxis_title="Diversity Measure Value",
        #         legend_title="Diversity Measure",
        #     )

        #     return fig


        """

        DIVERSITY APP CALLBACKS     DIVERSITY APP CALLBACKS    DIVERSITY APP CALLBACKS   DIVERSITY APP CALLBACKS

        """

        # @self.app.callback(
        #     Output("loading-output-1", "children"),
        #     [Input('beta_diversity_3d_pcoa', "loading_state")]
        # )
        # def update_loading_state(loading_state):
        #     if loading_state.is_loading:
        #         # Show the Lottie animation when the graph is loading
        #         return [Lottie(options=options, width="10%", height="10%", url=url),
        #                 dcc.Graph(id='beta_diversity_3d_pcoa')]
        #     else:
        #         # Hide the Lottie animation when the graph is not loading
        #         return dcc.Graph(id='beta_diversity_3d_pcoa')

        @self.app.callback(
            Output('alpha_diversities_plot1', 'figure'),
            Output('alpha_diversities_plot2', 'figure'),
            Input('sample_select_value', 'value'),
            Input('diversity_metric_dropdown', 'value')
        )
        def plot_alpha_diversities(sample_select_value,alpha_diversity_metric):
            if alpha_diversity_metric == "Simpson":
                diversity_df = self.diversity_app.simpson_diversity.reset_index()
                diversity_df_without_categories = self.diversity_app.simpson_diversity.reset_index()
            else:
                diversity_df = self.diversity_app.shannon_diversity.reset_index()
                diversity_df_without_categories = self.diversity_app.shannon_diversity.reset_index()
            diversity_df.columns = ['sample_id', f"{alpha_diversity_metric}Diversity"]
            diversity_df_without_categories.columns = ['sample_id', f"{alpha_diversity_metric}Diversity"]
            print(diversity_df_without_categories)
            diversity_df_selected = diversity_df_without_categories[diversity_df_without_categories['sample_id'].astype(str).isin(sample_select_value)]
            diversity_df['Project'] = diversity_df['sample_id'].map(self.diversity_app.sample_to_project_dict)



            fig = px.box(diversity_df, x='Project', y=f"{alpha_diversity_metric}Diversity",
                         title=f'Alpha Diversity ({alpha_diversity_metric} Index) across Sample Categories')

            fig2 = px.line(diversity_df_selected,x="sample_id",y=f"{alpha_diversity_metric}Diversity",
                           title=f'Alpha Diversity ({alpha_diversity_metric} Index) across selected samples')
            self.diversity_metric = alpha_diversity_metric
            return fig,fig2

            # BETA DIVERSITY

        @self.app.callback(
        Output('pcoa_plot_container', 'figure'),
        Input('sample_select_value', 'value'),
        Input('toggle-3d', 'checked')
        )
        def generate_pcoa_figure(selected_samples, toggle_3d):
            dimensions=2
            if toggle_3d:
                dimensions=3
            # Convert the DistanceMatrix to a DataFrame if necessary
            distance_matrix_df = pd.DataFrame(
                self.diversity_app.beta_diversity_matrix.data,
                index=self.diversity_app.beta_diversity_matrix.ids,
                columns=self.diversity_app.beta_diversity_matrix.ids
            )
            if selected_samples:
                distance_matrix_df = distance_matrix_df.loc[selected_samples, selected_samples]

            # Now perform PCoA with skbio - this needs to be done after each filter operation if the samples change
            pcoa_results = pcoa(distance_matrix_df)

            # Extract the PCoA scores
            pcoa_scores = pcoa_results.samples


            text_data = selected_samples

            # Select the appropriate number of dimensions
            if dimensions == 3:
                fig = px.scatter_3d(
                    pcoa_scores,
                    x='PC1',
                    y='PC2',
                    z='PC3',
                    text=text_data,  # Add sample names as hover text
                    labels={'PC1': 'PC1', 'PC2': 'PC2', 'PC3': 'PC3'},
                    title="3D PCoA Plot of inter sample beta diversity"
                )
            else:  # Default to 2D
                fig = px.scatter(
                    pcoa_scores,
                    x='PC1',
                    y='PC2',
                    text=text_data,  # Add sample names as hover text
                    labels={'PC1': 'PC1', 'PC2': 'PC2'},
                    title="2D PCoA Plot of inter sample beta diversity"
                )

            # Customize the figure as needed
            fig.update_traces(marker=dict(size=6),textposition="top center",
                              selector=dict(mode='markers+text'))  # Adjust marker size as needed
            fig.update_layout(margin=dict(l=0, r=0, b=0, t=30))
            fig.update_layout(width=1600,height=900)

            return fig


        @self.app.callback(
            Output('beta_diversity_plot', 'figure'),
            [
                Input('sample_select_value', 'value')

            ]
        )
        def update_beta_diversity_plot(selected_samples):
            if not selected_samples:
                return {}  # Return an empty plot if no samples are selected

            # Filter the beta diversity matrix based on selected samples
            filtered_matrix = self.diversity_app.beta_diversity_matrix.filter(selected_samples)

            # Create a 2D ordination plot (like PCoA) using the filtered matrix
            # PCoA is a common way to visualize beta diversity
            # You can use skbio or other libraries to perform PCoA
            pcoa_results = pcoa(filtered_matrix)

            fig = px.scatter(
                x=pcoa_results.samples['PC1'],
                y=pcoa_results.samples['PC2'],
                text=selected_samples
            )
            fig.update_layout(title="Beta Diversity (PCoA)", xaxis_title="PC1", yaxis_title="PC2")
            return fig

        # 3D PCOA BETA DIVERISTY

        @self.app.callback(
            Output('beta_diversity_3d_pcoa', 'figure'),
            [Input('sample_select_value', 'value')]
        )
        # def update_beta_diversity_3d_pcoa(selected_samples):
        #     if not selected_samples:
        #         return {}  # Return an empty plot if no samples are selected
        #
        #     # Filter the PCoA results for the selected samples
        #     filtered_samples = self.diversity_app.pcoa_results.samples.loc[selected_samples]
        #
        #     # Make sure to use the correct column names for x, y, z
        #     fig = px.scatter_3d(
        #         filtered_samples,
        #         x='PC1',  # First principal coordinate
        #         y='PC2',  # Second principal coordinate
        #         z='PC3',  # Third principal coordinate
        #         text=selected_samples,
        #         labels={'PC1': 'PC1', 'PC2': 'PC2', 'PC3': 'PC3'}
        #     )
        #     fig.update_layout(
        #         title="3D PCoA Plot of Beta Diversity",
        #         scene=dict(
        #             xaxis_title='PC1',
        #             yaxis_title='PC2',
        #             zaxis_title='PC3'
        #         )
        #     )
        #     return fig

        @self.app.callback(
            Output('alpha_diversity_boxplot', 'figure'),
            [Input('diversity_metric_dropdown', 'value'),
             Input('project-dropdown', 'value')]
        )
        def update_alpha_diversity_boxplot(selected_metric, selected_project):
            # filter data based on the selected project and metric
            # For demonstration purposes, let's assume `df` is your DataFrame that contains the alpha diversity data
            # and `project_column` is the name of the column that contains the project information.

            if selected_metric == 'Shannon':
                diversity_data = self.diversity_app.shannon_diversity
            else:
                diversity_data = self.diversity_app.simpson_diversity

            # If a specific project is selected, filter for that project
            if selected_project and selected_project != 'ALL':
                diversity_data = diversity_data[diversity_data['project_id'] == selected_project]

            # Create the box plot
            fig = px.box(diversity_data, y=selected_metric, color='project_id', labels={'y': selected_metric})

            return fig

        @self.app.callback(
            Output('beta_diversity_heatmap', 'figure'),
            [Input('sample_select_value', 'value')]
        )
        def update_beta_diversity_heatmap(selected_samples):
            # Convert the DistanceMatrix to a DataFrame first
            beta_matrix_df = distance_matrix_to_dataframe(self.diversity_app.beta_diversity_matrix)

            # Now you can use .loc since beta_matrix_df is a DataFrame
            if selected_samples:
                # Filter the DataFrame based on selected samples
                filtered_matrix = beta_matrix_df.loc[selected_samples, selected_samples]
            else:
                filtered_matrix = beta_matrix_df  # Use the full DataFrame if no samples are selected

            # Create the heatmap
            fig = px.imshow(
                filtered_matrix,
                labels=dict(x="Sample", y="Sample", color="Beta Diversity"),
                x=filtered_matrix.columns,
                y=filtered_matrix.columns,
                color_continuous_scale='balance'  # Feel free to choose a different color scale
            )

            # Update layout for better readability and aesthetics
            fig.update_layout(
                title="Beta Diversity Heatmap",
                xaxis=dict(tickangle=-90, tickfont=dict(size=8)),  # Adjust font size if needed
                yaxis=dict(tickmode='array', tickvals=filtered_matrix.index, tickfont=dict(size=7)),
                # Adjust font size if needed
                coloraxis_colorbar=dict(title="Diversity Score"),
                width=1600,  # Adjust the width
                height=900,  # Adjust the height
                margin=dict(l=50, r=50, b=50, t=50)
            )

            return fig



        # Convert DistanceMatrix to DataFrame for heatmap plotting
        def distance_matrix_to_dataframe(distance_matrix):
            # Convert to a square matrix and then to a DataFrame
            matrix_df = pd.DataFrame(distance_matrix.data,
                                     index=distance_matrix.ids,
                                     columns=distance_matrix.ids)
            return matrix_df

        @self.app.callback(
            Output("download-diversity-csv", "data"),
            [Input("btn-download-diversity", "n_clicks")]
        )
        def download_diversity_csv(n_clicks):

            if n_clicks is not None:
                # Convert DataFrame to CSV string
                if self.diversity_metric == "Shannon":
                    df = self.diversity_app.shannon_diversity
                    csv_string = self.diversity_app.shannon_diversity.to_csv(index=False)
                else:
                    df = self.diversity_app.simpson_diversity
                    csv_string = self.diversity_app.simpson_diversity.to_csv(index=False)

                # Create a BytesIO object to hold the CSV data
                csv_bytes = StringIO()
                csv_bytes.write(csv_string)

                # Seek to the beginning of the BytesIO stream
                csv_bytes.seek(0)

                # Base64 encode the CSV data
                csv_base64 = base64.b64encode(csv_bytes.read().encode()).decode()

                # Construct the download link
                csv_href = f"data:text/csv;base64,{csv_base64}"

                # Specify the filename for the download
                filename = f"alpha_diversity_{self.diversity_metric}.csv"

                # Return the download link and filename
                return dcc.send_data_frame(df.to_csv, filename=filename)

        """

        CORRELATIONS APP CALLBACKS     CORRELATIONS APP CALLBACKS    CORRELATIONS APP CALLBACKS   CORRELATIONS APP CALLBACKS

        """






        @self.app.callback(
        Output('graph-score', 'figure'),
        Output('graph-test', 'figure'),
        Input('taxonomy-dd', 'value'),
        Input('methods-dd', 'value'),
        Input('tests-dd', 'value')
        )
        def _update_graphs(tax: str, method: str, test: str) -> Tuple[Figure, Figure]:
            species = [x for x in tax] if tax else []

            if not species:  # add this condition to handle empty list
                return None, None, None, None, None, None

            """
            Populate the correlations and probability graphs
            according to dropdown selections.
            """
            # print(f"species in method: _update_graphs {species}")
            # print(f"taxonomy in method _update_graphs: {taxonomy}")
            # request data from database and filter columns containing metadata
            # abundance and metadata tables are joined to align entries by their sample_ids
            # print("this is species in _update_graphs")
            # print(species)
            species = replace_brackets(species)
            species_str = species[0] if species else None

            # print(f"species string before")
            # print(species_str)

            species_str = replace_brackets(species_str)
            # print(f"species string after")
            # print(species_str)
            df = self.get_abundance_meta_by_taxonomy(species_str)
            # metadata_columns = [col for col in df.columns if col not in ['sample_id', 'abundance', 'meta_id', 'project_id']]

            # for each metadata calculate the correlation and probability
            # transpose the list of tuples and extract each a correlation and a probability list:
            # [(c1, p1), (c2, p2), (c3, p3), ...] -> [c1, c2, c3, ...], [p1, p2, p3, ...]
            

            # print(df[meta])
            # print(test)
            # print(method)
            # print("METADATA COLUMNS")
            # print(self.metadata_columns)
            # print("DF")
            # print(species)
            # print(df)

            # y_axis_tuple = None
            # try:
            y_axis_tuple = None

            y_axis_tuple = [scipy_correlation(df['abundance'], df[meta], test, method) for meta in self.metadata_columns]






            # print("df[meta]")
            # print(df[meta])

            # print("metadata_columns")
            # print(self.metadata_columns)


            # print(y_axis_tuple)
            

            y_axis_score, y_axis_test = zip(*y_axis_tuple)
            y_axis_test = [xs[test] for xs in y_axis_test]


            # generate plots
            fig_score = px.scatter(x=self.metadata_columns, y=y_axis_score, labels={'x': 'Metric', 'y': f'{method} Score'})
            fig_test = px.scatter(x=self.metadata_columns, y=y_axis_test, labels={'x': 'Metric', 'y': f'{test} Score'})

            return fig_score, fig_test

        @self.app.callback(
            Output('table-correlations', 'columns'),
            Output('table-correlations', 'data'),
            Output('taxonomy-dd-tb', 'value'),
            Input('apply-btn-tb', 'n_clicks'),
            Input('select-all-btn-tb', 'n_clicks'),
            Input('clear-selection-btn-tb', 'n_clicks'),
            State('taxonomy-dd-tb', 'value'),
            State('methods-dd-tb', 'value'),
            State('tests-dd-tb', 'value'),
            State('table-correlations', 'columns'),
            State('table-correlations', 'data'),
        )
        def _update_table(x: int, y: int, z: int,
                      taxonomies: Union[str, List[str]],
                      methods: Union[str, List[str]],
                      tests: Union[str, List[str]],
                      tb_columns: Any,
                      tb_data: Any,
                      ) -> Tuple[Iterable, Dict, List]:
            """
            Populate the data table with correlation scores and their probabilities
            according to the dropdown selections. This table contains data more suited
            for higher dimensions, but in order to keep it displayable and exportable
            it is complexly condensed into two dimensions.

            The final dataframe/table will have this form:

            Taxonomy  | Method or Test    | Meta1  | Meta2  | Meta3  | ...
            ---------------------------------------------------------------
            taxonomy1 | Pearson           | score1 | score2 | score3 | ...
            taxonomy1 | Pearson T-Test    | score1 | score2 | score3 | ...
            taxonomy1 | Pearson Bootstrap | score1 | score2 | score3 | ...
            taxonomy1 | Kendall           | score1 | score2 | score3 | ...
            taxonomy1 | Kendall T-Test    | score1 | score2 | score3 | ...
            taxonomy1 | Kendall Bootstrap | score1 | score2 | score3 | ...
            taxonomy2 | Pearson           | score1 | score2 | score3 | ...
            taxonomy2 | Pearson T-Test    | score1 | score2 | score3 | ...
            taxonomy2 | Pearson Bootstrap | score1 | score2 | score3 | ...
            taxonomy2 | Kendall           | score1 | score2 | score3 | ...
            taxonomy2 | Kendall T-Test    | score1 | score2 | score3 | ...
            taxonomy2 | Kendall Bootstrap | score1 | score2 | score3 | ...
            ...
            """

                # figure out which button was clicked
                # default behaviour is 'apply'
            ctx = dash.callback_context
            button_id = 'apply-btn-tb'
            if ctx.triggered:
                button_id = ctx.triggered[0]['prop_id'].split('.')[0]

            # keep table, adjust selection in taxonomies dropdown menu
            if button_id == 'select-all-btn-tb':
                return tb_columns, tb_data, taxonomies
            elif button_id == 'clear-selection-btn-tb':
                return tb_columns, tb_data, []

            # format dropdown selections and eject if selections are invalid
            taxonomies: List[str] = _force_list(taxonomies)
            methods: List[str] = _force_list(methods)
            tests: List[str] = _force_list(tests)
            if len(taxonomies) == 0 or len(methods) == 0:
                raise PreventUpdate

            # request data from database and filter for metadata columns
            
            meta_cols = [meta for meta in self.meta_df.columns if meta != 'sample_id']

            # prepare the resulting dataframe/table
            columns = ['Taxonomy', 'Method or Test', *meta_cols]
            df = DataFrame(columns=columns, index=None)
            heatmap_df = pd.DataFrame(columns=['taxonomy'] + [f"{method}_{meta}" for method in methods for meta in meta_cols])

            # print(heatmap_df)


            # print("Initial Heatmap DF:\n", heatmap_df)

            # for each selected taxonomy
            for tax in taxonomies:

                # request corresponding abundances from database
                tax_df = self.get_abundance_by_taxonomy(tax)
                tax_df['sample_id'] = tax_df['sample_id'].astype(str)
                # print(f"Number of records in tax_df for taxonomy {taxonomy}: {len(tax_df)}")
                if tax_df.empty:
                    # print(f"tax_df is empty for taxonomy {taxonomy}")
                    continue

                self.meta_df['sample_id'] = self.meta_df['sample_id'].astype(str)
                # print("ASDF")
                # print(tax_df['sample_id'].dtype)
                # print(self.meta_df['sample_id'].dtype)

                merged_df = tax_df.merge(self.meta_df, on='sample_id', how='outer', suffixes=('_t', '_m'))

                merged_df = merged_df.dropna(subset=['abundance'])
                if merged_df.empty:
                    print(f"merged_df is empty for taxonomy {tax}")
                    continue

                # for each selected method
                for method in methods:

                    # prepare the row containing correlation scores per metadata
                    # and the rows containing the corresponding probabilities
                    # of the correlation score per metadata according to the selected tests
                    score_row = {'Taxonomy': tax, 'Method or Test': method}
                    test_rows = {t: {'Taxonomy': tax, 'Method or Test': ' '.join([method, t])} for t in tests}

                    # for each metadata available in the database
                    for meta in meta_cols:
                        merged_df_meta = merged_df.dropna(subset=[meta])
                        abundance_series = merged_df_meta['abundance']

                        if merged_df_meta.empty:
                            # print(f"merged_df_meta is empty for metadata {meta}")
                            continue
                        all_zero = (abundance_series == 0).all().all()
                        if len(abundance_series) > 1 or all_zero:
                            continue

                        if (abundance_series != 0).sum() <= 2:
                            continue

                        # calculate the correlation score and its probability
                        # according to the selected tests
                        # print("blaa")
                        # print(taxonomy)
                        # print(meta)
                        # print(merged_df['abundance'])

                        # print(f"META: {meta}")




                        score, test_scores = scipy_correlation(abundance_series, merged_df_meta[meta],
                                                                       tests, method)

                        heatmap_df.loc[f"{tax}_{method}", f"{method}_{meta}"] = score


                        # Create new row
                        # Append the row to the DataFrame
                        # Append the row to the DataFrame

                        # print("Final Heatmap DF:\n", heatmap_df)



                        # populate the row containing correlation scores per metadata
                        score_row[meta] = score

                        # then populate the rows containing the corresponding probabilities
                        # of the correlation score per metadata according to the selected tests
                        for test, test_score in test_scores.items():
                            test_rows[test][meta] = test_score
                            test_score_df = pd.DataFrame([test_scores[test]], columns=[meta],
                                                         index=[f"{tax}_{method}_{test}"])
                            heatmap_df = pd.concat([heatmap_df, test_score_df])

                    # finally append the correlation row and the probability rows to the dataframe
                    df = pd.concat([df, pd.DataFrame([score_row])], ignore_index=True)
                    for test, test_row in test_rows.items():
                        df = pd.concat([df, pd.DataFrame([test_row])], ignore_index=True)
                    self._heatmap_df = heatmap_df



                    self._heatmap_df.index = replace_brackets(self._heatmap_df.index)




            # return data for the dash data table according to
            # https://dash.plotly.com/datatable
            self._table_df = df
            # print(f"Heatmap df: {heatmap_df}")
            self._heatmap_df = heatmap_df  # Save the heatmap DataFrame as an attribute of the class

            return [{"name": i, "id": i} for i in df.columns], df.to_dict('records'), taxonomies


        @self.app.callback(Output('heatmap-graph', 'figure'),
                           Input('methods-dd', 'value'))
        def species_heatmap(methods_value):
            if self._heatmap_df is None:  # add this condition to handle None value
                return go.Figure()

            else:
                # print(f"Heatmap df: {self._heatmap_df}")
                selected_columns = [col for col in self._heatmap_df.columns if methods_value in col]
                # print("self._heatmap_df")
                # print(self._heatmap_df)
                selected_data = self._heatmap_df[['taxonomy'] + selected_columns]
                # print(f"selected data: {selected_data}")
                # selected_data = None
                # try:
                selected_data = selected_data[~selected_data.index.astype(str).str.contains('nan')]


            # Extract only the numerical values from the filtered selected_data DataFrame
                numerical_values = selected_data.iloc[:, 1:].values

            # Get the index after filtering the 'nan' rows
                filtered_index = selected_data.index

                # print(f"numerical values of method  {methods_value}: {numerical_values}")
                fig = go.Figure(data=go.Heatmap(
                    z=numerical_values,
                    x=[col.split('_', 1)[-1] for col in selected_columns],
                    y=filtered_index,
                    colorscale='blugrn',
                    colorbar_title=f"{methods_value} score"))

                return fig

        @self.app.callback(
                Output('download-tb', 'data'),
                Input('export-btn-tb', 'n_clicks'),
            )
        def _export_table(n_clicks) -> Dict[Any, str]:
            """
            Download data table content.
            """
            if n_clicks is None:
                raise PreventUpdate
            return dict(content=self._table_df.to_csv(index=False), filename='correlations.csv')


        """
    
          QC CALLBACKS ----- QC CALLBACKS ----- QC CALLBACKS ----- QC CALLBACKS ----- QC CALLBACKS ----- QC CALLBACKS ------
    
        """
        """
         configuration variables
        """
        stat_indicator_plots_margin = dict(t=0, b=0, l=0, r=0)
        stat_indicator_plots_fontsize = 30
        stat_indicator_plots_title_fontsize = 15

        stat_indicator_plots_height = 200
        stat_indicator_plots_width = 120

        ...
        # MEAN QUALITY PER BASE PLOT
        @self.app.callback(
            Output('mean-quality-per-base-plot', 'figure'),
            [Input('sample-dropdown-qc', 'value')]
        )
        def update_mean_quality_per_base_plot(selected_sample):
            # Fetch the SequencingStatistics for the selected sample
            stats_for_sample = SequencingStatistics.objects.filter(user_id=self.user_id,
                                                                   sample_name=selected_sample).first()

            # Deserialize the avg_qualities field
            avg_qualities = json.loads(stats_for_sample.avg_qualities)

            # Filter out the tail values based on z-score
            z_scores = zscore(avg_qualities)
            threshold = 0.5 # restrict to only show bases within 0.1 sd of mean of all base positions (increase to show more bases)
            valid_indices = np.where(np.abs(z_scores) < threshold)[0]
            truncated_avg_qualities = [avg_qualities[i] for i in valid_indices]

            # Calculate the smoothed values using LOWESS
            x_values = np.arange(len(truncated_avg_qualities))
            smoothed = lowess(truncated_avg_qualities, x_values, frac=0.1)

            fig = go.Figure()

            # Mean Quality as a solid line
            fig.add_trace(go.Scatter(
                x=list(range(1, len(truncated_avg_qualities) + 1)),  # 1-based index for base position
                y=truncated_avg_qualities,
                mode='lines',
                name='Mean Quality',
                line=dict(color='black')
            ))

            # Lowess smoothed line as a dashed line
            smoothed = lowess(truncated_avg_qualities, range(len(truncated_avg_qualities)), frac=0.1)
            fig.add_trace(go.Scatter(
                x=list(range(1, len(smoothed) + 1)),  # 1-based index for base position
                y=smoothed[:, 1],
                mode='lines',
                name='Smoothed Mean Quality',
                line=dict(dash='dash', color='yellow')
            ))

            fig.update_layout(
                title='Mean Quality per Base',
                xaxis_title='Base Position',
                yaxis_title='Mean Quality',
                xaxis=dict(showgrid=False),
                yaxis=dict(showgrid=True, gridcolor='rgba(230,230,230,0.5)'),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )

            return fig


        @self.app.callback(
            Output('mean_read_length-graph', 'figure'),
            [Input('sample-dropdown-qc', 'value')]
        )
        def update_mean_read_length_plot(selected_sample):
            # Fetch the SequencingStatistics for the selected sample
            stats_for_sample = SequencingStatistics.objects.filter(user_id=self.user_id, sample_name=selected_sample).first()

            # Extract mean read length
            mean_read_length = stats_for_sample.mean_read_length

            # Generate the plot
            fig = go.Figure()
            fig.add_trace(go.Indicator(
                mode = "number",
                value = mean_read_length,
                title={"text": "Mean Read Length", "font": {"size": stat_indicator_plots_title_fontsize}},
                number={"font": {"size": stat_indicator_plots_fontsize}}
            ))
            fig.update_layout(
                autosize=False,
                width=stat_indicator_plots_height,  # Adjust the width as desired
                height=stat_indicator_plots_width,
            margin=stat_indicator_plots_margin  # Reduce left margin
                # Adjust the height as desired
            )

            return fig

        @self.app.callback(
            Output('mean_quality_score-graph', 'figure'),
            [Input('sample-dropdown-qc', 'value')]
        )
        def update_mean_quality_score_plot(selected_sample):
            # Fetch the SequencingStatistics for the selected sample
            stats_for_sample = SequencingStatistics.objects.filter(user_id=self.user_id,
                                                                   sample_name=selected_sample).first()

            # Extract mean quality score
            mean_quality_score = stats_for_sample.mean_quality_score

            # Generate the plot
            fig = go.Figure()
            fig.add_trace(go.Indicator(
                mode="number",
                value=mean_quality_score,
                title={"text": "Mean Quality Score", "font": {"size": stat_indicator_plots_title_fontsize}},
                number={"font": {"size": stat_indicator_plots_fontsize}}

            ))
            fig.update_layout(
                # ... (other layout settings)
                autosize=False,
                width=stat_indicator_plots_height,  # Adjust the width as desired
                height=stat_indicator_plots_width,
                margin=stat_indicator_plots_margin  # Reduce left margin

            )

            return fig

        @self.app.callback(
            Output('number_of_reads-graph', 'figure'),
            [Input('sample-dropdown-qc', 'value')]
        )
        def update_number_of_reads_graph(selected_sample):
            # Fetch the SequencingStatistics for the selected sample
            stats_for_sample = SequencingStatistics.objects.filter(user_id=self.user_id,
                                                                   sample_name=selected_sample).first()

            # Create an indicator plot
            fig = go.Figure(go.Indicator(
                mode="number",
                value=stats_for_sample.number_of_reads,
                title={"text": "Number of Reads", "font": {"size": stat_indicator_plots_title_fontsize}},
                number={"font": {"size": stat_indicator_plots_fontsize}}

            ))

            # Remove the plot's axis for a cleaner look
            fig.update_layout(
                # ... (other layout settings)
                autosize=False,
                width=stat_indicator_plots_height,  # Adjust the width as desired
                height=stat_indicator_plots_width,
                margin= stat_indicator_plots_margin

            )

            return fig

        @self.app.callback(
            Output('total_bases_sequenced-graph', 'figure'),
            [Input('sample-dropdown-qc', 'value')]
        )
        def update_total_bases_sequenced_graph(selected_sample):
            # Fetch the SequencingStatistics for the selected sample
            stats_for_sample = SequencingStatistics.objects.filter(user_id=self.user_id,
                                                                   sample_name=selected_sample).first()

            # Create an indicator plot
            fig = go.Figure(go.Indicator(
                mode="number",
                value=stats_for_sample.total_bases_sequenced,
                title={"text": "Total Bases Sequenced", "font": {"size": stat_indicator_plots_title_fontsize}},

            number={"font": {"size": stat_indicator_plots_fontsize}}

            ))

            # Remove the plot's axis for a cleaner look
            fig.update_layout(
                # ... (other layout settings)
                autosize=False,
                width=stat_indicator_plots_height,  # Adjust the width as desired
                height=stat_indicator_plots_width,
                margin=stat_indicator_plots_margin

            )

            return fig

        @self.app.callback(
            Output('q20_score-graph', 'figure'),
            [Input('sample-dropdown-qc', 'value')]
        )
        def update_q20_score_graph(selected_sample):
            # Fetch the SequencingStatistics for the selected sample
            stats_for_sample = SequencingStatistics.objects.filter(user_id=self.user_id,
                                                                   sample_name=selected_sample).first()

            # Create an indicator plot
            fig = go.Figure(go.Indicator(
                mode="number",
                value=stats_for_sample.q20_score,
                title={"text": "Q20 Score", "font": {"size": stat_indicator_plots_title_fontsize}},
                number={"font": {"size": stat_indicator_plots_fontsize}}

            ))

            # Remove the plot's axis for a cleaner look
            fig.update_layout(
                # ... (other layout settings)
                autosize=False,
                width=stat_indicator_plots_height,  # Adjust the width as desired
                height=stat_indicator_plots_width,
                margin=stat_indicator_plots_margin

            )

            return fig

        @self.app.callback(
            Output('q30_score-graph', 'figure'),
            [Input('sample-dropdown-qc', 'value')]
        )
        def update_q30_score_graph(selected_sample):
            # Fetch the SequencingStatistics for the selected sample
            stats_for_sample = SequencingStatistics.objects.filter(user_id=self.user_id,
                                                                   sample_name=selected_sample).first()

            # Create an indicator plot
            fig = go.Figure(go.Indicator(
                mode="number",
                value=stats_for_sample.q30_score,
                title={"text": "Q30 Score", "font": {"size": stat_indicator_plots_title_fontsize}},
                number={"font": {"size": stat_indicator_plots_fontsize}}

            ))

            # Remove the plot's axis for a cleaner look
            fig.update_layout(
                # ... (other layout settings)
                autosize=False,
                width=stat_indicator_plots_height,  # Adjust the width as desired
                height=stat_indicator_plots_width,
                margin=stat_indicator_plots_margin

            )

            return fig

        @self.app.callback(
            Output('mean-gc-indicator-plot', 'figure'),
            [Input('sample-dropdown-qc', 'value')]
        )
        def update_mean_gc_indicator_plot(selected_sample):
            # Fetch the SequencingStatistics for the selected sample
            stats_for_sample = SequencingStatistics.objects.filter(user_id=self.user_id, sample_name=selected_sample).first()

            # Extract mean GC content
            mean_gc = stats_for_sample.mean_gc_content

            # Generate the plot
            fig = go.Figure()
            fig.add_trace(go.Indicator(
                mode="number",
                value=mean_gc,
                title={"text": "Mean GC Content", "font": {"size": stat_indicator_plots_title_fontsize}},
                number={"font": {"size": stat_indicator_plots_fontsize}}
            ))
            fig.update_layout(
                autosize=False,
                width=stat_indicator_plots_height,  # Adjust the width as desired
                height=stat_indicator_plots_width,
                margin=stat_indicator_plots_margin  # Reduce left margin
            )

            return fig

        @self.app.callback(
            Output('read-length-distribution-plot', 'figure'),
            [Input('sample-dropdown-qc', 'value')]
        )
        def update_read_length_distribution_plot(selected_sample):
            # Fetch the SequencingStatistics for the selected sample
            stats_for_sample = SequencingStatistics.objects.filter(user_id=self.user_id,
                                                                   sample_name=selected_sample).first()

            # Deserialize the read_lengths field
            lengths = json.loads(stats_for_sample.read_lengths)

            # Create the histogram
            fig = go.Figure(data=[go.Histogram(x=lengths)])
            fig.update_layout(title="Read Length Distribution",
                              xaxis_title="Read Length",
                              yaxis_title="Frequency",
                              xaxis=dict(showgrid=False),
                              yaxis=dict(showgrid=True, gridcolor='rgba(230,230,230,0.5)'),
                              plot_bgcolor='rgba(0,0,0,0)',
                              paper_bgcolor='rgba(0,0,0,0)')

            return fig

        @self.app.callback(
            Output('gc-content-distribution-plot', 'figure'),
            [Input('sample-dropdown-qc', 'value')]
        )
        def update_gc_content_distribution_plot(selected_sample):
            # Fetch the SequencingStatistics for the selected sample
            stats_for_sample = SequencingStatistics.objects.filter(user_id=self.user_id,
                                                                   sample_name=selected_sample).first()

            # Deserialize the sequences field


            # Compute GC content for each sequence
            gc_contents = json.loads(stats_for_sample.gc_contents_per_sequence)

            # Create the histogram
            fig = go.Figure(data=[go.Histogram(x=gc_contents)])
            fig.update_layout(title="GC Content Distribution",
                              xaxis_title="GC Content (%)",
                              yaxis_title="Frequency",
                              xaxis=dict(showgrid=False),
                              yaxis=dict(showgrid=True, gridcolor='rgba(230,230,230,0.5)'),
                              plot_bgcolor='rgba(0,0,0,0)',
                              paper_bgcolor='rgba(0,0,0,0)')

            return fig

    def get_abundance_meta_by_taxonomy(self, tax) -> pd.DataFrame:
        if not tax:  # add this condition to handle empty list
            return None
        tax = replace_brackets(tax)
        # if isinstance(tax, list):
        #     tax = tax[0]

            # print(f"Taxonomy in get_abundance_meta_by_taxonomy method {taxonomy}")

        q = f"""
            SELECT nanopore.sample_id, nanopore.abundance, metadata.*
            FROM nanopore
            INNER JOIN metadata
            ON nanopore.sample_id = metadata.sample_id
            WHERE nanopore.taxonomy = '{tax}'
            ORDER BY nanopore.sample_id
        """

        return _explode_metadata(self.query_to_dataframe(q))

    def get_abundance_by_taxonomy(self, taxonomy: str) -> pd.DataFrame:
        if isinstance(taxonomy, list):
            taxonomy = taxonomy[0]

        q = f"SELECT sample_id, abundance FROM nanopore WHERE taxonomy = '{taxonomy}' ORDER BY sample_id"
        return self.query_to_dataframe(q)


    def query_to_dataframe(self,query: str) -> pd.DataFrame:
        return pd.read_sql_query(query, self._engine)


def replace_brackets(input_data):
    def process_string(s):
        if s.startswith("[") and s.endswith("]"):
            return s[1:-1]
        return s

    if isinstance(input_data, str):
        return process_string(input_data)

    if isinstance(input_data, list):
        return [replace_brackets(item) for item in input_data]

    if isinstance(input_data, pd.RangeIndex) or isinstance(input_data, pd.Index):
        return pd.Index([process_string(str(item)) for item in input_data])

    raise TypeError("Unsupported type. Only strings, lists, or pandas RangeIndex are allowed.")


def _force_list(x: Union[Any, List]) -> List[Any]:
    """
    Force object into a list if object is not a list.
    """

    return x if isinstance(x, list) else [x]


            # @self.app.server.route('/shutdown', methods=['POST'])
        # def shutdown():
        #     """
        #     Terminate the dash app.
        #     """
        #     func = request.environ.get('werkzeug.server.shutdown')
        #     if func is None:
        #         raise RuntimeError('Not running with the Werkzeug Server')
        #     func()
        #     return 'Server is shutting down...'

    # def run_server(self, debug: bool) -> Non
