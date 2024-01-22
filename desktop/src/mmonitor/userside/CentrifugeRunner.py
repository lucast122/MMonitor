import gzip
import logging
import multiprocessing
import os
import subprocess

from build_mmonitor_pyinstaller import ROOT


def concatenate_fastq_files(input_files, output_file):
    with gzip.open(output_file, 'wt') as output:
        for input_file in input_files:
            is_gzipped = input_file.endswith(".gz")
            open_func = gzip.open if is_gzipped else open
            mode = 'rt' if is_gzipped else 'r'

            with open_func(input_file, mode) as input2:
                for line in input2:
                    output.write(line)


class CentrifugeRunner:

    def __init__(self):
        self.logger = logging.getLogger('timestamp')
        self.check_centrifuge()
        self.cent_out = ""
        self.concat_file_name = ""

    @staticmethod
    def unpack_fastq_list(ls):
        """
        Gets a list of paths and outputs a comma seperated string containing the paths used as input for centrifuge
        """
        if len(ls) == 1:
            return f"{ls[0]}"
        elif len(ls) > 1:
            return ",".join(ls)

    def check_centrifuge(self):
        try:
            subprocess.call(['centrifuge', '-h'], stdout=open(os.devnull, 'w'), stderr=subprocess.STDOUT)
        except FileNotFoundError:
            self.logger.error(
                "Make sure that centrifuge is installed and on the sytem path. For more info visit http://www.ccb.jhu.edu/software/centrifuge/manual.shtml")

    def run_centrifuge(self, sequence_list,sample_name,database_path):
        print(sequence_list)
        #remove concatenated files from sequence list to avoid concatenating twice
        sequence_list = [s for s in sequence_list if "concatenated" not in s]
        concat_file_name = f"{ROOT}/src/resources/pipeline_out/{sample_name}_concatenated.fastq.gz"
        self.concat_file_name = concat_file_name

        self.cent_out = f"{ROOT}/src/resources/pipeline_out/{sample_name}_cent_out"

        if not os.path.exists(concat_file_name):
            concatenate_fastq_files(sequence_list, concat_file_name)

        if sequence_list[0].lower().endswith(('.fq', '.fastq', '.fastq.gz', '.fq.gz')):
            self.cent_out = f"{ROOT}/src/resources/pipeline_out/{sample_name}_cent_out"
            # if ".fastq" in sequence_list[0] or ".fq" in sequence_list[0] or ".fastq.gz" in sequence_list[0]:

            cmd = f'centrifuge -x "{database_path}" -U {concat_file_name} -p {multiprocessing.cpu_count()} -S {self.cent_out}'
            print(cmd)
            os.system(cmd)
            # return
        if ".fasta" in sequence_list[0] or ".fa" in sequence_list[0]:
            cmd = f'centrifuge -x "{database_path}" -f {concat_file_name} -p {multiprocessing.cpu_count()} -S {self.cent_out}'
            print(cmd)
            os.system(cmd)
            # return
        self.make_kraken_report(database_path)
        return

    def make_kraken_report(self,centrifuge_index_path):
        cmd = f"centrifuge-kreport -x {centrifuge_index_path} {self.cent_out} > {self.cent_out.replace('cent_out', 'kraken_out')}"
        print(cmd)
        os.system(cmd)

    def get_files_from_folder(self, folder_path):
        """
        Gets a path to a folder, checks if path contains sequencing files with specified endings and returns list
        containing paths to sequencing files. centrifuge
        """
        files = []
        found = False
        try:
            for file in os.listdir(folder_path):
                print(file)
                if file.endswith(".fastq") or file.endswith(".fq") or file.endswith(".fasta") or file.endswith(
                        ".fastq.gz"):
                    files.append(f"{folder_path}/{file}")
                    found = True
            if not found:
                self.logger.error(f"No sequencing files (.fastq, .fq found at {folder_path}")
            return files
        except FileNotFoundError:
            self.logger.error(f"Invalid folder path")
