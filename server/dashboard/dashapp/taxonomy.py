from typing import Tuple, List, Any, Dict

import base64
from io import StringIO
import pandas as pd
from django_plotly_dash import DjangoDash

import plotly.express as px
import dash_core_components as dcc
from dash import html
from dash.dependencies import Input, Output
from plotly.graph_objects import Figure
from dash import dash_table
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
from dash import callback_context
from django.db import connections


class Taxonomy:
    """
    App to display the abundances of taxonomies in various formats.
    """

    def __init__(self):
        
        self.app = DjangoDash('taxonomy')
        
        

        with connections['mmonitor'].cursor() as cursor:

            raw_connection = cursor.db
            conn = cursor.db.connection
            self.unique_sample_ids = pd.read_sql_query("SELECT DISTINCT sample_id FROM nanopore",conn)["sample_id"].tolist()
            print(f"Unique sample ids{self.unique_sample_ids}")

            # Define your query
            q = "SELECT * FROM nanopore"

            # Use pandas to execute the query and store the result in a DataFrame
            self.df = pd.read_sql_query(q, conn)
            self.unique_samples = pd.read_sql_query("SELECT DISTINCT sample_id FROM nanopore",conn)
            print(f"Unique samples{self.unique_samples}")


        
        
        self.df_sorted = self.df.sort_values(by=["sample_id", "abundance"], ascending=[True, False])

        # Get the number of unique values in each column
        # get number of unique taxonomies for creation of slider. limit max taxa to plot to 100
        self.unique_counts = min(self.df.nunique()[1], 100)

        self._init_layout()
        self._init_callbacks()


    def _init_layout(self) -> None:
        """
        Taxonomy app layout consists of two graphs visualizing the abundances
        of taxonomies and an optional pie chart as well as a data table for
        debugging purposes.
        """
        selected_taxa = html.Div(id='selected-data')


        header = dbc.Row(
        dbc.Col(html.H1(children='Taxonomic composition'), width={'size': 12, 'offset': 0}),
        justify="center",
            )

        

        sample_select_dropdown= dbc.Col(
        dcc.Dropdown(
            id='sample_select_value',
            options=[{'label': i, 'value': i} for i in self.unique_sample_ids],
            multi=True  # allow multiple selections
        ),
        width={"size": 8, "offset": 0}
        )
        

        sample_select_dropdown_text = dbc.Row([
        dbc.Col(
        dbc.Label("Samples to plot:",html_for='sample_select_value',id='sample_select_text'),
        width={"size": 1, "offset": 0}
        )])




        # dropdown menu to select chart type
        # initialize as stacked bar chart
        demo_dd = dbc.Row([
        dbc.Col(
        dbc.Label("Plot type:",html_for='dropdown'),
        width={"size": 1, "offset": 0}
            ),
        dbc.Col(
        dcc.Dropdown(
            id='dropdown',
            options=[
                {'label': 'Stacked Barchart', 'value': 'stackedbar'},
                {'label': 'Grouped Barchart', 'value': 'groupedbar'},
                {'label': 'Area plot', 'value': 'area'},
                {'label': 'Pie chart', 'value': 'pie'},
                {'label': 'Scatter plot', 'value': 'scatter'},
                {'label': 'Scatter 3D', 'value': 'scatter3d'},
                {'label': 'Horizon plot', 'value': 'horizon'}],
            value='stackedbar'
                ),
                width={"size": 3, "offset": 0}
            ),
        ], justify="start")


        group_select = html.Div([
        dcc.Checklist(
            id='enable-group-selection',
            options=[{'label': 'Enable Group Selection', 'value': 'enabled'}],
            value=[]
        ),
        dcc.Input(
            id='group-name-input',
            type='text',
            placeholder='Enter group name',
            style={'display': 'none'}
        ),
        html.Button(
            'Create Group',
            id='create-group-button',
            style={'display': 'none'}
        ),
        dcc.Dropdown(
            id='group-selection-dropdown',
            placeholder='Select a group',
            style={'display': 'none'}
        ),
        dcc.Store(id='group-storage', storage_type='local')
        ])




            # graph elements
        graph1 = dcc.Graph(id='graph1',  figure={
        'data': [],  # Replace with your data
        'layout': {
            'clickmode': 'event+select',
            # Add the rest of your layout properties here...
        }}
            )
        graph2 = dcc.Graph(id='graph2', figure={'data': []})

        header_pie_chart_sample_select_dbc = dbc.Row(
            dbc.Col(html.H1(children='Select a sample to display.'), width={'size': 10, 'offset': 0}),justify="center",style = {'display': 'none'},id='header_pie_chart_sample_select_dbc')

        slider_header = dbc.Row(
            dbc.Col(        html.H1(children='Select the number of taxa to display:'), width={'size': 12, 'offset': 0}),justify="start")


        slider = html.Div([
    dbc.Row(
        dbc.Col(
            dcc.Slider(
                id='slider',
                min=1,
                max=self.unique_counts,
                value=10,
                marks={
                    i: str(i) if i in [1, self.unique_counts // 2, self.unique_counts] else "" 
                    for i in range(1, self.unique_counts + 1)
                },
                step=1
            ), 
            width={'size': 10, 'offset': 0}
        ),
        justify='start'
    ),
      
])


        pie_chart_input = dcc.Dropdown(
            id='number_input_piechart',
            options=[{'label': t, 'value': t} for t in self.unique_samples],
            
            style={'display': 'none'},
            clearable=False,
        )

        # data table for debugging

        db_header = dbc.Row(dbc.Col(html.H4(children="Database"), width={'size': 12, 'offset': 0}),justify="center")
        data, columns = self._generate_table_data_cols()
        data_tb = dbc.Row(dbc.Col(dash_table.DataTable(id='table-correlations', data=data, columns=columns), width={'size': 12, 'offset': 0}),justify="center")

        download_button = dbc.Button("Download CSV", id="btn-download")
        download_component = dcc.Download(id="download-csv")


        container = dbc.Container(
    [   selected_taxa,
        header, 
        sample_select_dropdown_text,
        sample_select_dropdown,
        demo_dd, group_select, 
        graph1,
        graph2,
        slider_header, 
        slider, 
        header_pie_chart_sample_select_dbc, 
        pie_chart_input,
        db_header,
        download_button, 
        download_component, 
        data_tb
    ], 
    fluid=True
)

        self.app.layout = container

    def _generate_table_data_cols(self, max_rows=40) -> Tuple[List[Any], List[Any]]:
        """
        Generate data to populate a dash data table with.
        A dash data table requires the data in a dict format as well as a collection of mapped column names.

        Args:
        max_rows (int, optional): The maximum number of rows to include in the table. Defaults to 40.

        Returns:
        Tuple[List[Any], List[Any]]: A tuple containing the data for the table in dict format and a collection of mapped column names.
        """
        with connections['mmonitor'].cursor() as cursor:

            raw_connection = cursor.db
            conn = cursor.db.connection
            
        

            # Use pandas to execute the query and store the result in a DataFrame
            q = f"SELECT * FROM nanopore LIMIT {max_rows}"
            self.df = self.df = pd.read_sql_query(q, conn)
            print(self.df)
        
                
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
        fig2 = px.bar(df, x="taxonomy", y="abundance", color="sample_id", barmode="group")

        return fig1, fig2

    def plot_scatter(self, df):
        fig1 = px.scatter(df, x="sample_id", y="abundance", size="abundance", color="sample_id")
        fig2 = px.scatter(df, x="taxonomy", y="sample_id", size="abundance", color="sample_id")
        fig2_style = {'display': 'none'}
        return fig1,fig2,fig2_style

    def plot_area(self, df):
        # Plotting code for area plot goes here...
        fig1 = px.area(df, x="sample_id", y="abundance", color="taxonomy", line_group="taxonomy")
        fig2_style = {'display': 'none'}
        return fig1,fig2_style

    def plot_scatter_3d(self, df):
        # Plotting code for scatter 3D goes here...
        fig1 = px.scatter_3d(df, x='taxonomy', y='abundance', z='sample_id', color='taxonomy')
        fig2 = px.scatter_3d(df, x='abundance', y='taxonomy', z='sample_id', color='abundance')
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

    def _init_callbacks(self) -> None:
        """
        Initialize the callbacks for the app.

        The callbacks include updating the figures when the dropdown value, piechart value, or slider value changes,
        and downloading the CSV when the download button is clicked.
        """

        
        #this updates the graph based on the samples selected 
        print("init callbacks in taxonomy pie called")
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
                fig1, fig2 = self.plot_stacked_bar(self.df_selected)

            elif value == 'groupedbar':
                fig1, fig2 = self.plot_grouped_bar(self.df_selected)

            elif value == 'scatter':
                fig1,fig2,fig2_style = self.plot_scatter(self.df_selected)

            elif value == 'area':
                fig1,fig2_style = self.plot_area(self.df_selected)

            elif value == 'scatter3d':
                fig1,fig2 = self.plot_scatter_3d(self.df_selected)

            elif value == "pie":
                fig1, piechart_style, fig2_style = self.plot_pie(self.result_df,sample_value_piechart)

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


