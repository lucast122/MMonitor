from dash import dcc as dcc
from dash import html
from dash.dependencies import Input, Output
from dash.exceptions import PreventUpdate

from mmonitor.dashapp.app import app
from mmonitor.dashapp.apps import correlations, taxonomy, kraken, horizon
from mmonitor.dashapp.base_app import BaseApp
from mmonitor.database.mmonitor_db import MMonitorDBInterface


class DashBaseApp(BaseApp):
    """
    Landing page of the dash application.
    Contains navigation to the various application pages.
    """

    def __init__(self, sql: MMonitorDBInterface):
        super().__init__(sql)
        self._app = app
        self._init_apps()
        self._init_layout()
        app.layout = self.layout
        self._init_callbacks()

    def _init_apps(self) -> None:
        """
        Register apps by their urls, names and instances.
        This is the only place you need to add an app.
        """

        self._apps = {
            '/apps/correlations': {
                'name': 'Correlations',
                'app': correlations.Correlations(self._sql)
            },
            '/apps/taxonomy': {
                'name': 'Taxonomy',
                'app': taxonomy.Taxonomy(self._sql)
            },
            '/apps/kraken2': {
                'name': 'Kraken2',
                'app': kraken.Kraken(self._sql)
            },
            '/apps/horizon': {
                'name': 'Horizon',
                'app': horizon.Horizon(self._sql)
            },
        }

    def _init_layout(self) -> None:
        """
        The index page's layout consists of the app navigation and
        the currently selected app's page content.
        """

        location = dcc.Location(id='url', refresh=False)
        navigation = html.Div([
            dcc.Link(values['name'], href=url, style={'padding': '10px'})
            for url, values in self._apps.items()
        ], className="row")
        page_content = html.Div(id='page-content', children=[])
        container = html.Div([location, navigation, page_content])
        self.layout = container

    def _init_callbacks(self) -> None:
        @app.callback(
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
            elif pathname in self._apps:
                return self._apps[pathname]['app'].layout
            # otherwise it's page not found
            else:
                return "404 Page Error! Please choose a link"

    def run_server(self, debug: bool) -> None:
        """
        Runs the dash app.
        """
        self._app.run_server(debug=debug)


if __name__ == '__main__':
    """
    Run dash app for debugging purposes.
    """
    from mmonitor.config import mmonitor_db_path

    db = MMonitorDBInterface(mmonitor_db_path)
    dash_app = DashBaseApp(db)
    dash_app.run_server(debug=True)
