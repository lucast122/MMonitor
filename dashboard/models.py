from django.db import models


class MMonitorDB(models.Model):
    read_id = models.AutoField(primary_key=True)
    project_id = models.IntegerField()
    sample_id = models.IntegerField()
    taxonomy = models.TextField()
    abundance = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'mmonitor'


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
