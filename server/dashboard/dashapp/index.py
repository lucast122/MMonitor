from dash import dcc
from dash import html
from dash.dependencies import Input, Output
from dash.exceptions import PreventUpdate
from flask import request
from django_plotly_dash import DjangoDash
import pandas as pd
import plotly.express as px
from typing import Tuple, List, Any, Dict
from plotly.graph_objects import Figure
import plotly.graph_objects as go

# from mmonitor.dashapp.app import app
# from mmonitor.dashapp.apps import correlations, taxonomy, horizon, kegg, genome_browser
# from mmonitor.dashapp.base_app import BaseApp
# from mmonitor.database.mmonitor_db import MMonitorDBInterface
from . import kraken, taxonomy, correlations,horizon
from json import loads, dumps
# from .database.mmonitor_db import MMonitorDBInterfaceSQL
import dash_bootstrap_components as dbc
from . import simple
from . import kraken
from dash import callback_context
from io import StringIO
import base64
from django.db import connections
from typing import Tuple, Any, List, Iterable, Dict, Union

from scipy.ndimage.filters import gaussian_filter

from django_plotly_dash import DjangoDash

import plotly.express as px
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash_table import DataTable
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
from pandas import DataFrame
from plotly.graph_objects import Figure

from .calculations.stats import scipy_correlation

def _explode_metadata(df):
    return pd.concat([df, df['data'].apply(_parse_dict)], axis=1).drop(columns='data')

def _parse_dict(x):
    return pd.Series(loads(x))


