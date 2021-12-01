from os.path import dirname, abspath, join


# STATIC PATHS
_MMONITOR_ROOT = dirname(abspath(__file__))
_RESOURCES = join(_MMONITOR_ROOT, 'resources')

mmonitor_db_path = join(_RESOURCES, 'mmonitor.db')
images_path = join(_RESOURCES, 'images')
r_path = join(_RESOURCES, 'r')


# USER REQUIRED CONFIGURATION

# path to Rscript that allows execution of R scripts from the command line
# WARNING: R instance must have packages ('lattice', 'latticeExtra') installed
rscript = 'Rscript'
