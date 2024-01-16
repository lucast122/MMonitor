from django.contrib import admin

# Register your models here.
from .models import NanoporeRecord
from .models import SequencingStatistics
from .models import Metadata

admin.site.register(NanoporeRecord)
admin.site.register(SequencingStatistics)
admin.site.register(Metadata)
