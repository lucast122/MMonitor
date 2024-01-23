import argparse
import csv
import json
import os

import numpy as np

from build_mmonitor_pyinstaller import ROOT
from mmonitor.userside.FastqStatistics import FastqStatistics
from mmonitor.userside.InputWindow import get_files_from_folder
from src.mmonitor.database.django_db_interface import DjangoDBInterface
from src.mmonitor.userside.CentrifugeRunner import CentrifugeRunner
from src.mmonitor.userside.EmuRunner import EmuRunner


class MMonitorCMD:
    def __init__(self):
        self.use_multiplexing = None
        self.multi_sample_input = None
        self.emu_runner = EmuRunner()
        self.centrifuge_runner = CentrifugeRunner()
        self.args = self.parse_arguments()
        self.db_config = {}
        self.django_db = DjangoDBInterface(self.args.config)

    def parse_arguments(self):
        parser = argparse.ArgumentParser(description='MMonitor command line tool')
        parser.add_argument('-a', '--analysis', required=True, choices=['taxonomy-wgs', 'taxonomy-16s', 'functional'],
                            help='Type of analysis to perform')
        parser.add_argument('-c', '--config', required=True, type=str, help='Path to JSON config file')

        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument('-m', '--multicsv', type=str, help='Path to CSV containing information for multiple samples')
        group.add_argument('-i', '--input', type=str, help='Path to folder containing sequencing data')

        parser.add_argument('-s', '--sample', type=str, help='Sample name')
        parser.add_argument('-d', '--date', type=str, help='Sample date')
        parser.add_argument('-p', '--project', type=str, help='Project name')
        parser.add_argument('-u', '--subproject', type=str, help='Subproject name')
        parser.add_argument('-b', '--barcodes', action="store_true",
                            help='Use barcode column from CSV for handling multiplexing')
        parser.add_argument("--overwrite", action="store_true",
                            help="Enable to overwrite existing records. If not specified, defaults to False.")

        parser.add_argument('-q', '--qc', action="store_true",
                            help='Calculate quality control statistics for input samples.'
                                                          ' Enable this to fill QC app with data. Increases time the analysis takes.')
        parser.add_argument('-x', '--update', action="store_true", help='Only update counts and abundances'
                                                              ' Enable this if you want to send count and abundances to the MMonitor webserver DB. '
                                                              ' Can be useful, e.g. when the tsv files from emu changed after analysis.')
        parser.add_argument('-n', '--minabundance', type=float, default=0.5,
                            help='Minimal abundance to be considered for 16s taxonomy')



        return parser.parse_args()

    def load_config(self):
        if os.path.exists(self.args.config):
            try:
                with open(self.args.config, "r") as f:
                    self.db_config = json.load(f)
                    print(f"DB config {self.args.config} loaded successfully.")
            except json.JSONDecodeError:
                print("Couldn't load DB config. Please make sure you provided the correct path to the file.")
        else:
            print(f"Config path doesn't exist")

    def add_statistics(self, fastq_file, sample_name, project_name, subproject_name, sample_date):
        fastq_stats = FastqStatistics(fastq_file)

        # Calculate statistics
        fastq_stats.quality_statistics()
        fastq_stats.read_lengths_statistics()
        quality_vs_lengths_data = fastq_stats.qualities_vs_lengths()
        gc_contents = fastq_stats.gc_content_per_sequence()

        data = {
            'sample_name': sample_name,
            'project_id': project_name,
            'subproject_id': subproject_name,
            'date': sample_date,
            'mean_gc_content': fastq_stats.gc_content(),
            'mean_read_length': np.mean(fastq_stats.lengths),
            'median_read_length': np.median(fastq_stats.lengths),
            'mean_quality_score': np.mean([np.mean(q) for q in fastq_stats.qualities]),
            'read_lengths': json.dumps(quality_vs_lengths_data['read_lengths']),
            'avg_qualities': json.dumps(quality_vs_lengths_data['avg_qualities']),
            'number_of_reads': fastq_stats.number_of_reads(),
            'total_bases_sequenced': fastq_stats.total_bases_sequenced(),
            'q20_score': fastq_stats.q20_q30_scores()[0],
            'q30_score': fastq_stats.q20_q30_scores()[1],
            'avg_quality_per_read': fastq_stats.quality_score_distribution()[0],
            'base_quality_avg': fastq_stats.quality_score_distribution()[1],
            'gc_contents_per_sequence': json.dumps(gc_contents)

        }

        self.django_db.send_sequencing_statistics(data)

    # method to check if a sample is already in the database, if user does not want to overwrite results
    # returns true if sample_name is in db and false if not
    def check_sample_in_db(self, sample_id):
        samples_in_db = self.django_db.get_unique_sample_ids()
        return sample_id in samples_in_db


    def taxonomy_nanopore_16s(self):
        global sample_name, project_name, subproject_name, sample_date

        def add_sample_to_databases(sample_name, project_name, subproject_name, sample_date):
            emu_out_path = f"{ROOT}/src/resources/pipeline_out/{sample_name}/"
            self.django_db.update_django_with_emu_out(emu_out_path, "species", sample_name, project_name, sample_date,
                                                      subproject_name, self.args.overwrite)
            print(self.args.overwrite)

        if not os.path.exists(os.path.join(ROOT, "src", "resources", "emu_db", "taxonomy.tsv")):
            print("emu db not found")



        if not self.args.multicsv:
            sample_name = str(self.args.sample)
            # when a sample is already in the database and user does not want to overwrite quit now
            if not self.args.overwrite:
                if self.check_sample_in_db(sample_name):
                    return
            project_name = str(self.args.project)
            subproject_name = str(self.args.subproject)
            sample_date = self.args.date.strftime('%Y-%m-%d')  # Convert date to string format
            files = self.args.input
            if self.args.update:
                print("Update parameter specified. Will only update results from file.")
                add_sample_to_databases(sample_name, project_name, subproject_name, sample_date)
                return

            self.emu_runner.run_emu(files, sample_name, self.args.minabundance)

            add_sample_to_databases(sample_name, project_name, subproject_name, sample_date)
        else:
            self.load_from_csv()
            print("Processing multiple samples")
            for index, file_path_list in enumerate(self.multi_sample_input["file_paths_lists"]):
                files = file_path_list
                sample_name = self.multi_sample_input["sample_names"][index]
                # when a sample is already in the database and user does not want to overwrite quit now
                if not self.args.overwrite:
                    if self.check_sample_in_db(sample_name):
                        print(
                            f"Sample {sample_name} already in DB and overwrite not specified, continue with next sample...")
                        continue
                project_name = self.multi_sample_input["project_names"][index]
                subproject_name = self.multi_sample_input["subproject_names"][index]
                sample_date = self.multi_sample_input["dates"][index]
                if self.args.update:
                    print("Update parameter specified. Will only update results from file.")
                    add_sample_to_databases(sample_name, project_name, subproject_name, sample_date)
                    continue

                self.emu_runner.run_emu(files, sample_name, self.args.minabundance)
                add_sample_to_databases(sample_name, project_name, subproject_name, sample_date)

        # calculate QC statistics if qc argument is given by user
        if self.args.qc:
            self.add_statistics(self.emu_runner.concat_file_name, sample_name, project_name, subproject_name,
                                sample_date)
            print("adding statistics")

        # emu_out_path = f"{ROOT}/src/resources/pipeline_out/subset/"

        # if self.db is not None:
        #     self.db.update_table_with_emu_out(emu_out_path, "species", sample_name, "project", self.sample_date)
        #
        # self.db_mysql.update_django_with_emu_out(emu_out_path, "species", sample_name, project_name, sample_date,
        #                                          subproject_name)

        print("Analysis complete. You can start monitoring now.")

    def load_from_csv(self):
        file_path = self.args.multicsv

        if not file_path:
            print("CSV file not provided")
            return

        # Check if CSV is empty
        if os.path.getsize(file_path) == 0:
            print("Selected CSV file is empty.")
            return

        error_messages = []  # list to accumulate error messages

        # Prepare dictionary to hold multiple sample data
        self.multi_sample_input = {
            "file_paths_lists": [],
            "sample_names": [],
            "dates": [],
            "project_names": [],
            "subproject_names": []
        }

        with open(file_path, 'r') as file:
            reader = csv.DictReader(file)

            for row in reader:
                # Check if provided path exists
                if not os.path.exists(row["sample folder"].strip()):
                    error_message = f"Invalid path from CSV: {row['sample folder'].strip()}"
                    print(error_message)
                    error_messages.append(error_message)
                    continue

                # Look for the fastq_pass folder in the provided path and its child directories
                folder_path = None
                for root, dirs, files in os.walk(row["sample folder"].strip()):
                    if "fastq_pass" in dirs:
                        folder_path = os.path.join(root, "fastq_pass")
                        break
                    else:
                        folder_path = os.path.join(root)

                if not folder_path:
                    error_message = f"'fastq_pass' directory not found for path: {row['sample folder'].strip()}"
                    print(error_message)
                    error_messages.append(error_message)
                    continue

                # If multiplexing is selected, navigate further to the barcode_x folder
                if self.args.barcodes:
                    barcode_id_string = str(row['Barcode ID'])

                    if len(barcode_id_string) == 1:
                        barcode_id_string = f"0{barcode_id_string}"

                    barcode_folder = f"barcode{barcode_id_string}"
                    folder_path = os.path.join(folder_path, barcode_folder)

                    if not os.path.exists(folder_path):
                        error_message = f"Barcode folder '{barcode_folder}' not found."
                        print(error_message)
                        error_messages.append(error_message)
                        continue

                files = get_files_from_folder(folder_path)
                print(files)

                # Extract attributes from CSV and check for errors
                required_columns = ["sample_name", "date", "project_name", "subproject_name"]
                for col in required_columns:
                    if not row[col]:
                        error_message = f"Missing {col} in CSV for path: {row['sample folder']}"
                        print(error_message)
                        error_messages.append(error_message)

                # Store extracted CSV information to multi_sample_input
                self.multi_sample_input["file_paths_lists"].append(files)
                self.multi_sample_input["sample_names"].append(row["sample_name"])
                self.multi_sample_input["dates"].append(row["date"])
                self.multi_sample_input["project_names"].append(row["project_name"])
                self.multi_sample_input["subproject_names"].append(row["subproject_name"])

            # Provide feedback on the number of samples to be processed
            num_samples_to_process = len(self.multi_sample_input["file_paths_lists"])
            if num_samples_to_process <= 5:
                print(f"Processing {num_samples_to_process} samples.")
            else:
                print(f"Processing {num_samples_to_process} samples. This may take a while.")

        # Handle error messages from loading the CSV

    def taxonomy_nanopore_wgs(self):
        cent_db_path = os.path.join(ROOT, 'src', 'resources', 'dec_22')

        def add_sample_to_databases(sample_name, project_name, subproject_name, sample_date):
            kraken_out_path = f"{ROOT}/src/resources/pipeline_out/{sample_name}_kraken_out"
            self.django_db.send_nanopore_record_centrifuge(kraken_out_path, sample_name, project_name, subproject_name,
                                                           sample_date, self.args.overwrite)
            print(self.args.overwrite)

        if not os.path.exists(os.path.join(ROOT, "src", "resources", "dec_22.1.cf")):
            print("centrifuge db not found")

        if not self.args.multicsv:
            sample_name = str(self.args.sample)
            # when a sample is already in the database and user does not want to overwrite quit now
            if not self.args.overwrite:
                if self.check_sample_in_db(sample_name):
                    print("Sample is already in DB use --overwrite to overwrite it...")
                    return
            project_name = str(self.args.project)
            subproject_name = str(self.args.subproject)
            # sample_date = self.args.date.strftime('%Y-%m-%d')  # Convert date to string format
            sample_date = self.args.date  # Convert date to string format

            files = self.args.input
            files = get_files_from_folder(files)
            if self.args.update:
                print("Update parameter specified. Will only update results from file.")
                add_sample_to_databases(sample_name, project_name, subproject_name, sample_date)
                return

            # self.emu_runner.run_emu(files, sample_name, self.args.minabundance)
            self.centrifuge_runner.run_centrifuge(files, sample_name, cent_db_path)
            self.centrifuge_runner.make_kraken_report(cent_db_path)

            add_sample_to_databases(sample_name, project_name, subproject_name, sample_date)
        else:
            self.load_from_csv()
            print("Processing multiple samples")
            for index, file_path_list in enumerate(self.multi_sample_input["file_paths_lists"]):
                files = file_path_list
                sample_name = self.multi_sample_input["sample_names"][index]
                # when a sample is already in the database and user does not want to overwrite quit now
                if not self.args.overwrite:
                    if self.check_sample_in_db(sample_name):
                        print(
                            f"Sample {sample_name} already in DB and overwrite not specified, continue with next sample...")
                        continue
                project_name = self.multi_sample_input["project_names"][index]
                subproject_name = self.multi_sample_input["subproject_names"][index]
                sample_date = self.multi_sample_input["dates"][index]
                if self.args.update:
                    print("Update parameter specified. Will only update results from file.")
                    add_sample_to_databases(sample_name, project_name, subproject_name, sample_date)
                    continue

                self.centrifuge_runner.run_centrifuge(files, sample_name, cent_db_path)
                self.centrifuge_runner.make_kraken_report(cent_db_path)
                add_sample_to_databases(sample_name, project_name, subproject_name, sample_date)

        # calculate QC statistics if qc argument is given by user
        if self.args.qc:
            self.add_statistics(self.centrifuge_runner.concat_file_name, sample_name, project_name, subproject_name,
                                sample_date)
            print("adding statistics")



if __name__ == "__main__":
    command_runner = MMonitorCMD()
    print(command_runner.args)
    command_runner.load_config()
    if command_runner.args.analysis == "taxonomy-16s":
        command_runner.taxonomy_nanopore_16s()
    if command_runner.args.analysis == "taxonomy-wgs":
        command_runner.taxonomy_nanopore_wgs()
