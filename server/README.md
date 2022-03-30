# Metagenome Monitor Django Server

## Set up server:

- Install Python>=3.9 
- `pip install -r requirements.txt`
- Install `R` and packages `('lattice', 'latticeExtra')`
- Set `Rscript` location in `MMonitor/settings.py`

## Run debug server:

- PyCharm (requires PyCharm Professional):
  - Set up Django run configuration:
    1. Enable Django support in settings
    2. Edit configuration
    3. Add new configuration -> Django server
    4. Set Name to _'MMonitor'_
    5. Set root directory
    6. Set path to `MMonitor/settings.py`
    7. Apply and run
- General purpose:
  - `python manage.py runserver`
