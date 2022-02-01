from django.urls import path
from django.conf import settings

from .dashapp import kraken, taxonomy, correlations
from .dashapp.database.mmonitor_db import MMonitorDBInterface
from . import views


db = MMonitorDBInterface(settings.MMONITOR_DB_PATH)

kraken.Kraken()
taxonomy.Taxonomy(db)
correlations.Correlations(db)

app_name = 'dashboard'

urlpatterns = [
    path('', views.index, name='index'),
    path('kraken/', views.load_app, {'name': 'kraken'}, name='kraken'),
    path('taxonomy/', views.load_app, {'name': 'taxonomy'}, name='taxonomy'),
    path('correlations/', views.load_app, {'name': 'correlations'}, name='correlations'),
    path('horizon/', views.horizon, name='horizon'),
]
