from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.conf import settings

from .dashapp.database.mmonitor_db import MMonitorDBInterface
from .dashapp.calculations.horizon_r import generate_image


db = MMonitorDBInterface(settings.MMONITOR_DB_PATH)


@login_required
def index(request):
    return render(request, 'dashboard/index.html')


@login_required
def load_app(request, name):
    return render(request, 'dashboard/dashapp.html', context={'name': name})


@login_required
def horizon(request):
    q = "SELECT sample_id, taxonomy, abundance FROM mmonitor"
    df = db.query_to_dataframe(q)
    generate_image(df, width=1500, height=1000)
    return render(request, 'dashboard/horizon.html')
