import base64
import io
import json
import re
import sqlite3
import tempfile
import zipfile
from io import StringIO
from json import loads
from typing import Any, List, Union

import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_mantine_components as dmc
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
from dash import dcc, html
from dash.exceptions import PreventUpdate
from dash_extensions.enrich import Output, Input, State
from dash_iconify import DashIconify
# from dash_bootstrap_templates import load_figure_template
from django_plotly_dash import DjangoDash
from scipy.ndimage.filters import gaussian_filter
from scipy.stats import zscore
from statsmodels.nonparametric.smoothers_lowess import lowess

from users.models import NanoporeRecord, Metadata
from users.models import SequencingStatistics
from . import taxonomy, correlations, qc, diversity, horizon


# def _init_mysql(user_id):


def _explode_metadata(df):
    return pd.concat([df, df['data'].apply(_parse_dict)], axis=1).drop(columns='data')


def _parse_dict(x):
    return pd.Series(loads(x))


class Index:
    """
    The Index class is the main class of the application.
    It contains the main layout and callbacks.
    """


    """
    Landing page of the dash application.
    Contains navigation to the various application pages.
    """

    def __init__(self, user_id):
        self.user_id = user_id
        self.sample_ids = None
        print(user_id)
        self.app = DjangoDash('Index', add_bootstrap_links=True)

        # self.colors = px.colors.qualitative.Dark24 + px.colors.qualitative.Light24
        # self.colors = self.colors + px.colors.qualitative.Plotly + px.colors.qualitative.Pastel

        # self.colors = colors

        self.taxonomy_app = taxonomy.Taxonomy(user_id)
        self.diversity_app = diversity.Diversity(user_id)
        self.correlations_app = correlations.Correlations(user_id)
        self.horizon_app = horizon.Horizon(user_id)

        self.qc_app = qc.QC(user_id)
        self.diversity_metric = None

        self.tax_fig = None
        pd.set_option('display.max_columns', None)
        pd.set_option('display.max_rows', None)

        # Get the session key from the cookie
        # session_key = flask.request.cookies.get(settings.SESSION_COOKIE_NAME)

        # Get the session
        # session = Session.objects.get(session_key=session_key)

        # Get the user ID from the session
        user_id = self.user_id
        # user_id = session.get_decoded().get('_auth_user_id')

        self._heatmap_df = None
        self._table_df = None
        records = NanoporeRecord.objects.filter(user_id=user_id)
        self.df = pd.DataFrame.from_records(records.values())
        self.df = self.df.drop_duplicates(subset=['sample_id', 'taxonomy'])

        self.df.loc[self.df['taxonomy'] == 'Not available', 'taxonomy'] = np.nan
        print(self.df.head())
        self.df.loc[self.df['taxonomy'] == 'Not Available', 'taxonomy'] = np.nan

        self.df.dropna(inplace=True)
        print(self.df.head())

        self.df.drop_duplicates(
            subset=['sample_id', 'abundance', 'taxonomy', 'project_id', 'subproject', 'user_id', 'date'],
            inplace=True)
        # sorted_sample_ids = natsorted(self.df['sample_id'].unique())
        # self.sample_ids = sorted_sample_ids
        self.df_sorted = self.df.sort_values(by=['project_id','subproject','sample_id'])
        print("df after sorting initially")
        print(self.df_sorted.head(50))
        print("df after sorting initially")

        # self.df_sorted = self.df.set_index('sample_id').loc[sorted_sample_ids].reset_index()


        self.meta_df = self.correlations_app.get_all_meta()
        # self.df['sample_id'] = self.df['sample_id'].astype(str)

        # self.meta_df['sample_id'] = self.meta_df['sample_id'].astype(str)
        if not self.meta_df.empty:
            self.df_merged = self.df.merge(self.meta_df, on="sample_id", how="left")
            self.metadata_columns = self.meta_df.columns.tolist()
            #
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
            '/dashapp/horizon': {
                'name': 'Horizon',
                'app': self.horizon_app.app,
                'instance': self.horizon_app
            },

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

        # initialize colors from taxonomy_app
        self.colors = self.taxonomy_app.colors

        # Initialize Index layout
        self._init_layout()
        self.app.layout = self.layout
        print("Initialized Index layout")
        # self.taxonomy_app._init_layout()

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

        #
        #     location = dmc.Container(
        #     [
        #         dmc.Space(h=50),
        #         dmc.Title("My Dash App", align="center"),
        #         dmc.Space(h=20),
        #         dmc.Group(
        #             position="center",
        #             children=[
        #                 html.A(
        #                     dmc.Button("Diversity Dashboard", variant="outline"),
        #                     href=f"values['name']",
        #
        #
        #
        #
        #                 ),
        #                 # Wrap more buttons in html.A if you have other dashboard links
        #                 # html.A(
        #                 #     dmc.Button("Another Dashboard", variant="outline"),
        #                 #     href="/another"
        #                 # ),
        #             ]
        #         ),
        #         dmc.Space(h=50),
        #         # Include other components as needed
        #     ],
        #     style={'textAlign': 'center'}
        #
        #
        # )
        #
        location = dcc.Location(id='url', refresh=True)
        navigation = html.Div([
            dcc.Link(values['name'], href=url, style={'padding': '15px 25px', 'font-size': "16px", 'color': 'white'})
            for url, values in self._apps.items()
        ], className="row", style={'margin-left': '0px', 'backgroundColor': '#15242B'})
        page_content = html.Div(id='page-content', children=[], style={})
        # graph1 = dcc.Graph(id='graph1', figure={'data': []})

        container = html.Div([location, navigation, page_content], style={},
                             className="dbc dbc-ag-grid")

        self.layout = container

        self.layout = container

    """
    Taxonomy app helper functions
    """

    def plot_pseudo_horizon(self, df):
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
        total_abundance = df.groupby(taxonomic_rank)['abundance'].sum().sort_values(ascending=False)
        x_axis = "date" if use_date_value else "sample_id"
        category_orders = {x_axis: sorted(df[x_axis].unique())} if not use_date_value else {}
        fig = px.bar(df, x=x_axis, y="abundance", color=taxonomic_rank, barmode="stack",
                     hover_data=df.columns, color_discrete_map=self.taxonomy_app.combined_color_dict,
                     category_orders=category_orders)
        fig.update_layout(legend={'traceorder': 'normal'})
        fig.data = sorted(fig.data, key=lambda trace: total_abundance[trace.name], reverse=True)

        fig.update_layout(
            legend=dict(
                orientation="v",
                y=1,
                x=1),
        )

        return fig

    def plot_heatmap(self, df, use_date_value, taxonomic_rank):
        x_axis = "date" if use_date_value else "sample_id"
        grouped_df = df.groupby([x_axis, taxonomic_rank])['abundance'].sum().reset_index()

        fig = go.Figure(data=go.Heatmap(
            z=grouped_df['abundance'],
            x=grouped_df[x_axis],
            y=grouped_df[taxonomic_rank],
            colorscale='Turbo'))

        # add abundance to legend description
        fig.update_layout(

            legend=dict(
                title="Abundance",
                orientation="v",
                y=1,
                x=1.1

            ),

            xaxis_title="Sample IDs",

            yaxis_title="Taxonomy",
        )
        # make plot bigger for heatmap (height = 1000)
        fig.update_layout(width=1800, height=1000)
        # make x-axis font size 12 and y-axis 10
        fig.update_xaxes(tickfont=dict(size=14))
        fig.update_yaxes(tickfont=dict(size=8))

        return fig

    def plot_line(self, df, use_date_value, taxonomic_rank):
        x_axis = "date" if use_date_value else "sample_id"
        grouped_df = df.groupby([x_axis, taxonomic_rank])['abundance'].sum().reset_index()
        fig1 = px.line(grouped_df, x=x_axis, y="abundance", color=taxonomic_rank
                       )
        return fig1

    def plot_grouped_bar(self, df, use_date_value, taxonomic_rank):
        x_axis = "date" if use_date_value else "sample_id"
        grouped_df = df.groupby([x_axis, taxonomic_rank])['abundance'].sum().reset_index()
        fig1 = px.bar(grouped_df, x=x_axis, y="abundance", color=taxonomic_rank)
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

        # Create the area plot with additional hover data
        fig = px.area(grouped_df, x=x_axis, y="abundance", color=taxonomic_rank,color_discrete_map=self.taxonomy_app.combined_color_dict)
                        # Include all columns as hover data

        # Customize hover template if necessary
        # fig.update_traces(
        #     hovertemplate="<br>".join([
        #                                   f"{x_axis}: %{{x}}",
        #                                   f"Abundance: %{{y}}",
        #                               ] + [f"{col}: %{{customdata[{i}]}}" for i, col in enumerate(df.columns) if
        #                                    col not in [x_axis, 'abundance']])
        # )

        # Add lines for project_id and subproject_id changes as before

        return fig

    def plot_scatter_3d(self, df, taxonomic_rank):
        # Plotting code for scatter 3D goes here...
        fig1 = px.scatter_3d(df, x='taxonomy', y='abundance', z='sample_id', color=taxonomic_rank)
        # fig2 = px.scatter_3d(df, x='abundance', y='taxonomy', z='sample_id', color='abundance',hover_data=self.hover_data)
        return fig1

    def plot_pie(self, df, sample_value_piechart, taxonomic_rank):
        filtered_df = df[df["sample_id"] == sample_value_piechart]
        aggregated_df = filtered_df.groupby(taxonomic_rank)['abundance'].sum().reset_index()
        fig1 = px.pie(aggregated_df, values='abundance', names=taxonomic_rank,
                      title=f'Pie chart of bioreactor taxonomy of sample {sample_value_piechart}')
        piechart_style = {'display': 'block'}
        return fig1, piechart_style

    def split_alphanumeric(self, text):
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

        @self.app.callback(
            Output('time-series-chart', 'figure'),
            Input('bar-chart', 'clickData'),
            prevent_initial_call=True
        )
        def update_time_series(clickData):
            if clickData is None:
                return go.Figure()

            taxon = clickData['points'][0]['customdata']
            # Filter your dataframe based on the selected taxon and create a time-series plot
            # Example:
            # filtered_df = df[df[taxonomic_rank] == taxon]
            # fig = px.line(filtered_df, x='date', y='abundance', title=f'Time-Series for {taxon}')
            return fig

        @self.app.callback(
            Output('info-modal', 'opened'),
            Output('taxon-details', 'children'),
            Input('bar-chart', 'clickData'),
            prevent_initial_call=True
        )
        def display_taxon_details(clickData):
            if clickData is None:
                return False, []

            taxon = clickData['points'][0]['customdata']
            details = f"Details for {taxon}"  # Replace with actual data retrieval logic
            return True, details

        @self.app.callback(
            Output("sample_select_value", "value"),
            [Input("project-dropdown", "value"),
             Input("subproject-dropdown", "value"),
             Input("date-dropdown", "value")]
        )
        def select_samples_by_x(selected_project, selected_subproject, selected_date):
            selected_date_dt = pd.to_datetime(selected_date)

            global trigger_id
            ctx = dash.callback_context

            if not ctx.triggered:
                return self.unique_sample_ids
            else:
                trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

            if trigger_id == "project-dropdown":
                if selected_project == "ALL":
                    # If 'All Projects' is selected, don't filter by project_id
                    filtered_df = self.df
                else:
                    filtered_df = self.df[self.df['project_id'] == selected_project]

            elif trigger_id == "subproject-dropdown":
                if selected_subproject == "ALL":
                    # If 'All Subprojects' is selected, don't filter by subproject
                    filtered_df = self.df
                else:
                    filtered_df = self.df[self.df['subproject'] == selected_subproject]

            elif trigger_id == "date-dropdown":
                if selected_date == "ALL":
                    filtered_df = self.df
                else:
                    filtered_df = self.df[self.df['date'] == selected_date_dt.date()]
                    print(f"type of self.df['date']: {type(self.df['date'][0])}")
                    print(f" self.df['date']: {self.df['date'][0]}")
                    print(f"type of selected_date: {type(selected_date)}")
                    print(f" selected_date: {selected_date}")

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
            # self.df.needs_processing = True
            # Check if sorting and duplicate removal is necessary

            # Efficient grouping and filtering
            self.df_selected = self.df_sorted[self.df_sorted['sample_id'].astype(str).isin(sample_select_value)]
            self.df_selected = self.df_selected.groupby('sample_id').head(slider_value).reset_index(drop=True)
            # self.df_selected = self.df_selected.sort_values(by=['sample_id','project_id'], ascending=[True, True])

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
            print(f"df selected before plotting: {self.df_selected.head(50)}")
            if value in plot_functions:
                fig1 = plot_functions[value](self.df_selected, use_date_value, taxonomic_rank) if value != 'pie' \
                    else plot_functions[value](self.df_selected, sample_value_piechart, taxonomic_rank)[0]
                if value == 'pie':
                    piechart_style = {'display': 'block'}

            #  give distinct color based on self.colors

            # if value != 'heatmap':
            #     for i in range(len(fig1['data'])):
            #         fig1['data'][i]['marker']['color'] = self.colors[i % len(self.colors)]
            #     #     make plot bigger if not heatmap
            #
            #
            # # also change color for px.area plot
            # if value == 'area':
            #     for i in range(len(fig1['data'])):
            #         fig1['data'][i]['fillcolor'] = self.colors[i % len(self.colors)]
            #
            # if value == 'pie':
            #     fig1['data'][0]['marker']['colors'] = self.colors
            #
            # # change color for scatter plot
            # if value == 'scatter':
            #     fig1['data'][0]['marker']['colorscale'] = self.colors
            # # remove grey background from plot
            fig1.update_layout(height=800, legend=dict(font=dict(size=18)), xaxis=dict(tickfont=dict(size=18)),
                               yaxis=dict(tickfont=dict(size=20)))
            fig1['layout']['plot_bgcolor'] = 'rgba(0,0,0,0)'

            # sort legend based on values from high to low
            # if value != 'heatmap':
            #     fig1['data'] = sorted(fig1['data'], key=lambda x: sum(x['y']), reverse=True)
            self.tax_fig = fig1
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
            [Input("btn-download-csv-taxonomy", "n_clicks")]
        )
        def download_csv(n_clicks):
            if n_clicks is None:  # This check prevents the callback from running on app load
                raise dash.exceptions.PreventUpdate

            # Your existing logic for CSV download goes here
            csv_string = self.df_sorted.to_csv(index=False)
            csv_bytes = StringIO()
            csv_bytes.write(csv_string)
            csv_bytes.seek(0)
            filename = f"mmonitor_data_user{self.user_id}.csv"
            return dcc.send_data_frame(self.df_sorted.to_csv, filename=filename)

        @self.app.callback(
            Output("download-counts", "data"),
            [Input("btn-download-counts-taxonomy", "n_clicks")]
        )
        def download_counts(n_clicks):
            if n_clicks is None:
                raise dash.exceptions.PreventUpdate

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
            filename = f"mmonitor_counts_user{self.user_id}.csv"

            # Return the download link and filename
            return dcc.send_data_frame(counts_df.to_csv, filename=filename)


        """

        DIVERSITY APP CALLBACKS     DIVERSITY APP CALLBACKS    DIVERSITY APP CALLBACKS   DIVERSITY APP CALLBACKS

        """

        @self.app.callback(
            [Output("menu-text", "children"),
             Output('project-clicks', 'data'),
             Output('subproject-clicks', 'data')],
            [Input("project-button", "n_clicks"),
             Input("subproject-button", "n_clicks")],
        )
        def click_menu(project_clicks, subproject_clicks):
            # Store the click counts in the Store components
            project_data = {'clicks': project_clicks}
            subproject_data = {'clicks': subproject_clicks}

            # Update the text to display the click counts
            text = f"Project clicked {project_clicks} times. Subproject clicked {subproject_clicks} times."
            return text, project_data, subproject_data

        @self.app.callback(
            Output('alpha_diversities_plot1', 'figure'),
            Output('alpha_diversities_plot2', 'figure'),
            Input('sample_select_value', 'value'),
            Input('diversity_metric_dropdown', 'value')
        )
        def plot_alpha_diversities(sample_select_value, alpha_diversity_metric):
            fig, fig2 = self.diversity_app.create_alpha_diversity_plots(sample_select_value, alpha_diversity_metric)
            return fig, fig2

            # BETA DIVERSITY

        @self.app.callback(
            Output('pcoa_plot_container', 'figure'),
            [
                Input('sample_select_value', 'value'),
                Input('toggle-3d', 'checked'),
                Input('project-button', 'n_clicks'),
                Input('subproject-button', 'n_clicks'),
                Input('kmeans-button', 'n_clicks'),
                Input('sample-date-button', 'n_clicks'),
                State('kmeans-input', 'value')
            ]
        )
        def generate_pcoa_figure(selected_samples, toggle_3d, project_clicks, subproject_clicks, kmeans_clicks,
                                 sample_date_clicks, k_value):
            fig = self.diversity_app.create_beta_pcoa_figure(selected_samples, toggle_3d, project_clicks,
                                                             subproject_clicks, kmeans_clicks, sample_date_clicks,
                                                             k_value)
            return fig


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
            fig = self.diversity_app.create_beta_diversity_heatmap(selected_samples)
            return fig

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

        # @self.app.callback(
        #     Output('heatmap-dendrogram', 'figure'),
        #     Input('heatmap-dendrogram', 'relayoutData'),
        #     Input("btn-download-corr", "n_clicks")
        # )
        # def update_heatmap_dendrogram(relayoutData):
        #     # Check if relayoutData is None
        #     if relayoutData is None:
        #         return None
        #     # Check if relayoutData contains zoom or selection information
        #     if 'xaxis.range' in relayoutData:
        #         xaxis_range = relayoutData['xaxis.range']
        #         yaxis_range = relayoutData['yaxis.range']
        #
        #         # Use xaxis_range and yaxis_range to update the displayed portion of the heatmap
        #         # You can filter or zoom in on specific data based on the user's interaction
        #
        #     correlation_matrix = self.correlations_app.correlation_matrix
        #
        #     # correlation_matrix = correlation_matrix.apply(pd.to_numeric, errors='coerce')
        #     correlation_matrix = correlation_matrix.fillna(0)
        #     print(correlation_matrix)

            # Compute hierarchical clustering
            # distances = 1 - correlation_matrix.abs()
            # row_linkage = hierarchy.linkage(1 - correlation_matrix.abs(), method='average', optimal_ordering=True)
            # row_dendrogram = hierarchy.dendrogram(row_linkage, no_plot=True)
            # row_order = row_dendrogram['leaves']

            # print("row_order:", row_order)  # Print row_order for debugging

            # Check the dimensions of correlation_matrix
            # print("correlation_matrix shape:", correlation_matrix.shape)

            # Create a new correlation matrix with reordered rows and columns
            # heatmap_data = correlation_matrix.iloc[row_order, row_order]

            # Create the heatmap using seaborn and plotly
            # sns.set(font_scale=0.7)  # Adjust font size if needed
            # fig = px.imshow(correlation_matrix)
            # fig.update_layout(xaxis_showticklabels=False, yaxis_showticklabels=False)
            # return fig

        @self.app.callback(
            Output("download-corr-csv", "data"),
            [Input("btn-download-corr", "n_clicks")]
            , prevent_initial_call=True)
        def download_correlations_csv(n_clicks):
            if n_clicks is None:
                return 0, None

            # Assuming correlation_matrix is your DataFrame with correlations

            correlation_matrix = self.correlations_app.compute_correlations_for_taxonomies(self.df,
                                                                                           self.correlations_app.get_all_meta())

            # Generate CSV content as a string
            csv_string = correlation_matrix.to_csv(index=False, encoding="utf-8")

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
            filename = "correlations.csv"

            # Return the download link and filename

            return dcc.send_data_frame(correlation_matrix.to_csv, filename=filename)

        @self.app.callback(
            Output('download-metadata-csv', 'data'),
            [Input('download-csv-button', 'n_clicks')],
            prevent_initial_call=True
        )
        def generate_csv(n_clicks):
            if n_clicks:
                # Create the CSV content in-memory using StringIO
                buffer = io.StringIO()
                create_csv_template(self.df, buffer)
                buffer.seek(0)
                csv_string = buffer.getvalue()

                # Use send_string to trigger the download
                return dcc.send_string(csv_string, "metadata_template.csv")

        # Function to create CSV template
        def create_csv_template(dataframe, buffer):
            # Extracting unique sample_ids
            unique_samples = dataframe['sample_id'].unique()

            # Creating a new DataFrame with the required columns
            template_df = pd.DataFrame(unique_samples, columns=['sample_id'])
            template_df['meta_1'] = ''
            template_df['meta_2'] = ''
            template_df['meta_3'] = ''

            # Writing the DataFrame to a buffer instead of a file
            template_df.to_csv(buffer, index=True)

        def create_dmc_notification(message, notification_type='success'):
            return dmc.Notification(id='notifcation-output',
                                    message=message,
                                    action='show',
                                    color='green' if notification_type == 'success' else 'red',

                                    icon=DashIconify(
                                        icon="mdi:bell-check") if notification_type == 'success' else DashIconify(
                                        icon="mdi:bell-cancel")

                                    )

        # METADATA UPLOAD CALLBACK

        def process_dataframe(df):
            row_count = 0
            for _, row in df.iterrows():
                # print(row)
                sample_id = row['sample_id']
                metadata_fields = {key: value for key, value in row.items() if key not in ['sample_id']}

                # Create new Metadata entry
                metadata_entry = Metadata().create_metadata(sample_id=sample_id, data=metadata_fields,
                                                            user_id=self.user_id)
                metadata_entry.create_metadata(metadata_entry, sample_id, self.user_id)
                metadata_entry.save()
                # print(metadata_entry)
                row_count += 1
            return row_count

        @self.app.callback(
            Output('notification-output', 'children'),
            Input('upload-data', 'contents'),
            State('upload-data', 'filename')
        )
        def upload_file(list_of_contents, list_of_names):
            if list_of_contents is not None:
                total_rows_processed = 0
                try:
                    for content, name in zip(list_of_contents, list_of_names):
                        # Split the content into metadata and base64 encoded data
                        content_type, content_string = content.split(',')

                        # Add the necessary padding to the base64 string
                        padding = '=' * (-len(content_string) % 4)
                        content_string_padded = content_string + padding

                        # Decode the base64 string
                        decoded = base64.b64decode(content_string_padded)

                        # Use Pandas to read the CSV data with semicolon as separator
                        df = pd.read_csv(io.StringIO(decoded.decode('utf-8')), sep=';', dtype={'sample_id': str})

                        # Process the DataFrame
                        total_rows_processed += process_dataframe(df)

                    # Success notification
                    return create_dmc_notification(f'Successfully added {total_rows_processed} metadata entries.',
                                                   'success')
                except Exception as e:
                    return create_dmc_notification(f'Error processing file: {str(e)}', 'error')
            return None

            # callback to update correlation graphs
            # @self.app.callback(
            #     Output('graph-score', 'figure'),
            #     Output('graph-test', 'figure'),
            #     Input('taxonomy-dd', 'value'),
            #     Input('methods-dd', 'value'),
            #     Input('tests-dd', 'value')
            # )
            # def _update_graphs(tax: str, method: str, test: str) -> Tuple[Figure, Figure]:
            #     species = [x for x in tax] if tax else []

            # if not species:  # add this condition to handle empty list
            #     return None, None, None, None, None, None

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
            # species = replace_brackets(species)
            # species_str = species[0] if species else None

            # print(f"species string before")
            # print(species_str)

            # species_str = replace_brackets(species_str)
            # print(f"species string after")
            # print(species_str)
            # df = self.get_abundance_meta_by_taxonomy(species_str)
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
            # y_axis_tuple = None

            # y_axis_tuple = [scipy_correlation(df['abundance'], df[meta], test, method) for meta in
            #                 self.metadata_columns]

            # print("df[meta]")
            # print(df[meta])

            # print("metadata_columns")
            # print(self.metadata_columns)

            # print(y_axis_tuple)

            # y_axis_score, y_axis_test = zip(*y_axis_tuple)
            # y_axis_test = [xs[test] for xs in y_axis_test]

            # generate plots
            # fig_score = px.scatter(x=self.metadata_columns, y=y_axis_score,
            #                        labels={'x': 'Metric', 'y': f'{method} Score'})
            # fig_test = px.scatter(x=self.metadata_columns, y=y_axis_test, labels={'x': 'Metric', 'y': f'{test} Score'})

            # return fig_score, fig_test

            # @self.app.callback(
            #     Output('table-correlations', 'columns'),
            #     Output('table-correlations', 'data'),
            #     Output('taxonomy-dd-tb', 'value'),
            #     Input('apply-btn-tb', 'n_clicks'),
            #     Input('select-all-btn-tb', 'n_clicks'),
            #     Input('clear-selection-btn-tb', 'n_clicks'),
            #     State('taxonomy-dd-tb', 'value'),
            #     State('methods-dd-tb', 'value'),
            #     State('tests-dd-tb', 'value'),
            #     State('table-correlations', 'columns'),
            #     State('table-correlations', 'data'),
            # )
            # def _update_table(x: int, y: int, z: int,
            #                   taxonomies: Union[str, List[str]],
            #                   methods: Union[str, List[str]],
            #                   tests: Union[str, List[str]],
            #                   tb_columns: Any,
            #                   tb_data: Any,
            #                   ) -> Tuple[Iterable, Dict, List]:
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
            # ctx = dash.callback_context
            # button_id = 'apply-btn-tb'
            # if ctx.triggered:
            #     button_id = ctx.triggered[0]['prop_id'].split('.')[0]
            #
            # # keep table, adjust selection in taxonomies dropdown menu
            # if button_id == 'select-all-btn-tb':
            #     return tb_columns, tb_data, taxonomies
            # elif button_id == 'clear-selection-btn-tb':
            #     return tb_columns, tb_data, []
            #
            # # format dropdown selections and eject if selections are invalid
            # taxonomies: List[str] = _force_list(taxonomies)
            # methods: List[str] = _force_list(methods)
            # tests: List[str] = _force_list(tests)
            # if len(taxonomies) == 0 or len(methods) == 0:
            #     raise PreventUpdate

            # request data from database and filter for metadata columns

            # meta_cols = [meta for meta in self.meta_df.columns if meta != 'sample_id']

            # prepare the resulting dataframe/table
            # columns = ['Taxonomy', 'Method or Test', *meta_cols]
            # df = DataFrame(columns=columns, index=None)
            # heatmap_df = pd.DataFrame(
            #     columns=['taxonomy'] + [f"{method}_{meta}" for method in methods for meta in meta_cols])

            # print(heatmap_df)

            # print("Initial Heatmap DF:\n", heatmap_df)

            # for each selected taxonomy
            # for tax in taxonomies:
            #
            # request corresponding abundances from database
            # tax_df = self.get_abundance_by_taxonomy(tax)
            # tax_df['sample_id'] = tax_df['sample_id'].astype(str)
            # print(f"Number of records in tax_df for taxonomy {taxonomy}: {len(tax_df)}")
            # if tax_df.empty:
            # print(f"tax_df is empty for taxonomy {taxonomy}")
            # continue

            # self.meta_df['sample_id'] = self.meta_df['sample_id'].astype(str)
            # print("ASDF")
            # print(tax_df['sample_id'].dtype)
            # print(self.meta_df['sample_id'].dtype)

            # merged_df = tax_df.merge(self.meta_df, on='sample_id', how='outer', suffixes=('_t', '_m'))

            # merged_df = merged_df.dropna(subset=['abundance'])
            # if merged_df.empty:
            #     print(f"merged_df is empty for taxonomy {tax}")
            #     continue

            # for each selected method
            # for method in methods:

            # prepare the row containing correlation scores per metadata
            # and the rows containing the corresponding probabilities
            # of the correlation score per metadata according to the selected tests
            # score_row = {'Taxonomy': tax, 'Method or Test': method}
            # test_rows = {t: {'Taxonomy': tax, 'Method or Test': ' '.join([method, t])} for t in tests}

            # for each metadata available in the database
            # for meta in meta_cols:
            #     merged_df_meta = merged_df.dropna(subset=[meta])
            #     abundance_series = merged_df_meta['abundance']
            #
            #     if merged_df_meta.empty:
            # print(f"merged_df_meta is empty for metadata {meta}")
            # continue
            # all_zero = (abundance_series == 0).all().all()
            # if len(abundance_series) > 1 or all_zero:
            #     continue

            # if (abundance_series != 0).sum() <= 2:
            #     continue

            # calculate the correlation score and its probability
            # according to the selected tests
            # print("blaa")
            # print(taxonomy)
            # print(meta)
            # print(merged_df['abundance'])

            # print(f"META: {meta}")

            # score, test_scores = scipy_correlation(abundance_series, merged_df_meta[meta],
            #                                        tests, method)

            # heatmap_df.loc[f"{tax}_{method}", f"{method}_{meta}"] = score

            # Create new row
            # Append the row to the DataFrame
            # Append the row to the DataFrame

            # print("Final Heatmap DF:\n", heatmap_df)

            # populate the row containing correlation scores per metadata
            # score_row[meta] = score

            # then populate the rows containing the corresponding probabilities
            # of the correlation score per metadata according to the selected tests
            # for test, test_score in test_scores.items():
            #     test_rows[test][meta] = test_score
            #     test_score_df = pd.DataFrame([test_scores[test]], columns=[meta],
            #                                  index=[f"{tax}_{method}_{test}"])
            #     heatmap_df = pd.concat([heatmap_df, test_score_df])

            # finally append the correlation row and the probability rows to the dataframe
            # df = pd.concat([df, pd.DataFrame([score_row])], ignore_index=True)
            # for test, test_row in test_rows.items():
            #     df = pd.concat([df, pd.DataFrame([test_row])], ignore_index=True)
            # self._heatmap_df = heatmap_df
            #
            # self._heatmap_df.index = replace_brackets(self._heatmap_df.index)

            # return data for the dash data table according to
            # https://dash.plotly.com/datatable
            # self._table_df = df
            # print(f"Heatmap df: {heatmap_df}")
            # self._heatmap_df = heatmap_df  # Save the heatmap DataFrame as an attribute of the class

            # return [{"name": i, "id": i} for i in df.columns], df.to_dict('records'), taxonomies

        # @self.app.callback(Output('heatmap-graph', 'figure'),
        #                    Input('methods-dd', 'value'))
        # def species_heatmap(methods_value):
        #     if self._heatmap_df is None:  # add this condition to handle None value
        #         return go.Figure()
        #
        #     else:
        #         # print(f"Heatmap df: {self._heatmap_df}")
        #         selected_columns = [col for col in self._heatmap_df.columns if methods_value in col]
        #         # print("self._heatmap_df")
        #         # print(self._heatmap_df)
        #         selected_data = self._heatmap_df[['taxonomy'] + selected_columns]
        #         # print(f"selected data: {selected_data}")
        #         # selected_data = None
        #         # try:
        #         selected_data = selected_data[~selected_data.index.astype(str).str.contains('nan')]
        #
        #         # Extract only the numerical values from the filtered selected_data DataFrame
        #         numerical_values = selected_data.iloc[:, 1:].values
        #
        #         # Get the index after filtering the 'nan' rows
        #         filtered_index = selected_data.index
        #
        #         # print(f"numerical values of method  {methods_value}: {numerical_values}")
        #         fig = go.Figure(data=go.Heatmap(
        #             z=numerical_values,
        #             x=[col.split('_', 1)[-1] for col in selected_columns],
        #             y=filtered_index,
        #             colorscale='blugrn',
        #             colorbar_title=f"{methods_value} score"))
        #
        #         return fig
        #
        # @self.app.callback(
        #     Output('download-tb', 'data'),
        #     Input('export-btn-tb', 'n_clicks'),
        # )
        # def _export_table(n_clicks) -> Dict[Any, str]:
        #     """
        #     Download data table content.
        #     """
        #     if n_clicks is None:
        #         raise PreventUpdate
        #     return dict(content=self._table_df.to_csv(index=False), filename='correlations.csv')

        """
    
          QC CALLBACKS ----- QC CALLBACKS ----- QC CALLBACKS ----- QC CALLBACKS ----- QC CALLBACKS ----- QC CALLBACKS ------
    
        """
        """
         configuration variables
        """
        stat_indicator_plots_margin = dict(t=0, b=0, l=0, r=0)
        stat_indicator_plots_fontsize = 24
        stat_indicator_plots_title_fontsize = 20


        ...

        # overview plot
        @self.app.callback(
            Output('average-read-length-plot', 'figure'),
            # Assuming 'average-read-length-plot' is the ID for the new plot
            [Input('some-input', 'value')]
            # Replace 'some-input' and 'value' with the actual ID and property of the triggering element
        )
        def update_average_read_length(input_value):
            # Logic to update the plot based on the input
            # For a general overview, we might not need to use the input_value
            return self.qc_app.get_mean_read_length_plot()

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
            threshold = 0.5  # restrict to only show bases within 0.1 sd of mean of all base positions (increase to show more bases)
            valid_indices = np.where(np.abs(z_scores) < threshold)[0]
            truncated_avg_qualities = [avg_qualities[i] for i in valid_indices]

            # Calculate the smoothed values using LOWESS
            x_values = np.arange(len(truncated_avg_qualities))
            smoothed = lowess(truncated_avg_qualities, x_values, frac=0.1)

            fig = go.Figure()

            # # Mean Quality as a solid line
            # fig.add_trace(go.Scatter(
            #     x=list(range(1, len(truncated_avg_qualities) + 1)),  # 1-based index for base position
            #     y=truncated_avg_qualities,
            #     mode='lines',
            #     name='Mean Quality',
            #     line=dict(color='black')
            # ))

            # Lowess smoothed line as a dashed line
            smoothed = lowess(truncated_avg_qualities, range(len(truncated_avg_qualities)), frac=0.1)
            fig.add_trace(go.Scatter(
                x=list(range(1, len(smoothed) + 1)),  # 1-based index for base position
                y=smoothed[:, 1],
                mode='lines',
                name='Smoothed Mean Quality',
                line=dict(dash='dash', color='blue')
            ))

            fig.update_layout(
                title='Smoothed Mean Quality per Base',
                xaxis_title='Base Position',
                yaxis_title='Mean Quality',
                xaxis=dict(showgrid=False),
                yaxis=dict(showgrid=False, gridcolor='rgba(230,230,230,0.5)'),
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
            stats_for_sample = SequencingStatistics.objects.filter(user_id=self.user_id,
                                                                   sample_name=selected_sample).first()

            # Extract mean read length
            mean_read_length = stats_for_sample.mean_read_length

            # Generate the plot
            fig = go.Figure()
            fig.add_trace(go.Indicator(
                mode="number",
                value=mean_read_length,
                title={"text": "Mean Read Length", "font": {"size": stat_indicator_plots_title_fontsize}},
                number={"font": {"size": stat_indicator_plots_fontsize}}
            ))
            fig.update_layout(
                autosize=False,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)')

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
                title={"text": "Mean Quality", "font": {"size": stat_indicator_plots_title_fontsize}},
                number={"font": {"size": stat_indicator_plots_fontsize}}

            ))
            fig.update_layout(
                # ... (other layout settings)
                autosize=False,
                plot_bgcolor='rgba(0,0,0,0)')

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
                title={"text": "#Reads", "font": {"size": stat_indicator_plots_title_fontsize}},
                number={"font": {"size": stat_indicator_plots_fontsize}}

            ))

            # Remove the plot's axis for a cleaner look
            fig.update_layout(
                # ... (other layout settings)
                autosize=False,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'

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
                title={"text": "Total Bases", "font": {"size": stat_indicator_plots_title_fontsize}},

                number={"font": {"size": stat_indicator_plots_fontsize}}

            ))

            fig.update_layout(
                # ... (other layout settings)
                autosize=False,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'

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
                title={"text": "Q20", "font": {"size": stat_indicator_plots_title_fontsize}},
                number={"font": {"size": stat_indicator_plots_fontsize}}

            ))

            # Remove the plot's axis for a cleaner look
            fig.update_layout(
                # ... (other layout settings)
                autosize=False,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'

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
                title={"text": "Q30", "font": {"size": stat_indicator_plots_title_fontsize}},
                number={"font": {"size": stat_indicator_plots_fontsize}}

            ))

            # Remove the plot's axis for a cleaner look
            fig.update_layout(
                # ... (other layout settings)
                autosize=False,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'

            )

            return fig

        @self.app.callback(
            Output('mean-gc-indicator-plot', 'figure'),
            [Input('sample-dropdown-qc', 'value')]
        )
        def update_mean_gc_indicator_plot(selected_sample):
            # Fetch the SequencingStatistics for the selected sample
            stats_for_sample = SequencingStatistics.objects.filter(user_id=self.user_id,
                                                                   sample_name=selected_sample).first()

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
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
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
                              yaxis=dict(showgrid=False, gridcolor='rgba(230,230,230,0.5)'),
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
                              yaxis=dict(showgrid=True),
                              plot_bgcolor='rgba(0,0,0,0)',
                              paper_bgcolor='rgba(0,0,0,0)')

            return fig

        # DOWLNOAD SVG CALLBACKS ----- DOWLNOAD SVG CALLBACKS ----- DOWLNOAD SVG CALLBACKS ----- DOWLNOAD SVG CALLBACKS -----
        @self.app.callback(
            Output("download-svg-diversity", "data"),
            [Input("btn-download-svg-diversity", "n_clicks")],
            prevent_initial_call=True
        )
        def download_all_svgs_diversity(n_clicks):
            plot_names = ['alpha_boxplot', 'alpha_lineplot', 'beta_heatmap', 'beta_pcoa']
            # Memory file for our zip.
            zip_buffer = io.BytesIO()
            figs = []
            figs.extend([self.diversity_app.alpha_fig1, self.diversity_app.alpha_fig2,
                         self.diversity_app.beta_fig1, self.diversity_app.beta_fig2])

            for idx, fig in enumerate(figs):
                if fig is None:
                    raise PreventUpdate
                with zipfile.ZipFile(zip_buffer, 'a', zipfile.ZIP_DEFLATED, False) as zip_file:
                    zip_file.writestr(f"{plot_names[idx]}.svg", pio.to_image(fig, format='svg'))

            # Important: Go to the beginning of the BytesIO buffer.
            zip_buffer.seek(0)

            # Use dcc.send_bytes which sends the contents of a BytesIO or file-like object.
            return dcc.send_bytes(zip_buffer.getvalue(), "plots.zip")

        @self.app.callback(
            Output("download-svg-taxonomy", "data"),
            [Input("btn-download-taxonomy-svg", "n_clicks")],
            prevent_initial_call=True
        )
        def download_svg_taxonomy(n_clicks):
            svg_data = pio.to_image(self.tax_fig, format='svg', width=1500)
            svg_bytes = io.BytesIO(svg_data)

            # Use send_bytes to send the SVG data
            return dcc.send_bytes(svg_bytes.getvalue(), "taxonomy.svg")

    #
    # def get_abundance_meta_by_taxonomy(self, tax) -> pd.DataFrame:
    #     if not tax:  # add this condition to handle empty list
    #         return None
    #     tax = replace_brackets(tax)
    #     # if isinstance(tax, list):
    #     #     tax = tax[0]
    #
    #     # print(f"Taxonomy in get_abundance_meta_by_taxonomy method {taxonomy}")
    #
    #     q = f"""
    #         SELECT nanopore.sample_id, nanopore.abundance, metadata.*
    #         FROM nanopore
    #         INNER JOIN metadata
    #         ON nanopore.sample_id = metadata.sample_id
    #         WHERE nanopore.taxonomy = '{tax}'
    #         ORDER BY nanopore.sample_id
    #     """
    #
    #     return _explode_metadata(self.query_to_dataframe(q))

    # def get_abundance_by_taxonomy(self, taxonomy: str) -> pd.DataFrame:
    #     if isinstance(taxonomy, list):
    #         taxonomy = taxonomy[0]
    #
    #     q = f"SELECT sample_id, abundance FROM nanopore WHERE taxonomy = '{taxonomy}' ORDER BY sample_id"
    #     return self.query_to_dataframe(q)

    # def query_to_dataframe(self, query: str) -> pd.DataFrame:
    #     return pd.read_sql_query(query, self._engine)


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
