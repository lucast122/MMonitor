# Metagenome Monitor

### Set up app:

- Install Python>=3.9 
- `pip install -r requirements.txt`
- Install `R` and packages `('lattice', 'latticeExtra')`
- Set `Rscript` location in `config.py`
- Download the latest version of [centrifuge](https://github.com/DaehwanKimLab/centrifuge), install and make sure executable is on system path
- Either download and [build new index](https://ccb.jhu.edu/software/centrifuge/manual.shtml) or download pre-built index for centrifuge

### Run debug server:

- PyCharm (requires PyCharm Professional):
  - Set up Django run configuration:
    1. Edit configuration
    2. Add new configuration -> Django server
    3. Set Name to 'MMonitor'
    4. Enable Django support (warning at the bottom)
    5. Set root directory and path to _settings.py_
    6. Apply and run
- General purpose:
  - `python manage.py runserver`

### Run desktop app:

- `python manage.py runapp`

To use the tool, first choose a centrifuge index and select a sqlite3 database, or create a new one.
To test out the correlations app, please use the database `mmonitor.sqlite3` as it includes sample metadata.
If you use another database the correlations app is not yet working,
as there is no parser for metadata yet. (to be included in next update)
