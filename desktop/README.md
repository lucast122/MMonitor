# Metagenome Monitor Desktop Application


## App Requirements

- Install `R` and packages `("jpeg", "png", "RColorBrewer", "lattice", "latticeExtra")`
- Add `Rscript` to path!
- Download the latest version of [centrifuge](https://github.com/DaehwanKimLab/centrifuge), install and make sure executable is on system path
- Either download and [build new index](https://ccb.jhu.edu/software/centrifuge/manual.shtml) or download pre-built index for centrifuge


## Develop Project

- Install Python>=3.9 (must include `tkinter`)
- `pip install -r requirements.txt`
- `cd src && python -m mmonitor`


## R Horizon Plot Troubleshooting

`latticeExtra` and its dependencies needs to be installed in the library that `Rscript` uses.
Find out what libraries `Rscript` uses with `Rscript -e ".libPaths()"` and make sure they all have the necessary packages installed with
`install.packages(c("jpeg", "png", "RColorBrewer", "lattice", "latticeExtra"), lib = "<library path>")`.
You might need to start your R IDE with admin privileges depending on the library location. 


## Build App


1. Download code on machine with desired operating system 
2. `pip install pyinstaller`[1](https://pyinstaller.readthedocs.io/en/stable/spec-files.html) [2](https://pyinstaller.readthedocs.io/en/stable/usage.html#supporting-multiple-operating-systems)

3. `python build.py`

Tested on Windows 10 and Ubuntu 18.

Executable is most likely not backwards compatible.

## How to use

To use the tool, first choose a centrifuge index and select a sqlite3 database, or create a new one.

Then, populate the database with data from fastq files and csv files containing metadata.
Currently requires metadata in the same form as the database table.

Finally, start monitoring.

Be sure to press 'Quit' to terminate the app, as it also terminates the dash server.