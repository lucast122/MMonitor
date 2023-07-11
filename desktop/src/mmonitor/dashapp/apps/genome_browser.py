import os
import subprocess
import tarfile
import urllib.request

import dash
import dash_bio as dashbio
from dash import dcc
from dash import html

from build import ROOT
from mmonitor.dashapp.app import app
from mmonitor.dashapp.base_app import BaseApp
from mmonitor.database.mmonitor_db import MMonitorDBInterface


class GenomeBrowser(BaseApp):
    """
    App to load genome of MAGs and view them.
    """

    def __init__(self, sql: MMonitorDBInterface):

        super().__init__(sql)
        self._taxonomies = self._sql.get_unique_taxonomies()

        self._table_df = None
        self._init_layout()
        self._init_callbacks()

    # Define the layout of the Dash app
    def _init_layout(self) -> None:
        browser = html.Div([
            html.Button('Load Genomes', id='load-genomes'),
            dashbio.Igv(
                id='genome-browser',
                reference={
                    'id': 'hg19',
                    'fastaURL': 'https://www.dnastack.com/ga4gh/trs/v2/references/NCBI37'
                },
                tracks=[],
                minimumBases=10
            ),
            dcc.ConfirmDialog(
                id='confirm-dialog',
                message=''
            )
        ])

        CONTENT_STYLE = {

            "margin-right": "2rem",
            "padding": "2rem 1rem",
            'margin-bottom': '200px',
            'font-size': '15px'
        }

        container = html.Div([browser], style=CONTENT_STYLE)
        self._layout = container

    # Callback to handle GenBank file upload and display in the genome browser

    def _init_callbacks(self) -> None:
        @app.callback(
            dash.dependencies.Output('genome-browser', 'tracks'),
            [dash.dependencies.Input('load-genomes', 'n_clicks')]
        )
        def load_genomes(n_clicks):
            if n_clicks:
                genbank_dir = "/Users/timolucas/Documents/caro/kluyveri_filtered/prokka/"
                tracks = []

                # Check if bedtools is installed
                if not self.check_bedtools_installed():
                    self.install_bedtools(f"{ROOT}/src/resources/")  # Specify the desired installation directory

                for filename in os.listdir(genbank_dir):
                    if filename.endswith(".gbk"):
                        # Convert GenBank to BigBed
                        self.gbk_path = os.path.join(genbank_dir, filename)
                        self.bb_path = self.gbk_path.replace('.gbk', '.bb')

                        subprocess.run(
                            ['/Users/timolucas/Applications/bedtobigbed', '-type=bed12+', '-tab', self.gbk_path,
                             'chrom.sizes', self.bb_path])

                        tracks.append({
                            'name': filename,
                            'url': self.bb_path,
                            'indexURL': self.bb_path + '.bbi',
                            'format': 'bigBed'
                        })
                return tracks
            else:
                return []

    def install_bedtools(self, target_dir):
        download_url = 'https://github.com/arq5x/bedtools2/releases/download/v2.31.0/bedtools-2.31.0.tar.gz'
        tarball_path = os.path.join(target_dir, 'bedtools-2.31.0.tar.gz')

        # Download the tarball file
        urllib.request.urlretrieve(download_url, tarball_path)

        # Extract the tarball
        with tarfile.open(tarball_path, 'r:gz') as tar:
            tar.extractall(path=target_dir)

        # Set the bedtools directory path
        bedtools_dir = os.path.join(target_dir, 'bedtobigbed')

        # Add the bedtools directory to the system PATH
        os.environ['PATH'] = bedtools_dir + ':' + os.environ['PATH']

    def check_bedtools_installed(self):
        try:
            subprocess.run(['bedtools', '--version'], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def generate_chrom_sizes(fasta_file):
        chrom_sizes_file = 'chrom.sizes'
        subprocess.run(['fetchChromSizes', '-noheader', 'stdout', fasta_file], capture_output=True, text=True,
                       check=True, stdout=open(chrom_sizes_file, 'w'))
        return chrom_sizes_file
