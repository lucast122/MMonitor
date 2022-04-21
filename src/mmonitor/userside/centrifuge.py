import os
import glob
import logging
import subprocess
import multiprocessing
import pathlib


class CentrifugeRunner():

    def __init__(self):
        self.logger = logging.getLogger('timestamp')
        self.check_centrifuge()
        self.cent_out = ""

    # this method gets a list of paths and outputs a comma seperated string containing the paths used as input for centrifuge
    def unpack_fastq_list(self,list):
        if len(list) == 1:
            return f"{list[0]}"
        elif len(list) > 1:
            return ",".join(list)
    def check_centrifuge(self):
        try:
            subprocess.call(['centrifuge','-h'],stdout=open(os.devnull, 'w'), stderr=subprocess.STDOUT)
        except FileNotFoundError:
            self.logger.error("Make sure that centrifuge is installed and on the sytem path. For more info visit http://www.ccb.jhu.edu/software/centrifuge/manual.shtml")

    def run_centrifuge(self, sequence_list, centrifuge_index, sample_name):
        cmd = ""
        print(sequence_list)
        if sequence_list[0].lower().endswith(('.fq','.fastq','.fastq.gz','.fq.gz')):
        # if ".fastq" in sequence_list[0] or ".fq" in sequence_list[0] or ".fastq.gz" in sequence_list[0]:
            self.cent_out=f"{pathlib.Path(__file__).parent.resolve()}/classifier_out/{sample_name}_cent_out"
            cmd = f'centrifuge -x {centrifuge_index} -U {self.unpack_fastq_list(sequence_list)} -p {multiprocessing.cpu_count()} -S {pathlib.Path(__file__).parent.resolve()}/classifier_out/{sample_name}_cent_out'
            print(cmd)
            os.system(cmd)
            return
        if ".fasta" in sequence_list[0] or ".fa" in sequence_list[0]:
            self.cent_out=f"{pathlib.Path(__file__).parent.resolve()}/classifier_out/{sample_name}_cent_out"
            cmd = f'centrifuge -x {centrifuge_index} -f {self.unpack_fastq_list(sequence_list)} -p {multiprocessing.cpu_count()} -S {pathlib.Path(__file__).parent.resolve()}/classifier_out/{sample_name}_cent_out'
            print(cmd)
            os.system(cmd)
            return
    def make_kraken_report(self,centrifuge_index):
        cmd = f"centrifuge-kreport -x {centrifuge_index} {self.cent_out} > {self.cent_out.replace('cent_out','kraken_out')}"
        os.system(cmd)

    # gets a path to a folder, checks if path contains sequencing files with specified endings and returns list
    # containing paths to sequencing files. centrifuge
    def get_files_from_folder(self, folder_path):
        files = []
        found=False
        try:
            for file in os.listdir(folder_path):
                print(file)
                if file.endswith(".fastq") or file.endswith(".fq") or file.endswith(".fasta") or file.endswith(".fastq.gz"):
                    files.append(f"{folder_path}/{file}")
                    found = True
            if not found:
                self.logger.error(f"No sequencing files (.fastq, .fq found at {folder_path}")
            return files
        except FileNotFoundError:
            self.logger.error(f"Invalid folder path")




# c = CentrifugeRunner()
# c.check_centrifuge()
# c.run_centrifuge(['/Users/timolucas/Downloads/r1_august_g5_5perc.fastq'], '/Users/timolucas/Downloads/p_compressed_2018_4_15/p_compressed', 'test')
# c.make_kraken_report('/Users/timolucas/Downloads/p_compressed_2018_4_15/p_compressed')