class Index():
    """
    Landing page of the dash application.
    Contains navigation to the various application pages.
    """

    def __init__(self):
        self._table_df = None

        # self._sql = sql
        self.app = DjangoDash('Index', external_stylesheets=['/dash/static/bWLwgP.css'])
        correlations_app = correlations.Correlations()
        with connections['mmonitor'].cursor() as cursor:
            raw_connection = cursor.db
            self.conn = cursor.db.connection

            # Define your query
            q = "SELECT * FROM nanopore"

            # Use pandas to execute the query and store the result in a DataFrame
            self.df = pd.read_sql_query(q, self.conn)
            self.meta_df = correlations_app.get_all_meta()
            self.df['sample_id'] = self.df['sample_id'].astype(str)

            self.meta_df['sample_id'] = self.meta_df['sample_id'].astype(str)   
            self.df_merged = self.df.merge(self.meta_df, on="sample_id", how="left")

        self.metadata_columns = self.meta_df.columns.tolist()

        self.hover_data = {column: True for column in self.metadata_columns}
        self.metadata_columns.pop(0)
        

            

        
        # q = f"SELECT * FROM mmonitor"
        # self.df = pd.read_sql_query(q,conn)

        self.df_sorted = self.df.sort_values("abundance", ascending=False)
        self.df_grouped = self.df_merged.groupby("sample_id")
        self.result_df = pd.DataFrame()

        # Initialize apps
        taxonomy_app = taxonomy.Taxonomy()
        horizon_app = horizon.Horizon()
        
        # simple_app = simple.SimpleApp()
        # kraken_app = kraken.Kraken()

        # taxonomy_app._init_layout()

        self._apps = {
        '/dashapp/taxonomy': {
                'name': 'Taxonomy',
                'app': taxonomy_app.app,
                'instance': taxonomy_app
            },
        '/dashapp/horizon': {
            'name': 'Horizon',
            'app': horizon_app.app,
            'instance': horizon_app
        },
        
            '/dashapp/correlations': {
                'name': 'Correlations',
                'app': correlations_app.app,
                'instance': correlations_app
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
        

        # Initialize callbacks for each app
        # for app_info in self._apps.values():
        #     print(f"Initializing callbacks for {app_info['name']} app")
        #     app_info['instance']._init_callbacks()

        # Initialize Index callbacks
        self._init_callbacks()
        print("Initialized Index callbacks")


        

        for app_info in self._apps.values():
            print("appinfo instance")
            print(app_info['instance'])
            app_info['instance']._init_layout()
            # app_info['instance']._init_callbacks()




        # print(f"After init {self.app}")

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
            dcc.Link(values['name'], href=url, style={'padding': '10px', 'font-size': "30px", "font-weight" : "bold",  "hover" : "#B22222:"})
            for url, values in self._apps.items()
        ], className="row")
        page_content = html.Div(id='page-content', children=[])
        # graph1 = dcc.Graph(id='graph1', figure={'data': []})
        container = html.Div([location, navigation, page_content])
        
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


    def plot_stacked_bar(self, df):
        # metadata_columns = [col for col in self.df.columns if col not in ["sample_id", "abundance", "taxonomy"]]
        


        fig1 = px.bar(df, x="sample_id", y="abundance", color="taxonomy", barmode="stack", hover_data=self.hover_data)

        fig1.update_layout(
            legend=dict(
                orientation="v",
                y=1,
                x=1.1
            ),
                clickmode='event+select',
            margin=dict(
                l=100,  # Add left margin to accommodate the legend
                r=100,  # Add right margin to accommodate the legend
                b=100,  # Add bottom margin
                t=100  # Add top margin
            ),
            autosize=True
            
        )

        fig2 = px.bar(df, x="taxonomy", y="abundance", color="sample_id", barmode="stack",hover_data=self.hover_data)
        return fig1, fig2

    def plot_grouped_bar(self, df):
        # Plotting code for grouped bar goes here...
        fig1 = px.bar(df, x="sample_id", y="abundance", color="taxonomy", barmode="group",hover_data=self.hover_data)
        fig2 = px.bar(df, x="taxonomy", y="abundance", color="sample_id", barmode="group",hover_data=self.hover_data)

        return fig1, fig2

    def plot_scatter(self, df):
        fig1 = px.scatter(df, x="sample_id", y="abundance", size="abundance", color="sample_id",hover_data=self.hover_data)
        fig2 = px.scatter(df, x="taxonomy", y="sample_id", size="abundance", color="sample_id",hover_data=self.hover_data)
        fig2_style = {'display': 'block'}
        return fig1,fig2,fig2_style

    def plot_area(self, df):
        # Plotting code for area plot goes here...
        fig1 = px.area(df, x="sample_id", y="abundance", color="taxonomy", line_group="taxonomy",hover_data=self.hover_data)
        fig2 = px.area(df, x="sample_id", y="abundance", color="abundance", line_group="abundance",hover_data=self.hover_data)
        fig2_style = {'display': 'none'}
        return fig1,fig2,fig2_style

    def plot_scatter_3d(self, df):
        # Plotting code for scatter 3D goes here...
        fig1 = px.scatter_3d(df, x='taxonomy', y='abundance', z='sample_id', color='taxonomy',hover_data=self.hover_data)
        fig2 = px.scatter_3d(df, x='abundance', y='taxonomy', z='sample_id', color='abundance',hover_data=self.hover_data)
        return fig1, fig2

    def plot_pie(self, df,sample_value_piechart):
        # Plotting code for pie chart goes here...
        pie_values = df.loc[df["sample_id"] == sample_value_piechart, 'abundance']
        pie_names = df.loc[df["sample_id"] == sample_value_piechart, 'taxonomy']
        fig1 = px.pie(df, values=pie_values, names=pie_names,
                      title=f'Pie chart of bioreactor taxonomy of sample {sample_value_piechart}')
        piechart_style = {'display': 'block'}
        
        fig2_style = {'display': 'none'}
        return fig1, piechart_style, fig2_style


    """
    Index callback
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
                app._init_callbacks()  # ensure callbacks are registered
                return app.app.layout
            # otherwise it's page not found
            else:
                return "404 Page Error! Please choose a link"

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

    
    
        """
        Taxonomy callbacks
        """



        #GROUP SELECTION CALLBACKS

        @self.app.callback(
        Output('selected-data', 'children'),
        Input('graph1', 'selectedData')
    )
        def display_selected_data(selectedData):
            if selectedData is None:
                return "No taxa selected"

        # Extract the taxa from the selected data
            selected_taxa = [point['customdata'][0] for point in selectedData['points']]

            return f"Selected taxa: {', '.join([str(taxon) for taxon in selected_taxa])}"



        #this enables the group selection components when the checkbox is clicked
        @self.app.callback(
        Output('group-name-input', 'style'),
        Output('create-group-button', 'style'),
        Output('group-selection-dropdown', 'style'),
        Input('enable-group-selection', 'value')
        )
        def toggle_group_selection(enable_group_selection):
            if 'enabled' in enable_group_selection:
                style = {'display': 'block'}
                print("enabled")
            else:
                style = {'display': 'none'}
                print('disabled')
            return style, style, style


        @self.app.callback(
        Output('group-storage', 'data'),
        Input('create-group-button', 'n_clicks'),
        State('group-name-input', 'value'),
        State('graph1', 'selectedData'),
        State('group-storage', 'data')
        )
        def create_group(n_clicks, group_name, selected_data, stored_data):
            if n_clicks is None:
                raise PreventUpdate

            if group_name is None or group_name == '' or selected_data is None:
                return stored_data

            if stored_data is None:
                stored_data = {}

            # Extract the taxa from the selected data
            selected_taxa = [point['customdata'][1] for point in selected_data['points']]
            print(selected_data['points'])


            # Add the selected taxa to the group
            stored_data[group_name] = selected_taxa

            return stored_data
        @self.app.callback(
        Output('group-selection-dropdown', 'options'),
        Input('group-storage', 'data')
    )
        def update_group_selection_dropdown(data):
            if data is None:
                raise PreventUpdate
            return [{'label': group, 'value': group} for group in data.keys()]


        #this updates the plot based on selected groups



        #this updates the graph based on the samples selected 
        
        @self.app.callback(
            Output('graph1', 'figure'),
            Output('graph2', 'figure'),
            # this output hides the pie chart number input when no pie chart is plotted
            Output('number_input_piechart', 'style'),
            # hides 2nd plot for pie chart
            Output('graph2', 'style'),
            Input('dropdown', 'value'),
            Input('number_input_piechart', 'value'),
            Input('slider', 'value'),
            Input('sample_select_value', 'value')

        )
        def plot_selected_figure(value, sample_value_piechart, slider_value, sample_select_value) -> Tuple[Figure, Figure, Dict[str, str]]:
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
            
            # print("Triggered by:", callback_context.triggered)
            # print("Current state:", callback_context.states)
            # print(value)
            # print(sample_select_value)
            # print(slider_value)
            # print(sample_value_piechart)

            # if not value or not sample_value_piechart or not slider_value:
                # raise PreventUpdate


            fig1 = {'data': []}
            fig2 = {'data': []}
            piechart_style = {'display': 'none'}

            fig2_style = {'display': 'block'}
            # request necessary data from database
            # q = "SELECT sample_id, taxonomy, abundance FROM mmonitor"
            # df = self._sql.query_to_dataframe(q)
            
            
            result_df = pd.DataFrame()
            for name, group in self.df_grouped:
                # get most abundant for slider_value number of selected taxa for each sample to display in taxonomy plots
                sample_rows = group.head(slider_value)
                result_df = pd.concat([result_df, sample_rows])

            result_df = result_df.reset_index(drop=True)
            self.result_df = result_df
            self.df_selected = self.result_df[self.result_df['sample_id'].astype(str).isin(sample_select_value)]
            # print(self.df_selected)
            


            if value == 'stackedbar':
                fig1, fig2 = self.plot_stacked_bar(self.df_selected)

            elif value == 'groupedbar':
                fig1, fig2 = self.plot_grouped_bar(self.df_selected)

            elif value == 'scatter':
                fig1,fig2,fig2_style = self.plot_scatter(self.df_selected)

            elif value == 'area':
                fig1,fig2,fig2_style = self.plot_area(self.df_selected)

            elif value == 'scatter3d':
                fig1,fig2 = self.plot_scatter_3d(self.df_selected)

            elif value == "pie":
                fig1, piechart_style, fig2_style = self.plot_pie(self.result_df,sample_value_piechart)
            elif value == "horizon":
                fig1 = self.plot_pseudo_horizon(self.df_selected)


            return fig1, fig2, piechart_style, fig2_style


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
        def _update_graphs(taxonomy: str, method: str, test: str) -> Tuple[Figure, Figure]:
            """
            Populate the correlations and probability graphs
            according to dropdown selections.
            """

            # request data from database and filter columns containing metadata
            # abundance and metadata tables are joined to align entries by their sample_ids
            df = self.get_abundance_meta_by_taxonomy(taxonomy)
            # metadata_columns = [col for col in df.columns if col not in ['sample_id', 'abundance', 'meta_id', 'project_id']]

            # for each metadata calculate the correlation and probability
            # transpose the list of tuples and extract each a correlation and a probability list:
            # [(c1, p1), (c2, p2), (c3, p3), ...] -> [c1, c2, c3, ...], [p1, p2, p3, ...]
            
            print("METADATA COLUMNS")
            # print(df[meta])
            print(test)
            print(method)
            print(self.metadata_columns)

            # print(self.metadata_columns)
            
            y_axis_tuple = [scipy_correlation(df['abundance'], df[meta], test, method) for meta in self.metadata_columns]
            print(y_axis_tuple)
            
            print()
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

            # for each selected taxonomy
            for taxonomy in taxonomies:

                # request corresponding abundances from database
                tax_df = self.get_abundance_by_taxonomy(taxonomy)
                tax_df['sample_id'] = tax_df['sample_id'].astype(str)
                self.meta_df['sample_id'] = self.meta_df['sample_id'].astype(str)
                # print("ASDF")
                # print(tax_df['sample_id'].dtype)
                # print(self.meta_df['sample_id'].dtype)



                merged_df = tax_df.merge(self.meta_df, on='sample_id', how='outer', suffixes=('_t', '_m'))
                merged_df = merged_df.dropna(subset=['abundance'])



                # for each selected method
                for method in methods:

                    # prepare the row containing correlation scores per metadata
                    # and the rows containing the corresponding probabilities
                    # of the correlation score per metadata according to the selected tests
                    score_row = {'Taxonomy': taxonomy, 'Method or Test': method}
                    test_rows = {t: {'Taxonomy': taxonomy, 'Method or Test': ' '.join([method, t])} for t in tests}

                    # for each metadata available in the database
                    for meta in meta_cols:
                        merged_df = merged_df.dropna(subset=[meta])


                        # calculate the correlation score and its probability
                        # according to the selected tests
                        # print("blaa")
                        # print(taxonomy)
                        # print(meta)
                        # print(merged_df['abundance'])






                        try:
                            score, test_scores = scipy_correlation(merged_df['abundance'], merged_df[meta], tests, method)
                        except ValueError as e:
                            print("Can't calculate correlation for taxa that are only present in one sample.")
                            continue

                        # populate the row containing correlation scores per metadata
                        score_row[meta] = score

                        # then populate the rows containing the corresponding probabilities
                        # of the correlation score per metadata according to the selected tests
                        for test, test_score in test_scores.items():
                            test_rows[test][meta] = test_score

                    # finally append the correlation row and the probability rows to the dataframe
                    df = pd.concat([df, pd.DataFrame([score_row])], ignore_index=True)
                    for test, test_row in test_rows.items():
                        df = pd.concat([df, pd.DataFrame([test_row])], ignore_index=True)



            # return data for the dash data table according to
            # https://dash.plotly.com/datatable
            self._table_df = df
            return [{"name": i, "id": i} for i in df.columns], df.to_dict('records'), taxonomies


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



    def get_abundance_meta_by_taxonomy(self, taxonomy) -> pd.DataFrame:
        if isinstance(taxonomy, list):
            taxonomy = taxonomy[0]

        q = f"""
            SELECT nanopore.sample_id, nanopore.abundance, metadata.*
            FROM nanopore
            INNER JOIN metadata
            ON nanopore.sample_id = metadata.sample_id
            WHERE nanopore.taxonomy = '{taxonomy}'
            ORDER BY nanopore.sample_id
        """

        return _explode_metadata(self.query_to_dataframe(q))

    def get_abundance_by_taxonomy(self, taxonomy: str) -> pd.DataFrame:
        if isinstance(taxonomy, list):
            taxonomy = taxonomy[0]

        q = f"SELECT sample_id, abundance FROM nanopore WHERE taxonomy = '{taxonomy}' ORDER BY sample_id"
        return self.query_to_dataframe(q)


    def query_to_dataframe(self,query: str) -> pd.DataFrame:
        return pd.read_sql_query(query, self.conn)

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

    # def run_server(self, debug: bool) -> None:
    #     """
    #     Runs the dash app.
    #     """
    #     self._app.run_server(debug=debug)
