# Metagenome Monitor

### Set up app:

- Install Python and packages in `requirements.txt`
- Install `R` and packages `('lattice', 'latticeExtra')`
- Set `Rscript` location in `config.py`

### Run debug server:

- PyCharm:
  - mark `/src/` as source directory
  - run `/src/mmonitor/userside/view.py`

- General purpose:
  - `cd src && python -m mmonitor`

Running view.py should open the GUI.
To use the tool first choose a centrifuge index and select an sqlite3 data base, or create a new one.
To test out the correlations app please use the data base /resourecs/mmonitor_test.sqlite as that on includes sample metadata.
If you use another data base the correlations app is not yet working, as there is no parser for metadata yet. (to be included in next update)
