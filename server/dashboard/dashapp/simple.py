from dash import dcc, html
from dash.dependencies import Input, Output
from django_plotly_dash import DjangoDash

class SimpleApp():
    def __init__(self):
        self.app = DjangoDash('SimpleApp')  # replace with the name of your app

        self.app.layout = html.Div([
            html.Button('Click me', id='button'),
            html.Label(id='label')
        ])

        @self.app.callback(
            Output('label', 'children'),
            Input('button', 'n_clicks')
        )
        def update_label(n_clicks):
            if n_clicks is None:
                return "Button hasn't been clicked yet."
            else:
                return f"Button has been clicked {n_clicks} times."
