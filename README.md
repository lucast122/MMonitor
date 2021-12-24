# Metagenome Monitor

### Set up app:

- Install Python and packages in `requirements.txt`
- Install `R` and packages `('lattice', 'latticeExtra')`
- Set `Rscript` location in `config.py`
- Download latest version of centrifuge, install and make sure executable is on system path (https://github.com/DaehwanKimLab/centrifuge)
- Either download and build new index or download pre built index for centrifuge (https://ccb.jhu.edu/software/centrifuge/manual.shtml)

### Run debug server:

- PyCharm:
  - mark `/src/` as source directory
  - run `/src/mmonitor/userside/view.py`

- General purpose:
  - `cd src && python -m mmonitor`

Running view.py should open the GUI.
To use the tool first choose a centrifuge index and select an sqlite3 data base, or create a new one.
To test out the correlations app please use the data base /resources/mmonitor.sqlite3 as that on includes sample metadata.
If you use another data base the correlations app is not yet working, as there is no parser for metadata yet. (to be included in next update)
