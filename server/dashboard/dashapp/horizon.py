import pandas as pd
import plotly.graph_objects as go
from dash import dcc
import dash_html_components as html
from html import unescape
from dash_extensions import DeferScript


from dash.dependencies import Input, Output
from plotly.subplots import make_subplots
# from mmonitor.dashapp.app import app
# from mmonitor.dashapp.base_app import BaseApp
# from mmonitor.database.mmonitor_db import MMonitorDBInterface
import dash_bootstrap_components as dbc
from django_plotly_dash import DjangoDash
from dash_extensions.enrich import DashProxy, html



class Horizon:


    """
    App to display the taxonomy abundances in a horizon plot
    """
    def __init__(self, user_id):
        self.app = DjangoDash('horizon')
        # self.app = DashProxy()
        self.user_id = user_id
        # super().__init__(sql)
        # self.app = dash.Dash(__name__)
        q = 'SELECT sample_id, taxonomy, abundance FROM mmonitor'



        # Define the JavaScript code for the horizon chart
        self.js_code = """
            setTimeout(function() {
    var series = [];
    for (var i = 0, variance = 0; i < 1500; i++) {
        variance += (Math.random() - 0.5) / 10;
        series.push(Math.cos(i / 100) + variance);
    }

    var horizonChart = d3.horizonChart()
        .height(100)
        .title('Horizon, 4-band')
        .colors(['#313695', '#4575b4', '#74add1', '#abd9e9', '#fee090', '#fdae61', '#f46d43', '#d73027']);

    var horizons = d3.select('#horizon-chart-container').selectAll('.horizon')
        .data([series])
        .enter().append('div')
        .attr('class', 'horizon')
        .each(horizonChart);
}, 3000); // Adjust the timeout as needed

        """

        self._init_layout()
        self._init_callbacks()

    def _init_layout(self):
        container = html.Div([
            # Container for the horizon chart
            html.Div(id="horizon-chart-container"),

            # Include D3.js and d3-horizon-chart libraries
            html.Script(src="https://d3js.org/d3.v4.js"),
            html.Script(src="https://unpkg.com/d3-horizon-chart"),
            html.Script(self.js_code)
        ])

        # mxgraph = r'{&quot;highlight&quot;:&quot;#0000ff&quot;,&quot;nav&quot;:true,&quot;resize&quot;:true,&quot;toolbar&quot;:&quot;zoom layers lightbox&quot;,&quot;edit&quot;:&quot;_blank&quot;,&quot;xml&quot;:&quot;&lt;mxfile host=\&quot;app.diagrams.net\&quot; modified=\&quot;2021-06-07T06:06:13.695Z\&quot; agent=\&quot;5.0 (Windows)\&quot; etag=\&quot;4lPJKNab0_B4ArwMh0-7\&quot; version=\&quot;14.7.6\&quot;&gt;&lt;diagram id=\&quot;YgMnHLNxFGq_Sfquzsd6\&quot; name=\&quot;Page-1\&quot;&gt;jZJNT4QwEIZ/DUcToOriVVw1JruJcjDxYho60iaFIaUs4K+3yJSPbDbZSzN95qPTdyZgadm/GF7LAwrQQRyKPmBPQRzvktidIxgmwB4IFEaJCUULyNQvEAyJtkpAswm0iNqqegtzrCrI7YZxY7Dbhv2g3r5a8wLOQJZzfU4/lbByoslduPBXUIX0L0cheUrugwk0kgvsVojtA5YaRDtZZZ+CHrXzukx5zxe8c2MGKntNgknk8bs8fsj3+KtuDhxP+HZDVU5ct/RhatYOXgGDbSVgLBIG7LGTykJW83z0dm7kjklbaneLnEnlwFjoL/YZzb93WwNYgjWDC6EEdkuC0cZEO7p3i/6RF1WutL8nxmnkxVx6UcUZJIy/LgP49622mO3/AA==&lt;/diagram&gt;&lt;/mxfile&gt;&quot;}'


        # self.app.layout = html.Div([
        #     html.Div(className='mxgraph', style={"maxWidth": "100%"}, **{'data-mxgraph': unescape(mxgraph)}),
        #     DeferScript(src='https://viewer.diagrams.net/js/viewer-static.min.js')
        # ])





        self.app.layout = container

    def _init_callbacks(self):
        return
