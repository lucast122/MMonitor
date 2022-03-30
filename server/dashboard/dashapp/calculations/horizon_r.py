from os import environ, getcwd, chdir
from os.path import join, dirname, abspath
from subprocess import call
from pathlib import Path

import pandas as pd
from django.conf import settings

# static paths
_R_PATH = join(dirname(abspath(__file__)), 'r')
_HORIZON_R_SCRIPT = join(_R_PATH, 'horizon.r')


def generate_image(df: pd.DataFrame, uid: str, width: int, height: int) -> None:
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

    image_dir = join(settings.STATICFILES_DIRS[0], 'dashboard', uid)
    Path(image_dir).mkdir(parents=True, exist_ok=True)
    image_path = join(image_dir, 'horizon.png')
    csv_file = join(_R_PATH, uid + '_abundances.csv')

    _write_csv(df, csv_file)
    _export_env_vars(image_path, width, height, csv_file)
    _call_r_script()


def _write_csv(df: pd.DataFrame, csv_file: str) -> None:
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
    csv_df.to_csv(csv_file, index=False)


def _export_env_vars(image_path: str, width: int, height: int, csv_file: str) -> None:
    """
    Export necessary variables to environment
    so that the R script can read them from the environment.
    """

    environ['HORI_WIDTH'] = str(width)
    environ['HORI_HEIGHT'] = str(height)
    environ['HORI_CSV'] = csv_file
    environ['HORI_IMAGE'] = image_path


def _call_r_script() -> None:
    """
    Execute the R script that generates a horizon plot.
    """

    cwd = getcwd()
    chdir(_R_PATH)
    call([settings.RSCRIPT, '--no-save', _HORIZON_R_SCRIPT])
    chdir(cwd)
