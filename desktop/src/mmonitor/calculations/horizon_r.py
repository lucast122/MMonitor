from os import environ, getcwd, chdir
from os.path import join
from subprocess import call

import pandas as pd

from mmonitor.config import images_path, r_path

# static paths
# check config.py for file locations
_CSV_FILE = join(r_path, 'abundances.csv')
_IMAGE_FILE = join(images_path, 'horizon.png')
_HORIZON_R_SCRIPT = join(r_path, 'horizon.r')


def generate_image(df: pd.DataFrame, width: int, height: int) -> None:
    """
    Generate a horizon plot of taxonomy abundances.
    Check static paths for file locations.

    WARNING: - Local files are being created to pass data
             - Files that should be static are created dynamically
             - Scripts are being called in subprocesses
             - Environment variables are being passed between processes

    Future considerations:
             - Find a way to integrate the R script into Python
             - Find a Python-native method to generate horizon plots
             - Find a way to generate horizon plots in Plotly
    """

    _write_csv(df)
    _export_env_vars(width, height)
    _call_r_script()


def _write_csv(df: pd.DataFrame) -> None:
    """
    Transpose mmonitor db to a Dataframe with only taxonomies and their abundances.
    """

    # target df
    csv_df = pd.DataFrame()

    # create column in target df for each unique taxonomy
    taxonomies = df['taxonomy'].unique()

    # extract a taxonomy's abundances as series and
    # append it to the target df as new column
    for t in taxonomies:
        f = df['taxonomy'] == t
        csv_df[t] = pd.Series(df[f]['abundance']).reset_index(drop=True)

    # write file
    csv_df.to_csv(_CSV_FILE, index=False)


def _export_env_vars(width: int, height: int) -> None:
    """
    Export necessary variables to environment
    so that the R script can read them from the environment.
    """

    environ['HORI_WIDTH'] = str(width)
    environ['HORI_HEIGHT'] = str(height)
    environ['HORI_CSV'] = _CSV_FILE
    environ['HORI_IMAGE'] = _IMAGE_FILE


def _call_r_script() -> None:
    """
    Execute the R script that generates a horizon plot.
    """

    cwd = getcwd()
    chdir(r_path)
    call(['Rscript', '--no-save', _HORIZON_R_SCRIPT])
    chdir(cwd)
