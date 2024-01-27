import gzip
import logging
import multiprocessing
import os
import subprocess

from build_mmonitor_pyinstaller import ROOT
from Bio import SeqIO
import gzip
from concurrent.futures import ThreadPoolExecutor
import concurrent
from threading import Lock
import gzip
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import Manager

class CentrifugeRunner:

    def __init__(self):
        self.logger = logging.getLogger('timestamp')
        self.check_centrifuge()
        self.cent_out = ""
        self.concat_file_name = ""

    @staticmethod
    def process_file(file, outfile_lock, outfile):
        """
        Process a single FASTQ or FASTQ.GZ file and write to the output file.

        :param file: Path to the FASTQ or FASTQ.GZ file.
        :param outfile_lock: A lock for thread-safe writing to the output file.
        :param outfile: Handle to the output gzipped FASTQ file.
        """
        file_open = gzip.open if file.endswith('.gz') else open
        with file_open(file, 'rt') as handle:
            for record in SeqIO.parse(handle, "fastq"):
                with outfile_lock:
                    SeqIO.write(record, outfile, "fastq")


    @staticmethod
    def concatenate_files_in_memory(file_paths):
        """
        Create a file-like object that virtually concatenates multiple files.
        """
        concatenated_content = StringIO()
        for file_path in file_paths:
            with open(file_path, 'r') as file:
                concatenated_content.write(file.read())
        concatenated_content.seek(0)
        return concatenated_content

    @staticmethod
    def process_file(file, shared_list):
        with gzip.open(file, 'rt') as infile:
            file_content = infile.read()
        shared_list.append(file_content)

    @staticmethod
    def concatenate_fastq_parallel(files, output_file):
        files_to_process = [file for file in files if "concatenated" not in file]

        with Manager() as manager:
            shared_list = manager.list()  # shared list to collect file contents
            with ProcessPoolExecutor() as executor:
                executor.map(CentrifugeRunner.process_file, files_to_process, [shared_list] * len(files_to_process))

            with gzip.open(output_file, 'wt') as outfile:
                for content in shared_list:
                    outfile.write(content)

    @staticmethod
    def concatenate_to_tempfile(file_paths):
        """
        Concatenate multiple files into a temporary file.
        Returns the path of the temporary file.
        """
        with tempfile.NamedTemporaryFile(delete=False, mode='w+') as temp_file:
            for file_path in file_paths:
                with open(file_path, 'r') as file:
                    temp_file.write(file.read())
            return temp_file.name


    @staticmethod
    def make_kraken_report(centrifuge_index_path, cent_out):
        cmd = f"centrifuge-kreport -x {centrifuge_index_path} {cent_out} > {cent_out.replace('cent_out', 'kraken_out')}"
        print(cmd)
        os.system(cmd)

    @staticmethod
    def process_line(line, centrifuge_index_path):
        columns = line.strip().split('\t')
        if len(columns) < 5:
            return
        col_path, output_file = columns[3], columns[4]
        cmd = ["centrifuge-kreport", "-x", centrifuge_index_path, col_path]
        with open(output_file, 'w') as output:
            subprocess.run(cmd, stdout=output, stderr=subprocess.DEVNULL)

    @staticmethod
    def make_kraken_report_from_tsv(file_path, centrifuge_index_path, max_workers=64):
        with open(file_path, 'r') as file, concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(CentrifugeRunner.process_line, line, centrifuge_index_path) for line in file]
            concurrent.futures.wait(futures)

    @staticmethod
    def run_centrifuge_multi_sample(centrifuge_tsv_path, database_path):
        cmd = f'centrifuge -x "{database_path}" --sample-sheet {centrifuge_tsv_path} -p {multiprocessing.cpu_count()}'
        os.system(cmd)

    @staticmethod
    def create_centrifuge_input_file(sample_names, concat_file_names, output_tsv_file):
        """
        Creates a TSV file for running centrifuge in multi sample mode.

        :param sample_names: List of sample names.
        :param concat_file_name: The concatenated file name for read-file1.
        :param output_tsv_file: The path to the output TSV file.
        """
        with open(output_tsv_file, 'w') as file:
            # no header
            # Write the data rows
            for idx, sample_name in enumerate(sample_names):
                classification_result_output = f"{ROOT}/src/resources/pipeline_out/{sample_name}_cent_out"
                report_file = f"{ROOT}/src/resources/pipeline_out/{sample_name}_kraken_out"
                file.write(
                    f"1\t{concat_file_names[idx]}\tread-file2\t{classification_result_output}\t{report_file}\n")

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
        concat_file_name = f"{os.path.dirname(sequence_list[0])}/{sample_name}_concatenated.fastq.gz"
        self.concat_file_name = concat_file_name

        self.cent_out = f"{ROOT}/src/resources/pipeline_out/{sample_name}_cent_out"

        concatenate_fastq_files(sequence_list, concat_file_name)
        if sequence_list[0].lower().endswith(('.fq', '.fastq', '.fastq.gz', '.fq.gz')):
            cmd = f'centrifuge -x "{database_path}" -U {concat_file_name} -p {multiprocessing.cpu_count()} -S {self.cent_out}'
            print(cmd)
            os.system(cmd)
            make_kraken_report(database_path)
            os.remove(self.concat_file_name)
            return

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
