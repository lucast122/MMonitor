import mmonitor.config as cfg
from mmonitor.database.mmonitor_db import MMonitorDBInterface
from mmonitor.dashapp.index import DashBaseApp


def main():
    mmonitor_db = MMonitorDBInterface(cfg.mmonitor_db_path)
    dash_app = DashBaseApp(mmonitor_db)
    dash_app.run_server(debug=True)


if __name__ == '__main__':
    main()
