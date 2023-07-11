import base64
from io import StringIO
from typing import Tuple, List, Any, Dict

import pandas as pd
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
        q = f"SELECT * FROM mmonitor"
        self.df = self._sql.query_to_dataframe(q)
        self.df_sorted = self.df.sort_values(by=["sample_id", "abundance"], ascending=[True, False])

        # Get the number of unique values in each column
        # get number of unique taxonomies for creation of slider. limit max taxa to plot to 100
        self.unique_counts = self.df.nunique()[1]
        if self.unique_counts > 100:
            self.unique_counts = 100

        self._init_layout()
        self._init_callbacks()

    def _init_layout(self) -> None:
        """
        Taxonomy app layout consists of two graphs visualizing the abundances
        of taxonomies and an optional pie chart as well as a data table for
        debugging purposes.
        """

        header = html.H1(children='Taxonomic composition')

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
            style={"max-width": "50%", "height": "auto"},
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

        header_pie_chart_sample_select = html.H1(children='Select a sample to display.')

        slider_header = html.H1(children='Select the number of taxa to display:')
        slider = dcc.Slider(
            id='slider',
            min=1,
            max=self.unique_counts,  # Adjust this based on the range of values in your data
            value=1,
            marks={i: str(i) for i in range(1, self.unique_counts + 1)},  # Adjust marks based on your data
            step=1
        )


        pie_chart_input = dcc.Dropdown(
            id='number_input_piechart',
            options=[{'label': t, 'value': t} for t in self._sql.get_unique_samples()],
            value=self._sql.get_unique_samples()[0],
            style={'display': 'none'},
            clearable=False,
        )

        # data table for debugging
        db_header = html.H4(children="Database")
        data, columns = self._generate_table_data_cols()
        data_tb = dash_table.DataTable(id='table-correlations', data=data, columns=columns)

        download_button = html.Button("Download CSV", id="btn-download")
        download_component = dcc.Download(id="download-csv")

        CONTENT_STYLE = {

            "margin-right": "2rem",
            "padding": "2rem 1rem",
            'margin-bottom': '200px',
            'font-size': '25px'
        }

        container = html.Div(
            [header, demo_dd, slider_header, slider, graph1, graph2, header_pie_chart_sample_select, pie_chart_input,
             db_header,
             download_button, download_component, data_tb], style=CONTENT_STYLE)
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
            Input('slider', 'value')

        )
        def plot_selected_figure(value, sample_value_piechart, slider_value) -> Tuple[Figure, Figure, Dict[str, str]]:
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
            df_sorted = df.sort_values("abundance", ascending=False)
            df_grouped = df_sorted.groupby("sample_id")
            result_df = pd.DataFrame()
            for name, group in df_grouped:
                # get most abundant for slider_value number of selected taxa for each sample to display in taxonomy plots
                sample_rows = group.head(slider_value)
                # result_df = result_df.append(sample_rows)
                result_df = pd.concat([result_df, sample_rows])

            result_df = result_df.reset_index(drop=True)
            self.result_df = result_df

            if value == 'stackedbar':
                fig1 = px.bar(result_df, x="sample_id", y="abundance", color="taxonomy", barmode="stack")
                fig1.update_layout(
                    legend=dict(
                        orientation="v",
                        y=1,
                        x=1.1
                    ),
                    margin=dict(
                        l=100,  # Add left margin to accommodate the legend
                        r=100,  # Add right margin to accommodate the legend
                        b=100,  # Add bottom margin
                        t=100  # Add top margin
                    ),
                    width=2000,
                    height=1000
                )

                fig2 = px.bar(result_df, x="taxonomy", y="abundance", color="sample_id", barmode="stack")

            elif value == 'groupedbar':
                fig1 = px.bar(result_df, x="sample_id", y="abundance", color="taxonomy", barmode="group")
                fig2 = px.bar(result_df, x="taxonomy", y="abundance", color="sample_id", barmode="group")

            elif value == 'scatter':
                fig1 = px.scatter(result_df, x="sample_id", y="abundance", size="abundance", color="sample_id")
                fig2 = px.scatter(result_df, x="taxonomy", y="abundance", size="sample_id", color="sample_id")

            elif value == 'area':
                fig1 = px.area(result_df, x="sample_id", y="abundance", color="taxonomy", line_group="taxonomy")
                # fig2 = fig

            elif value == 'scatter3d':
                fig1 = px.scatter_3d(result_df, x='taxonomy', y='abundance', z='sample_id', color='taxonomy')

                fig2 = px.scatter_3d(result_df, x='abundance', y='taxonomy', z='sample_id', color='sample_id')

            elif value == "pie":
                pie_values = result_df.loc[df["sample_id"] == sample_value_piechart, 'abundance']
                pie_names = result_df.loc[df["sample_id"] == sample_value_piechart, 'taxonomy']
                fig1 = px.pie(result_df, values=pie_values, names=pie_names,
                              title=f'Pie chart of bioreactor taxonomy of sample {sample_value_piechart}')
                # pie_values = df.loc[df["sample_id"] == sample_value_piechart + 1, 'abundance']
                # pie_names = df.loc[df["sample_id"] == sample_value_piechart + 1, 'taxonomy']
                # fig2 = px.pie(df, values=pie_values, names=pie_names,
                #               title=f'Pie chart of bioreactor taxonomy of sample {sample_value_piechart + 1}')
                piechart_style = {'display': 'block'}
                fig2_style = {'display': 'none'}

            return fig1, fig2, piechart_style, fig2_style

        @app.callback(
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
