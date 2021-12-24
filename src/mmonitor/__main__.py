import mmonitor.config as cfg
from mmonitor.database.mmonitor_db import MMonitorDBInterface
from mmonitor.dashapp.index import DashBaseApp
import webbrowser
from threading import Timer


def open_browser():
	webbrowser.open_new("http://localhost:{}".format(8050))


def main(db_path):
    Timer(1, open_browser).start();
    mmonitor_db = MMonitorDBInterface(db_path)
    dash_app = DashBaseApp(mmonitor_db)
    dash_app.run_server(debug=False)




if __name__ == '__main__':
    main()
