from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt

from users.models import NanoporeRecord
from .models import SequencingStatistics
from .models import UserProfile


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
                tax_genus=data.get('tax_genus'),
                tax_family=data.get('tax_family'),
                tax_order=data.get('tax_order'),
                tax_class=data.get('tax_class'),
                tax_phylum=data.get('tax_phylum'),
                tax_superkingdom=data.get('tax_superkingdom'),
                tax_clade=data.get('tax_clade'),
                tax_subspecies=data.get('tax_subspecies'),
                abundance=data.get('abundance'),
                count=data.get('count'),
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


from django.contrib.auth import authenticate
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import base64
import json


@csrf_exempt
def overwrite_nanopore_record(request):
    if request.method == "POST":
        try:
            records = json.loads(request.body)
            if not isinstance(records, list):
                return JsonResponse({"error": "Expected a list of records"}, status=400)

            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Basic '):
                return JsonResponse({"error": "Missing or invalid Authorization header"}, status=400)

            username, password = base64.b64decode(auth_header.split(' ', 1)[1]).decode().split(':', 1)
            user = authenticate(request, username=username, password=password)
            if user is None:
                return JsonResponse({"error": "Invalid username or password"}, status=400)

            # Collect unique sample_ids from incoming records
            unique_sample_ids = set(record['sample_id'] for record in records if 'sample_id' in record)

            # Delete existing records for each unique sample_id
            for sample_id in unique_sample_ids:
                NanoporeRecord.objects.filter(sample_id=sample_id, user=user).delete()

            # Process each record
            new_records = []
            for record_data in records:
                sample_id = record_data.get('sample_id')
                # Delete existing records for the given sample_id
                NanoporeRecord.objects.filter(sample_id=sample_id, user=user).delete()

                # Prepare new record
                new_record = NanoporeRecord(
                    taxonomy=record_data.get('taxonomy'),
                    tax_genus=record_data.get('tax_genus'),
                    tax_family=record_data.get('tax_family'),
                    tax_order=record_data.get('tax_order'),
                    tax_class=record_data.get('tax_class'),
                    tax_phylum=record_data.get('tax_phylum'),
                    tax_superkingdom=record_data.get('tax_superkingdom'),
                    tax_clade=record_data.get('tax_clade'),
                    tax_subspecies=record_data.get('tax_subspecies'),
                    abundance=record_data.get('abundance'),
                    count=record_data.get('count'),
                    sample_id=sample_id,
                    project_id=record_data.get('project_id'),
                    subproject=record_data.get('subproject'),
                    date=record_data.get('date'),
                    user=user
                )
                new_records.append(new_record)

            # Bulk insert new records
            NanoporeRecord.objects.bulk_create(new_records)

            return JsonResponse({"message": "Records created successfully"}, status=201)

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON format"}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    else:
        return JsonResponse({"error": "Invalid request method"}, status=405)


@csrf_exempt
def get_unique_sample_ids(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(username=username, password=password)

        if user is not None:
            unique_sample_ids = NanoporeRecord.objects.filter(user=user).values_list('sample_id', flat=True).distinct()
            sample_ids_list = list(unique_sample_ids)
            print(sample_ids_list)
            return JsonResponse({'sample_ids': sample_ids_list}, status=200)
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

