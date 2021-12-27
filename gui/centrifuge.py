import logging
import multiprocessing
import os
import pathlib
import subprocess


def unpack_fastq_list(xs):
    """
    Gets a list of paths and outputs a comma seperated string
    containing the paths used as input for centrifuge
    """
    if len(xs) == 1:
        return str(xs[0])
    elif len(xs) > 1:
        return ",".join(xs)


class CentrifugeRunner:

    def __init__(self):
        self.logger = logging.getLogger('timestamp')
        self.check_centrifuge()
        self.cent_out = ""

    def check_centrifuge(self):
        try:
            subprocess.call(['centrifuge', '-h'], stdout=open(os.devnull, 'w'), stderr=subprocess.STDOUT)
        except FileNotFoundError:
            self.logger.error("Make sure that centrifuge is installed and on the sytem path."
                              " For more info visit http://www.ccb.jhu.edu/software/centrifuge/manual.shtml")

    def run_centrifuge(self, fastq_list, centrifuge_index, sample_name):
        self.cent_out = f"{pathlib.Path(__file__).parent.resolve()}/classifier_out/{sample_name}_cent_out"
        cmd = f'centrifuge -x {centrifuge_index} -U {unpack_fastq_list(fastq_list)} -p {multiprocessing.cpu_count()}' \
              f' -S {pathlib.Path(__file__).parent.resolve()}/classifier_out/{sample_name}_cent_out '
        os.system(cmd)

    def make_kraken_report(self, centrifuge_index):
        cmd = f"centrifuge-kreport -x {centrifuge_index} {self.cent_out} >" \
              f" {self.cent_out.replace('cent_out', 'kraken_out')}"
        os.system(cmd)

    def get_files_from_folder(self, folder_path):
        """
        Gets a path to a folder, checks if path contains sequencing files with
        specified endings and returns list containing paths to sequencing files
        """
        try:
            files = [os.path.join(folder_path, file) for file in os.listdir(folder_path)
                     if file.endswith(".fastq") or file.endswith(".fq")]
            if len(files) == 0:
                self.logger.error(f"No sequencing files (.fastq, .fq) found at {folder_path}")
            return files
        except FileNotFoundError:
            self.logger.error("Invalid folder path")
            return []
