from django.urls import path

from .views import chart_data_api  # Adjust the import based on where your view function is located

urlpatterns = [
    path('api/chart-data/', chart_data_api, name='chart_data_api'),
]
