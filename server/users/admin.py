from django.contrib import admin

# Register your models here.
from .models import NanoporeRecord
from .models import SequencingStatistics


admin.site.register(NanoporeRecord)
admin.site.register(SequencingStatistics)
