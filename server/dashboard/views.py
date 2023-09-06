from os.path import isfile, join

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.http import JsonResponse
from django.contrib.sessions.models import Session
from django.contrib.auth.models import User

from .dashapp.database.mmonitor_db_mysql import MMonitorDBInterfaceMySQL
from .dashapp.calculations.horizon_r import generate_image
from .dashapp.index import Index


@login_required
def get_user_id(request):
    # Get the session ID from the URL parameters
    session_id = request.GET.get('session_id', None)

    if session_id:
        # If a session ID was provided, get the session
        session = Session.objects.get(session_key=session_id)
        user_id = session.get_decoded().get('_auth_user_id')

        # If a user ID was found, return it
        if user_id:
            return JsonResponse({'user_id': user_id})

    # If no session ID was provided, or no user ID was found, return an error
    return JsonResponse({'error': 'No session ID provided or no user found'}, status=400)


@login_required
def index(request):
    return render(request, 'dashboard/index.html')


@login_required
def load_app(request, name):
    user_id = request.user.id  # Assuming the user is authenticated
    index_instance = Index(user_id=user_id)
    return render(request, 'dashboard/dashapp.html', context={'name': name})



@login_required
def horizon(request):
    """
    Render page for horizon plot.

    Render horizon plot based on current user id.
    Calls external R script to generate plot.
    """

    # settings
    width = 1500
    height = 1000
    uid = str(request.user.id)
    image_file = join(settings.STATICFILES_DIRS[0], 'dashboard', uid, 'horizon.png')

    # if 'generate' button was clicked
    # or image simply doesn't exist yet
    # call the R script to generate a horizon plot
    # if request.method == 'POST' or not isfile(image_file):
    #     q = "SELECT sample_id, taxonomy, abundance FROM mmonitor"
    #     df = db.query_to_dataframe(q)
    #     width = int(request.POST.get("width", str(width)))
    #     height = int(request.POST.get("height", str(height)))
    #     generate_image(df, uid, width=width, height=height)

    # context = {'width': width, 'height': height, 'uid': uid}
    # return render(request, 'dashboard/horizon.html', context=context)
