from django.urls import path
from django.conf import settings

# from .dashapp import kraken, taxonomy, correlations

from . import views
from .dashapp.database.mmonitor_db_mysql import MMonitorDBInterfaceMySQL
from .dashapp.index import Index
from .dashapp.kraken import Kraken
from .dashapp.taxonomy import Taxonomy



# db = MMonitorDBInterfaceMySQL
index_app = Index()
# Kraken()
# Taxonomy(db)

# correlations.Correlations(db)

app_name = 'dashboard'

urlpatterns = [
    path('', views.load_app, {'name': 'Index'}, name='index')
    # path('kraken/', views.load_app, {'name': 'kraken'}, name='kraken'),
    # path('taxonomy/', views.load_app, {'name': 'taxonomy'}, name='taxonomy')
    # path('correlations/', views.load_app, {'name': 'correlations'}, name='correlations'),
    # path('horizon/', views.load_app, {'name': 'horizon'}, name='horizon'),
    # path('kegg/', views.load_app, {'name': 'kegg'}, name='kegg'),
    # path('genome_browser/', views.load_app, {'name': 'genome_browser'}, name='genome_browser'),
]
