from django.contrib.auth.decorators import login_required
from django.core.serializers import serialize
from django.http import HttpResponse
from django.shortcuts import render

from users.models import NanoporeRecord  # Adjust the import according to your model's location


@login_required
def chart_data_api(request):
    if request.user.is_authenticated:
        user_id = request.user.id

    # user_id = request.GET.get('user_id')
    print(f"user id in view: {user_id}")
    chart_data_queryset = NanoporeRecord.objects.filter(user_id=user_id)
    chart_data_json = serialize('json', chart_data_queryset)
    return HttpResponse(chart_data_json, content_type="application/json")


@login_required
def your_view(request):
    if request.user.is_authenticated:
        user_id = request.user.id

    return render(request, 'base.html', {'user_id': user_id})
