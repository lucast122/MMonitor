from django.db import models
from django.contrib.auth.models import User
from datetime import date



class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    some_field = models.CharField(max_length=200)

    class Meta:
        app_label = 'users'  # If this is the Django app for your MySQL db


class NanoporeRecord(models.Model):
    read_id = models.AutoField(primary_key=True)
    taxonomy = models.TextField(default='empty')
    abundance = models.FloatField(default=0.0)
    sample_id = models.CharField(max_length=255, default='empty')
    project_id = models.CharField(max_length=255, default='empty')
    subproject = models.CharField(max_length=255, default='empty')
    date = models.DateField(default=date.today)
    tax_id = models.IntegerField(default=0)
    tax_genus = models.CharField(max_length=255, null=True, blank=True, default='empty')
    tax_family = models.CharField(max_length=255, null=True, blank=True, default='empty')
    tax_order = models.CharField(max_length=255, null=True, blank=True, default='empty')
    tax_class = models.CharField(max_length=255, null=True, blank=True, default='empty')
    tax_phylum = models.CharField(max_length=255, null=True, blank=True, default='empty')
    tax_superkingdom = models.CharField(max_length=255, null=True, blank=True, default='empty')
    tax_clade = models.CharField(max_length=255, null=True, blank=True, default='empty')
    tax_subspecies = models.CharField(max_length=255, null=True, blank=True, default='empty')
    tax_species_subgroup = models.CharField(max_length=255, null=True, blank=True, default='empty')
    tax_species_group = models.CharField(max_length=255, null=True, blank=True, default='empty')
    user = models.ForeignKey(User, on_delete=models.CASCADE)



# class NanoporeRecord(models.Model):
#     read_id = models.AutoField(primary_key=True)
#     taxonomy = models.TextField()
#     abundance = models.FloatField()
#     sample_id = models.CharField(max_length=255)
#     project_id = models.CharField(max_length=255)
#     subproject = models.CharField(max_length=255)
#     date = models.CharField(max_length=255)


# model that gets basic statistics from the sequencing files
class SequencingStatistics(models.Model):
    sample_name = models.CharField(max_length=255)
    project_id = models.CharField(max_length=255)
    subproject_id = models.CharField(max_length=255)
    date = models.CharField(max_length=255)
    mean_read_length = models.FloatField(null=True, blank=True)
    median_read_length = models.FloatField(null=True, blank=True)
    mean_quality_score = models.FloatField(null=True, blank=True)
    mean_gc_content = models.FloatField(null=True, blank=True)
    read_lengths = models.TextField(null=True, blank=True)  # Serialized list of read lengths
    avg_qualities = models.TextField(null=True, blank=True)  # Serialized list of average qualities per length
    number_of_reads = models.IntegerField(null=True, blank=True)
    total_bases_sequenced = models.IntegerField(null=True, blank=True)
    q20_score = models.FloatField(null=True, blank=True)
    q30_score = models.FloatField(null=True, blank=True)
    avg_quality_per_read = models.TextField(null=True, blank=True)  # Serialized list
    base_quality_avg = models.TextField(null=True, blank=True)  # Serialized dictionary
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    class Meta:
        verbose_name_plural = "Sequencing Statistics"




class MetaDB(models.Model):
    meta_id = models.AutoField(primary_key=True)
    project_id = models.IntegerField()
    sample_id = models.IntegerField()
    n_butyric_acid = models.FloatField()
    n_valeric_acid = models.FloatField()
    n_caproic_acid = models.FloatField()
    n_heptanoic_acid = models.FloatField()
    n_caprylic_acid = models.FloatField()

    class Meta:
        managed = False
        db_table = 'metadata'
