import logging
import os
import subprocess


class KaijuRunner:
    def __init__(self):
        self.setup_logging()
        self.check_kaiju()
        self.output_path = "kaiju_output"  # Set a default path for Kaiju outputs

    def setup_logging(self):
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def check_kaiju(self):
        try:
            subprocess.run(["kaiju"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except FileNotFoundError:
            self.logger.error("Make sure that Kaiju is installed and on the system path.")

    def run_kaiju(self, sequence_list, sample_name):
        output_dir = os.path.join(self.output_path, sample_name)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        for seq_file in sequence_list:
            cmd = [
                "kaiju",
                "-t", "/path/to/nodes.dmp",
                "-f", "/path/to/kaiju_db.fmi",
                "-i", seq_file,
                "-o", os.path.join(output_dir, f"{os.path.basename(seq_file)}.out")
            ]
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
