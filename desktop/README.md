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

Tested on Windows 10 and Ubuntu 20.

Executable is most likely not backwards compatible.

## How to use

1. Create or choose Project
  A project represents the database MMonitor uses. The user always has to create or choose a previously created database in order to use the tool. Creating a project         will create a called <name>.sqlite3 on the dard drive, where <name> is the name the user chooses.
2. Run analysis pipeline
  Click the button "Run analysis pipeline" to open up the pipeline selection window. Please select the analysis you want to perform. For taxonomic analysis select either     "Quick taxonomy nanopore" or "Quick taxonomy 16s nanopore" depending on your data input. Use the first if you have whole genome sequencing reads and, if you have 16s       reads choose the second. The functional analysis takes way longer than taxonomic because the reads will first need to get assembled into contigs and then mapped against    a database for binning. Especially binning may take longer depending on your system.
4. Start Monitoring
   If you choose a project that has been previously created and you already ran an analysis for it then you can also skip step 2 and start monitoring directly. However,       clicking the button "Start monitoring" with an empty project will result in an error message popping up. If you ran an analysis in step 2 and received a notification       that the analysis has finished you can then go ahead and click "Start monitoring". A browser window with your default browser will popup along with the visualization       application.
5. Analyze data in Dashboard
   After step 3 you can now look at the results of the analysis in the browser dashboard. Click on one of the links to change between the different apps. Following is a       quick summary of each apps' functionality.
Optional: Add metadata from csv
   If you have metadata you can add it as a csv file. In the analysis dashapp you can then see correlation values for your metadata and taxonomy.

Taxonomy: View the absolute and relative abundances of your samples after running a taxonomic analysis.
Horizon plot: Create a horizon plot to quickly see changes in abundance between your samples.
Correlations: If you previously added metadata you can here view the different correlation values between your metagenome abundances and the metadata.
KEGG: View the KEGG metabolic maps created by the analysis pipeline if all functional analysis steps were selected.
Gene browser: Check out your assembled metagenomes using the gene browser nNot tested yet, may not work on every system).

Be sure to press 'Quit' to terminate the app, as it also terminates the dash server.
