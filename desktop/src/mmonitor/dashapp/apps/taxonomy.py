from typing import Tuple, List, Any, Dict

import plotly.express as px
from dash import dash_table
from dash import dcc
from dash import html
from dash.dependencies import Input, Output
from plotly.graph_objects import Figure

from mmonitor.dashapp.app import app
from mmonitor.dashapp.base_app import BaseApp
from mmonitor.database.mmonitor_db import MMonitorDBInterface


class Taxonomy(BaseApp):
    """
    App to display the abundances of taxonomies in various formats.
    """

    def __init__(self, sql: MMonitorDBInterface):
        super().__init__(sql)
        self._init_layout()
        self._init_callbacks()

    def _init_layout(self) -> None:
        """
        Taxonomy app layout consists of two graphs visualizing the abundances
        of taxonomies and an optional pie chart as well as a data table for
        debugging purposes.
        """

        maira_header = html.H1(children='Taxonomic composition')

        # dropdown menu to select chart type
        # initialize as stacked bar chart
        demo_dd = dcc.Dropdown(
            id='dropdown',
            options=[
                {'label': 'Stacked Barchart', 'value': 'stackedbar'},
                {'label': 'Grouped Barchart', 'value': 'groupedbar'},
                {'label': 'Area plot', 'value': 'area'},
                {'label': 'Pie chart', 'value': 'pie'},
                {'label': 'Scatter 3D', 'value': 'scatter3d'}],
                    style={"max-width" : "50%", "height" : "auto"},
                    value='stackedbar'
        )


        # graph elements
        graph1 = dcc.Graph(id='graph1', figure={'data': []})
        graph2 = dcc.Graph(id='graph2', figure={'data': []})

        # pie chart options will be displayed
        # if pie chart is selected in the dropdown menu
        # pie_chart_input = dcc.Input(
        #     id='number_input_piechart',
        #     type='number',
        #     placeholder="Sample ID",
        #     value=1,
        #     style={'display': 'none'}
        # )

        pie_chart_input = dcc.Dropdown(
            id='number_input_piechart',
            options=[{'label': t, 'value': t} for t in self._sql.get_unique_samples()],
            value=self._sql.get_unique_samples()[1],
            style={'display': 'none'},
            clearable=False,
        )

        # data table for debugging
        db_header = html.H4(children="Database")
        data, columns = self._generate_table_data_cols()
        data_tb = dash_table.DataTable(id='table-correlations', data=data, columns=columns)

        CONTENT_STYLE = {

            "margin-right": "2rem",
            "padding": "2rem 1rem",
            'margin-bottom': '200px',
            'font-size': '25px'
        }

        container = html.Div([maira_header, demo_dd, graph1, graph2, pie_chart_input, db_header, data_tb],style=CONTENT_STYLE)
        self.layout = container

    def _generate_table_data_cols(self, max_rows=40) -> Tuple[List[Any], List[Any]]:
        """
        Generate data to populate a dash data table with.
        A dash data table requires the data in a dict format
        as well as a collection of mapped column names.
        """

        q = f"SELECT * FROM mmonitor LIMIT {max_rows}"
        df = self._sql.query_to_dataframe(q)
        return df.to_dict('records'), [{'name': i, 'id': i} for i in df.columns]

    def _init_callbacks(self) -> None:
        @app.callback(
            Output('graph1', 'figure'),
            Output('graph2', 'figure'),
            # this output hides the pie chart number input when no pie chart is plotted
            Output('number_input_piechart', 'style'),
            # hides 2nd plot for pie chart
            Output('graph2', 'style'),
            Input('dropdown', 'value'),
            Input('number_input_piechart', 'value'),
        )
        def plot_selected_figure(value, sample_value_piechart) -> Tuple[Figure, Figure, Dict[str, str]]:
            """
            Populate graph1 and graph2 elements with selected plots
            and en/disable input options for the pie chart accordingly.
            """

            # fallback values
            fig1 = {'data': []}
            fig2 = {'data': []}
            piechart_style = {'display': 'none'}
            fig2_style = {'display': 'block'}
            # request necessary data from database
            q = "SELECT sample_id, taxonomy, abundance FROM mmonitor"
            df = self._sql.query_to_dataframe(q)

            if value == 'stackedbar':
                fig1 = px.bar(df, x="sample_id", y="abundance", color="taxonomy", barmode="stack")
                fig2 = px.bar(df, x="taxonomy", y="abundance", color="sample_id", barmode="stack")

            elif value == 'groupedbar':
                fig1 = px.bar(df, x="sample_id", y="abundance", color="taxonomy", barmode="group")
                fig2 = px.bar(df, x="taxonomy", y="abundance", color="sample_id", barmode="group")

            elif value == 'scatter':
                fig1 = px.scatter(df, x="sample_id", y="abundance", size="abundance", color="sample_id")
                fig2 = px.scatter(df, x="taxonomy", y="abundance", size="sample_id", color="sample_id")

            elif value == 'area':
                fig1 = px.area(df, x="sample_id", y="abundance", color="taxonomy", line_group="taxonomy")
                # fig2 = fig

            elif value == 'scatter3d':
                fig1 = px.scatter_3d(df, x='taxonomy', y='abundance', z='sample_id', color='taxonomy')
                fig2 = px.scatter_3d(df, x='abundance', y='taxonomy', z='sample_id', color='sample_id')


            elif value == "pie":
                pie_values = df.loc[df["sample_id"] == sample_value_piechart, 'abundance']
                pie_names = df.loc[df["sample_id"] == sample_value_piechart, 'taxonomy']
                fig1 = px.pie(df, values=pie_values, names=pie_names,
                              title=f'Pie chart of bioreactor taxonomy of sample {sample_value_piechart}')
                # pie_values = df.loc[df["sample_id"] == sample_value_piechart + 1, 'abundance']
                # pie_names = df.loc[df["sample_id"] == sample_value_piechart + 1, 'taxonomy']
                # fig2 = px.pie(df, values=pie_values, names=pie_names,
                #               title=f'Pie chart of bioreactor taxonomy of sample {sample_value_piechart + 1}')
                piechart_style = {'display': 'block'}
                fig2_style = {'display': 'none'}

            return fig1, fig2, piechart_style, fig2_style
