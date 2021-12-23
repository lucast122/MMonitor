from os.path import isfile, join

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

    width = 1500
    height = 1000
    uid = request.user.id
    image_file = join(settings.STATICFILES_DIRS[0], 'dashboard', str(uid), 'horizon.png')

    if request.method == 'POST' or not isfile(image_file):
        q = "SELECT sample_id, taxonomy, abundance FROM mmonitor"
        df = db.query_to_dataframe(q)
        width = int(request.POST.get("width", str(width)))
        height = int(request.POST.get("height", str(height)))
        generate_image(df, uid, width=width, height=height)

    context = {'width': width, 'height': height, 'uid': str(uid)}
    return render(request, 'dashboard/horizon.html', context=context)
