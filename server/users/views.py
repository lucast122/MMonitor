from django.core.mail import send_mail
from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth import authenticate

from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.conf import settings
from .models import UserProfile, SequencingStatistics
from django.contrib.auth import authenticate
from django.http import JsonResponse
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from users.models import NanoporeRecord
from django.contrib.auth.decorators import login_required
from .models import UserProfile
import json
import base64
from django.http import HttpResponse


@csrf_exempt
def add_sequencing_statistics(request):
    if request.method == "POST":
        # Get the username and password from the Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Basic '):
            return JsonResponse({"error": "Missing or invalid Authorization header"}, status=400)
        username, password = base64.b64decode(auth_header.split(' ', 1)[1]).decode().split(':', 1)

        # Authenticate the user
        user = authenticate(request, username=username, password=password)
        if user is None:
            return JsonResponse({"error": "Invalid username or password"}, status=400)

        print("POST request received at /users/add_sequencing_statistics/")
        try:
            data = json.loads(request.body.decode('utf-8'))
            SequencingStatistics.objects.create(
                sample_name=data['sample_name'],
                project_id=data['project_id'],
                subproject_id=data['subproject_id'],
                date=data['date'],
                mean_read_length=data.get('mean_read_length'),
                median_read_length=data.get('median_read_length'),
                mean_quality_score=data.get('mean_quality_score'),
                mean_gc_content=data.get('mean_gc_content'),
                read_lengths=data.get('read_lengths', "[]"),  # Default to empty list if not provided
                avg_qualities=data.get('avg_qualities', "[]"),  # Default to empty list if not provided
                number_of_reads=data.get('number_of_reads'),
                total_bases_sequenced=data.get('total_bases_sequenced'),
                q20_score=data.get('q20_score'),
                q30_score=data.get('q30_score'),
                avg_quality_per_read=json.dumps(data.get('avg_quality_per_read', [])),
                base_quality_avg=json.dumps(data.get('base_quality_avg', {})),
                gc_contents_per_sequence=data.get('gc_contents_per_sequence', "[]"),  # Default to empty list if not provided

                user=user
            )
            return JsonResponse({"status": "success"}, status=201)
        except Exception as e:
            return JsonResponse({"status": "error", "error": str(e)}, status=400)


@csrf_exempt
def add_nanopore_record(request):
    print(f"Request method: {request.method}")
    print(f"Request path: {request.path}")
    print(f"Request body: {request.body}")
    print(f"Request headers: {request.headers}")


    if request.method == "POST":
        # Get the username and password from the Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Basic '):
            return JsonResponse({"error": "Missing or invalid Authorization header"}, status=400)
        username, password = base64.b64decode(auth_header.split(' ', 1)[1]).decode().split(':', 1)

        # Authenticate the user
        user = authenticate(request, username=username, password=password)
        if user is None:
            return JsonResponse({"error": "Invalid username or password"}, status=400)


        print("POST request received at /users/add_nanopore_record/")
        try:
            data = json.loads(request.body)
            print(f"Received data: {data}")
            user_id = data.get('user_id')
            print(f"User ID: {user_id}")
            user = User.objects.get(id=user_id)
            print(f"User: {user}")

            NanoporeRecord.objects.create(
                taxonomy=data.get('taxonomy'),
                abundance=data.get('abundance'),
                sample_id=data.get('sample_id'),
                project_id=data.get('project_id'),
                subproject=data.get('subproject'),
                date=data.get('date'),
                user=user
            )
            print("Nanopore record created successfully")
            return JsonResponse({"success": True}, status=200)
        except User.DoesNotExist:
            print(f"No user found with ID {user_id}")
            return JsonResponse({"error": "User not found"}, status=400)
        except Exception as e:
            print(f"Error occurred bla: {e}")
            return JsonResponse({"error": str(e), "type": str(type(e))}, status=400)


@csrf_exempt
def get_user_id(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            return JsonResponse({'user_id': user.id}, status=200)
        else:
            return JsonResponse({'error': 'Invalid username or password.'}, status=400)
    else:
        return JsonResponse({'error': 'Invalid request method.'}, status=400)




def create_mysql_user(username, password):
    from django.conf import settings
    import mysql.connector

    # Connect to MySQL as root
    cnx = mysql.connector.connect(
        user=settings.DATABASES['mmonitor']['USER'],
        password=settings.DATABASES['mmonitor']['PASSWORD'],
        host=settings.DATABASES['mmonitor']['HOST'],
        database=settings.DATABASES['mmonitor']['NAME']
    )
    cursor = cnx.cursor()

    # Create the MySQL user and grant privileges
    try:
        cursor.execute(f"CREATE USER '{username}'@'%' IDENTIFIED BY '{password}';")
        cursor.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON your_database.* TO '{username}'@'%';")

    except mysql.connector.Error as err:
        print(f"Failed creating MySQL user: {err}")
        return False

    cnx.commit()
    cursor.close()
    cnx.close()
    return True


@login_required
def profile_view(request):
    # Fetch the UserProfile for the currently logged-in user
    user_profile = UserProfile.objects.get(user=request.user)
    # Now user_profile contains the data for the currently logged-in user only

def redirect_to_dash(request):
    # Get the Django session ID
    session_id = request.session.session_key

    # Redirect to the Dash app, including the session ID as a URL parameter
    return redirect(f'{settings.DASH_APP_URL}?session_id={session_id}')


def register(request):
    """Register a new user"""
    if request.method != "POST":
        # Display black registration form
        form = UserCreationForm()

    else:
        # Process completed form
        form = UserCreationForm(data=request.POST)

        if form.is_valid():
            new_user = form.save()
            # default to non-active so admin needs to authorize user
            new_user.is_active = False
            new_user.save()
            UserProfile.objects.create(user=new_user, some_field="default value")



            # Login and redirect to homepage
            login(request, new_user)
            return redirect("main:index")

    # Display a blank or invalid form
    context = {"form": form}

    return render(request, "registration/register.html", context)

