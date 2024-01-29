import base64
from io import StringIO
from typing import Tuple, List, Any, Dict

import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_mantine_components as dmc
import pandas as pd
import plotly.express as px
from dash import dash_table
from dash import html
from dash.dependencies import Input, Output
from dash_ag_grid import AgGrid
from dash_iconify import DashIconify
from django_plotly_dash import DjangoDash
from plotly.graph_objects import Figure

from users.models import NanoporeRecord
from users.models import SequencingStatistics


class Taxonomy:
    """
    App to display the abundances of taxonomies in various formats.
    """

    def get_data(self):
        records = NanoporeRecord.objects.filter(user_id=self.user_id)
        self.records = records
        if not records.exists():
            return pd.DataFrame()  # Return an empty DataFrame if no records are found

        for record in records:
            if record.date == 'default':
                # Print the record or take other actions if the date is 'default'
                print("Record with 'default' date:", record)

        # Create DataFrame
        try:
            return pd.DataFrame.from_records(records.values())
        except ValueError as e:
            print("Error while converting data to DataFrame:", e)
            # Handle the error or return an empty DataFrame
            return pd.DataFrame()

    def __init__(self, user_id):
        self.records = None
        self.user_id = user_id
        dbc_css = ("https://cdn.jsdelivr.net/gh/AnnMarieW/dash-bootstrap-templates@V1.0.2/dbc.min.css")
        self.app = DjangoDash('taxonomy', external_stylesheets=[dbc.themes.BOOTSTRAP, dbc_css])

        # 55 distinct colors generated using https://mokole.com/palette.html (input: 55, 5% 90%, 1000 loops)
        self.colors = [

            '#a9a9a9', '#2f4f4f', '#556b2f', '#8b4513', '#6b8e23', '#006400', '#708090',
            '#8b0000', '#3cb371', '#bc8f8f', '#663399', '#008080', '#bdb76b', '#4682b4',
            '#000080', '#9acd32', '#20b2aa', '#cd5c5c', '#32cd32', '#daa520', '#8fbc8f',
            '#8b008b', '#b03060', '#d2b48c', '#ff0000', '#ff8c00', '#ffd700', '#ffff00',
            '#c71585', '#00ff00', '#ba55d3', '#00ff7f', '#4169e1', '#e9967a', '#dc143c',
            '#00ffff', '#00bfff', '#f4a460', '#0000ff', '#a020f0', '#adff2f', '#ff7f50',
            '#ff00ff', '#db7093', '#eee8aa', '#6495ed', '#dda0dd', '#87ceeb', '#ff1493',
            '#f5f5dc', '#afeeee', '#ee82ee', '#98fb98', '#7fffd4', '#e6e6fa', '#ffc0cb'
        ]



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
        # self.df.replace("Not available", np.nan, inplace=True)
        # self.df.dropna(inplace=True)

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
            self.unique_genera = self.df['tax_genus'].unique()
            self.unique_families = self.df['tax_family'].unique()
            self.unique_classes = self.df['tax_class'].unique()
            self.unique_orders = self.df['tax_order'].unique()

            self.df_full_for_diversity = self.df.pivot_table(index='sample_id',
                                                             columns='taxonomy',
                                                             values='abundance',
                                                             fill_value=0)
            self.df.to_csv('/home/minion-computer/df.csv')
            self.df_full_for_diversity.to_csv('/home/minion-computer/pivot.csv')

            sample_project_mapping = self.records.values('sample_id', 'project_id')
            self.sample_to_project_dict = {item['sample_id']: item['project_id'] for item in sample_project_mapping}

            # self.df_full_for_diversity.columns = self.df_full_for_diversity.columns.droplevel(0)

            self.df_sorted = self.df.sort_values(by=["sample_id", "abundance"], ascending=[True, False])

            # Get the number of unique values in each column
            # get number of unique taxonomies for creation of slider. limit max taxa to plot to 100
            self.unique_counts = min(self.df.nunique()[1], 500)

        unique_species = self.df_sorted['taxonomy'].unique()
        self.species_colors = {species: color for species, color in
                          zip(unique_species, self.colors * (len(unique_species) // len(self.colors) + 1))}

        def assign_color_to_taxonomy(df, taxonomy, color_dict):
            taxonomy_colors = {}
            for item in df[taxonomy].unique():
                species_in_taxonomy = df[df[taxonomy] == item]['taxonomy'].iloc[
                    0]  # Get the first species in this taxonomy
                taxonomy_colors[item] = color_dict.get(species_in_taxonomy, self.colors[
                    len(taxonomy_colors) % len(self.colors)])  # Assign species color or a new color
            return taxonomy_colors

        self.genus_colors = assign_color_to_taxonomy(self.df_sorted, 'tax_genus', self.species_colors)
        self.family_colors = assign_color_to_taxonomy(self.df_sorted, 'tax_family', self.species_colors)

        self.combined_color_dict = {**self.species_colors, **self.genus_colors, **self.family_colors}

        self._init_layout()
        self._init_callbacks()

    def _init_layout(self) -> None:
        """
        Taxonomy app layout consists of two graphs visualizing the abundances
        of taxonomies and an optional pie chart as well as a data table for
        debugging purposes.
        """
        selected_taxa = html.Div(id='selected-data')

        # Inside your layout
        upload_component = dcc.Upload(
            id='upload-sqlite',
            children=html.Button('Upload SQLite File'),
            multiple=False  # Allow single file upload
        )
        dropdown_container = dbc.Container([
            dbc.Row([
                dbc.Col(
                    [
                        dmc.Text("Samples to plot:", className='text-primary my-2', id='sample_select_text',
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
                    ],
                    width=12, style={'padding-left': 0}
                ),

                dbc.Col(
                    [
                        dmc.Text("Select Samples by project:", id='project-dropdown-text', style={'width': '100%'},
                                 className='text-primary my-2'),
                        dcc.Dropdown(
                            id='project-dropdown',
                            options=[{'label': 'All Projects', 'value': 'ALL'}] +
                                    [{'label': project, 'value': project} for project in self.unique_projects_ids],
                            value=None,
                            style={'width': '100%', 'margin-bottom': '5px'},
                        ),
                    ],
                    width=2, style={'padding-left': 0}
                ),

                dbc.Col(
                    [
                        dmc.Text("Select Samples by subproject:", id='subproject-dropdown-text',
                                 className='text-primary my-2'),
                        dcc.Dropdown(
                            id='subproject-dropdown',
                            options=[{'label': 'All Subprojects', 'value': 'ALL'}] +
                                    [{'label': subproject, 'value': subproject} for subproject in
                                     self.unique_subprojects],
                            value=None
                        ),
                    ],
                    width=2, style={'padding-left': 0}
                ),
                dbc.Col(
                    [
                        dmc.Text("Plot type:", className='text-primary my-2'),
                        dcc.Dropdown(
                            id='dropdown',
                            options=[
                                {'label': 'Stacked Barchart', 'value': 'stackedbar'},
                                {'label': 'Grouped Barchart', 'value': 'groupedbar'},
                                {'label': 'Area plot', 'value': 'area'},
                                {'label': 'Line plot', 'value': 'line'},
                                {'label': 'Heatmap', 'value': 'heatmap'},
                                {'label': 'Scatter plot', 'value': 'scatter'}
                            ],
                            value='stackedbar',
                            style={'width': '100%'}
                        ),
                        dbc.Checklist(id='use_date_value',
                                      options=[{'label': 'Use Date for plotting', 'value': True}],
                                      value=[],
                                      inline=True)
                    ],
                    width=2, style={'padding-left': 0}
                ),
                dbc.Col(
                    [
                        dmc.Text("Taxonomic rank for plot:", className='text-primary my-2'),
                        dcc.Dropdown(
                            id='tax_rank_dropdown',
                            options=[
                                {'label': 'Species', 'value': 'taxonomy'},
                                {'label': 'Genus', 'value': 'tax_genus'},
                                {'label': 'Family', 'value': 'tax_family'},
                                {'label': 'Order', 'value': 'tax_order'},
                                {'label': 'Class', 'value': 'tax_class'},
                                {'label': 'Phylum', 'value': 'tax_phylum'},
                                {'label': 'Superkingdom', 'value': 'tax_superkingdom'},
                                {'label': 'Clade', 'value': 'tax_clade'}
                            ],
                            value='taxonomy',
                            style={'width': '90%'}
                        )
                    ],
                    width=2, style={'padding-left': 0}
                ),
            ])
        ], fluid=True)

        graph_container = html.Div(
            [
                # graph elements
                html.Div(
                    [
                        dcc.Graph(
                            id='graph1',
                            figure={
                                'data': [],  # Replace with your data
                                'layout': {


                                    'height': '800px'
                                    # Add the rest of your layout properties here...
                                }
                            },

                        ),
                        html.Div(
                            dcc.Markdown("**Figure 1**: Abundance of each sample"),
                            style={"textAlign": "center", "margin-top": "1px"}  # Adjust "10px" as needed
                        )
                    ], style={'width': '100%', "padding": "5px"})
                # ),
                #
                # html.Div(
                #     [
                #         dcc.Graph(
                #             id='graph2',
                #             figure={
                #                 'data': []  # Replace with your data
                #             },
                #             style={"border":"2px solid black"}  # Add a border here
                #         ),
                #         html.Div(
                #             dcc.Markdown("**Figure 2**: Abundance of each species"),
                #             style={"textAlign": "center", "margin-top": "1px"}  # Adjust "10px" as needed
                #         ,id='markdown-caption')
                #     ], style={'width': '100%', "padding":"5px"}
                # ),
            ]

        )

        graph3 = dcc.Graph(
            id='graph3',
            figure={
                'data': []  # Replace with your data
            },
            style={'width': '50%'}
        )

        header_pie_chart_sample_select_dbc = dbc.Row(
            dbc.Col(dbc.Label(children='Select a sample to display.'), width={'size': 10, 'offset': 0}),
            justify="center", style={'display': 'none'}, id='header_pie_chart_sample_select_dbc')

        slider_header = dbc.Row(
            dbc.Col(dmc.Text(children='Number of taxa to display:', className='text-primary my-2'),
                    width={'size': 12, 'offset': 0}), justify="start")

        unique_counts_value = self.unique_counts if self.unique_counts else 10
        slider = html.Div([
            dbc.Row(
                dbc.Col(
                    dcc.Slider(
                        id='slider',
                        min=1,

                        max=unique_counts_value,
                        value=unique_counts_value,
                        marks={
                            i: str(i) if i in [1, unique_counts_value // 2, unique_counts_value] else ""
                            for i in range(1, unique_counts_value + 1)
                        },
                        step=1
                    ),
                    width={'size': 4, 'offset': 0}  # centering the slider by offsetting it 3 units
                ),
                justify='start'
            ),
        ])
        unique_samples_value = self.unique_samples
        pie_chart_input = dcc.Dropdown(
            id='number_input_piechart',
            options=[{'label': t, 'value': t} for t in unique_samples_value],

            style={'display': 'none'},
            clearable=False,
        )

        # data table for debugging

        data, columns = self._generate_table_data_cols()
        data_tb = dbc.Row(dbc.Col(dash_table.DataTable(id='table-correlations', data=data, columns=columns),
                                  width={'size': 12, 'offset': 0}), justify="center")

        grid, columns = self._generate_table_ag_grid(100000)

        data_dag_div = html.Div(grid, style={"margin-top": "10px", 'margin-left': '0px'})

        download_button = dbc.Row(
            dmc.Button('Export All',
                       leftIcon=DashIconify(icon="foundation:page-export-csv", width=20),
                       size="lg",
                       variant="filled",
                       id="btn-download-csv-taxonomy",
                       color='blue'


                       ))

        # DashIconify(icon="foundation:page-export-csv"), id="btn-download", size='lg', style={"margin-left":'20px'}))
        download_component = dcc.Download(id="download-csv")

        download_button_counts = dmc.Button('Export Counts',
                                            leftIcon=DashIconify(icon="foundation:page-export-csv", width=20),
                                            size="lg",
                                            variant="filled",
                                            id="btn-download-counts-taxonomy",
                                            color='blue'


                                            )
        download_component_counts = dcc.Download(id="download-counts")
        download_slider_components = dbc.Col(dmc.Group(
            [download_button, download_button_counts, download_component_counts, download_component]))
        container = dbc.Container(

            [
                dropdown_container,
                graph_container,

                # new definition including both dropdowns
                # group_select #,upload_component,
                slider_header, slider,
                pie_chart_input, download_slider_components,
                data_dag_div,

                # data_tb
            ],
            fluid=True, style={}, className="dbc dbc-ag-grid"
        )
        self.app.layout = container

    def _generate_table_ag_grid(self, max_rows=40):
        """
        Generate data to populate a dash-ag-grid table with.
        dash-ag-grid requires the data in a list of dictionaries format and a collection of column definitions.

        Args:
        max_rows (int, optional): The maximum number of rows to include in the table. Defaults to 40.

        Returns:
        Dash AgGrid component with the specified data and columns.
        """
        # Limit the number of rows if needed
        if max_rows is not None:
            df_display = self.df.head(max_rows)
        else:
            df_display = self.df

        # Generate column definitions for dash-ag-grid
        column_defs = [{"headerName": col, "field": col, "sortable": True, "filter": True} for col in
                       df_display.columns]

        # Create the AgGrid component
        ag_grid_table = AgGrid(
            id="table-correlations",
            rowData=df_display.to_dict('records'),
            className="ag-theme-balham",

            columnDefs=column_defs)
        return ag_grid_table, [{'name': i, 'id': i} for i in self.df.columns]

    def _generate_table_data_cols(self, max_rows=40) -> Tuple[List[Any], List[Any]]:
        """
        Generate data to populate a dash data table with.
        A dash data table requires the data in a dict format as well as a collection of mapped column names.

        Args:
        max_rows (int, optional): The maximum number of rows to include in the table. Defaults to 40.

        Returns:
        Tuple[List[Any], List[Any]]: A tuple containing the data for the table in dict format and a collection of mapped column names.
        """
        # q = f"SELECT * FROM nanopore LIMIT {max_rows}"
        # self.df = self.df = pd.read_sql_query(q, self._engine)
        return self.df.to_dict('records'), [{'name': i, 'id': i} for i in self.df.columns]

    # def plot_stacked_bar(self, df):w 
    #     fig1 = px.bar(df, x="sample_id", y="abundance", color="taxonomy", barmode="stack",hover_data="taxonomy")
    #     fig1.update_layout(
    #         legend=dict(
    #             orientation="v",
    #             y=1,
    #             x=1.1
    #         ),
    #         margin=dict(
    #             l=100,  # Add left margin to accommodate the legend
    #             r=100,  # Add right margin to accommodate the legend
    #             b=100,  # Add bottom margin
    #             t=100  # Add top margin
    #         ),
    #         autosize=True

    #     )

    #     fig2 = px.bar(df, x="taxonomy", y="abundance", color="sample_id", barmode="stack")
    #     return fig1, fig2

    def plot_grouped_bar(self, df):
        # Plotting code for grouped bar goes here...
        fig1 = px.bar(df, x="sample_id", y="abundance", color="taxonomy", barmode="group")

        return fig1

    def plot_scatter(self, df):
        fig1 = px.scatter(df, x="sample_id", y="abundance", size="abundance", color="sample_id")
        fig2 = px.scatter(df, x="taxonomy", y="sample_id", size="abundance", color="sample_id")
        fig2_style = {'display': 'none'}

        return fig1

    def plot_area(self, df):
        # Plotting code for area plot goes here...
        fig1 = px.area(df, x="sample_id", y="abundance", color="taxonomy", line_group="taxonomy")

        return fig1

    def plot_scatter_3d(self, df):
        # Plotting code for scatter 3D goes here...
        fig1 = px.scatter_3d(df, x='taxonomy', y='abundance', z='sample_id', color='taxonomy')

        return fig1

    def plot_pie(self, df, sample_value_piechart):
        # Plotting code for pie chart goes here...
        pie_values = df.loc[df["sample_id"] == sample_value_piechart, 'abundance']
        pie_names = df.loc[df["sample_id"] == sample_value_piechart, 'taxonomy']
        fig1 = px.pie(df, values=pie_values, names=pie_names,
                      title=f'Pie chart of bioreactor taxonomy of sample {sample_value_piechart}')
        piechart_style = {'display': 'block'}

        fig2_style = {'display': 'none'}
        return fig1, piechart_style

    def _init_callbacks(self) -> None:
        """
        Initialize the callbacks for the app.

        The callbacks include updating the figures when the dropdown value, piechart value, or slider value changes,
        and downloading the CSV when the download button is clicked.
        """

        # this updates the graph based on the samples selected
        print("init callbacks in taxonomy pie called")

        @self.app.callback(
            Output('graph1', 'figure'),
            Output('graph2', 'figure'),
            # this output hides the pie chart number input when no pie chart is plotted
            Output('number_input_piechart', 'style'),
            # hides 2nd plot for pie chart
            Output('graph2', 'style'),
            Output('markdown-caption', 'style'),
            Input('dropdown', 'value'),
            Input('number_input_piechart', 'value'),
            Input('slider', 'value'),
            Input('sample_select_value', 'value')

        )
        def plot_selected_figure(value, sample_value_piechart, slider_value, sample_select_value) -> Tuple[
            Figure, Figure, Dict[str, str]]:
            """
            Update the figures based on the selected value from the dropdown menu, the selected sample value for the piechart,
            and the selected number of taxa from the slider.

            Args:
            value (str): The selected value from the dropdown menu.
            sample_value_piechart (str): The selected sample value for the piechart.
            slider_value (int): The selected number of taxa from the slider.
            sample_select_value: (str) output of multi select dropdown (selected samples)

            Returns:
                Tuple[Figure, Figure, Dict[str, str]]: A tuple containing two figures for the graphs and a dict for the piechart style.
            """
            # fallback values
            # Check if sample_select_value is None or empty list

            # if not value or not sample_value_piechart or not slider_value or not sample_select_value:
            #     raise PreventUpdate

            fig1 = {'data': []}
            fig2 = {'data': []}
            piechart_style = {'display': 'none'}

            fig2_style = {'display': 'block'}

            # request necessary data from database
            # q = "SELECT sample_id, taxonomy, abundance FROM mmonitor"
            # df = self._sql.query_to_dataframe(q)
            df_sorted = self.df.sort_values("abundance", ascending=False)
            df_grouped = df_sorted.groupby("sample_id")
            result_df = pd.DataFrame()
            for name, group in df_grouped:
                # get most abundant for slider_value number of selected taxa for each sample to display in taxonomy plots
                sample_rows = group.head(slider_value)
                result_df = pd.concat([result_df, sample_rows])

            result_df = result_df.reset_index(drop=True)
            self.result_df = result_df
            self.df_selected = self.result_df[self.result_df['sample_id'].astype(str).isin(sample_select_value)]

            if value == 'stackedbar':
                fig1 = self.plot_stacked_bar(self.df_selected)

            elif value == 'groupedbar':
                fig1 = self.plot_grouped_bar(self.df_selected)

            elif value == 'scatter':
                fig1, fig2, fig2_style = self.plot_scatter(self.df_selected)

            elif value == 'area':
                fig1, fig2_style = self.plot_area(self.df_selected)

            elif value == 'scatter3d':
                fig1, fig2 = self.plot_scatter_3d(self.df_selected)

            elif value == "pie":
                fig1, piechart_style, fig2_style = self.plot_pie(self.result_df, sample_value_piechart)

            return fig1, fig2, piechart_style, fig2_style, fig2_style
            # fig2_style,fig2_style 2nd fi2_style used for hiding markdown caption

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
