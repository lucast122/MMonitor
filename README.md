# Metagenome Monitor

### Set up app:

- Install Python>=3.9 
- `pip install -r requirements.txt`
- Install `R` and packages `('lattice', 'latticeExtra')`
- Set `Rscript` location in `MMonitor.settings.py`

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
