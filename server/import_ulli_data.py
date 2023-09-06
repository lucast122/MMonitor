import os
import sqlite3
import pandas as pd
import django

from django.conf import settings

settings.configure(
    DATABASES={
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': "~/mmonitor_new/server/db.sqlite3",
        },
        'mmonitor': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': 'mydjangodb',
            'USER': 'mmonitor_remote',
            'PASSWORD': 'asdf!minion',
            'HOST': '134.2.78.150',  # Or an IP Address that your DB is hosted on
            'PORT': '3306',
        }
    },
    INSTALLED_APPS=[
        'django_plotly_dash.apps.DjangoPlotlyDashConfig',
        'plotly',
        'users',
        'main',
        'dashboard',
        'django.contrib.admin',
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'django.contrib.messages',
        'django.contrib.staticfiles',
        'bootstrap5'
    ],
    # add more settings here if needed
)


# Setup Django
# os.environ['DJANGO_SETTINGS_MODULE'] = 'MMonitor.settings'
# settings.configure()
django.setup()
from django.contrib.auth.models import User
from users.models import NanoporeRecord


# Connect to the SQLite database
conn = sqlite3.connect('/home/minion-computer/PycharmProjects/MMonitor/desktop/src/mmonitor/Run9_R1.sqlite3')

# Query all records from the table
df = pd.read_sql_query("SELECT * FROM mmonitor", conn)

# Get the user
user = User.objects.get(username='ulli')

# Iterate over the rows of the DataFrame
for _, row in df.iterrows():
    # Create a new NanoporeRecord
    NanoporeRecord.objects.create(
        taxonomy=row['taxonomy'],
        abundance=row['abundance'],
        sample_id=row['sample_id'],
        project_id=row['project_id'],
        user=user
    )
