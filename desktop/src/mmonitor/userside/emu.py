import gzip
import logging
import multiprocessing
import os
import subprocess
from build import ROOT


# TODO complete implementation of this class for 16s analysis to work
class EmuRunner:

    def __init__(self):
        self.logger = logging.getLogger('timestamp')
        self.check_emu()
        self.emu_out = ""

    @staticmethod
    def unpack_fastq_list(ls):
        """
        Gets a list of paths and outputs a comma seperated string containing the paths used as input for emu
        """
        if len(ls) == 1:
            return f"{ls[0]}"
        elif len(ls) > 1:
            return ",".join(ls)

    def check_emu(self):
        try:
            subprocess.call([f"{ROOT}/lib/emu-v3.4.5/emu", '-h'], stdout=open(os.devnull, 'w'), stderr=subprocess.STDOUT)
        except FileNotFoundError:
            self.logger.error(
                "Make sure that emu is installed and on the sytem path. For more info visit http://www.ccb.jhu.edu/software/centrifuge/manual.shtml")

    def run_emu(self, sequence_list, sample_name):
        self.emu_out = f"{ROOT}/src/resources/pipeline_out/{sample_name}/"
        print(sequence_list)
        #remove concatenated files from sequence list to avoid concatenating twice
        sequence_list = [s for s in sequence_list if "concatenated" not in s]
        concat_file_name = f"{os.path.dirname(sequence_list[0])}/{sample_name}_concatenated.fastq.gz"
        if not os.path.exists(concat_file_name):
            concatenate_fastq_files(sequence_list,concat_file_name)

        if ".fasta" in sequence_list[0] or ".fa" in sequence_list[0] or ".fastq" in sequence_list[0]\
                or ".fq" in sequence_list[0]:
            cmd = f"{ROOT}/lib/emu-v3.4.5/emu abundance {concat_file_name} --db {ROOT}/src/resources/emu_db/" \
                  f" --output-dir {self.emu_out} --threads {multiprocessing.cpu_count()} --type map-ont --output-basename {sample_name}"
            print(cmd)
            os.system(cmd)
        return



    def get_files_from_folder(self, folder_path):
        """
        Gets a path to a folder, checks if path contains sequencing files with specified endings and returns list
        containing paths to sequencing files.
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

def concatenate_fastq_files(input_files, output_file):
    with gzip.open(output_file, 'wt') as output:
        for input_file in input_files:
            with gzip.open(input_file, 'rt') as input:
                for line in input:
                    output.write(line)
