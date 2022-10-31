import glob
import logging
import multiprocessing
import os.path
import subprocess
import zipfile
from os import path

import requests

from build import ROOT

"""
This is a runner for a functional annotation pipeline. As input it takes raw nanopore reads, then assembles them with
flye then corrects the assembly with racon and medaka. The final assembly then gets aligned to a database, e.g. the
annotree database using DIAMOND, binned using MEGAN and finally the seperate bins are annotated using PROKKA
"""


class FunctionalAnalysisRunner():

    def __init__(self):

        self.logger = logging.getLogger('timestamp')
        self.cpus = multiprocessing.cpu_count()  # get number of cpu cores available
        self.assembly_out = f"{os.path.abspath('.')}/pipeline_out/"
        self.working_directory = os.getcwd()
        # get absolute path of all tools used and safe as class variable
        # os.chdir("../../lib/")
        self.flye_path = os.path.abspath(f"{ROOT}/lib/Flye-2.9/bin/flye")
        print(self.flye_path)
        self.minimap_path = os.path.abspath("Flye-2.9/lib/minimap2/python/minimap2.py")
        print(self.minimap_path)
        os.chdir(self.working_directory)
        # all kegg ids to input into keggcharter. TODO: put them in a file and parse them instead having them in the code
        self.kegg_ids = [10, 20, 30, 40, 51, 52, 53, 61, 62, 71, 73, 100, 120, 121, 130, 140, 190, 195, 196, 220, 230,
                         232, 240, 250, 253, 254,
                         260, 261, 270, 280, 281, 290, 300, 310, 311, 330, 331, 332, 333, 340, 350, 360, 361, 362, 363,
                         364, 365, 380, 400,
                         401, 402, 403, 404, 405, 410, 430, 440, 450, 460, 470, 480, 500, 510, 511, 512, 513, 514, 515,
                         520, 521, 522, 523,
                         524, 525, 531, 532, 533, 534, 540, 541, 542, 550, 552, 561, 562, 563, 564, 565, 571, 572, 590,
                         591, 592, 600, 601,
                         603, 604, 620, 621, 622, 623, 624, 625, 626, 627, 630, 633, 640, 642, 643, 650, 660, 670, 680,
                         710, 720, 730, 740,
                         750, 760, 770, 780, 785, 790, 791, 830, 860, 900, 901, 902, 903, 904, 905, 906, 908, 909, 910,
                         920, 930, 940, 941, 942,
                         943, 944, 945, 950, 960, 965, 966, 970, 980, 981, 982, 983, 984, 996, 997, 998, 999, 1010,
                         1040, 1051, 1052, 1053,
                         1054, 1055, 1056, 1057, 1059, 1060, 1061, 1062, 1063, 1064, 1065, 1066, 1070, 1100, 1110, 1120,
                         1200, 1210,
                         1212, 1220, 1230, 1232, 1240, 1250, 1501, 1502, 1503, 1521, 1522, 1523, 1524, 2010, 2020, 2024,
                         2025, 2026,
                         2030, 2040, 2060, 3008, 3010, 3013, 3015, 3018, 3020, 3022, 3030, 3040, 3050, 3060, 3070, 3230,
                         3240, 3250, 3320, 3410, 3420, 3430, 3440, 3450, 3460, 4010, 4011, 4012, 4013, 4014, 4015, 4016,
                         4020, 4022, 4024, 4060, 4061, 4062, 4064, 4066, 4068, 4070, 4071, 4072, 4075, 4080, 4110, 4111,
                         4112, 4113, 4114, 4115, 4120, 4122, 4130, 4136, 4137, 4138, 4139, 4140, 4141, 4142, 4144, 4145,
                         4146, 4150, 4151, 4152, 4210, 4211, 4212, 4213, 4214, 4215, 4216, 4217, 4218, 4260, 4261, 4270,
                         4310, 4320, 4330, 4340, 4341, 4350, 4360, 4361, 4370, 4371, 4380, 4390, 4391, 4392, 4510, 4512,
                         4514, 4520, 4530, 4540, 4550, 4610, 4611, 4612, 4613, 4614, 4620, 4621, 4622, 4623, 4624, 4625,
                         4626, 4630, 4640, 4650, 4657, 4658, 4659, 4660, 4662, 4664, 4666, 4668, 4670, 4672, 4710, 4711,
                         4712, 4713, 4714, 4720, 4721, 4722, 4723, 4724, 4725, 4726, 4727, 4728, 4730, 4740, 4742, 4744,
                         4745, 4750, 4810, 4910, 4911, 4912, 4913, 4914, 4915, 4916, 4917, 4918, 4919, 4920, 4921, 4922,
                         4923, 4924, 4925, 4926, 4927, 4928, 4929, 4930, 4931, 4932, 4933, 4934, 4935, 4936, 4940, 4950,
                         4960, 4961, 4962, 4964, 4966, 4970, 4971, 4972, 4973, 4974, 4975, 4976, 4977, 4978, 4979, 5010,
                         5012, 5014, 5016, 5017, 5020, 5022, 5030, 5031, 5032, 5033, 5034, 5100, 5110, 5111, 5120, 5130,
                         5131, 5132, 5133, 5134, 5135, 5140, 5142, 5143, 5144, 5145, 5146, 5150, 5152, 5160, 5161, 5162,
                         5163, 5164, 5165, 5166, 5167, 5168, 5169, 5170, 5171, 5200, 5202, 5203, 5204, 5205, 5206, 5207,
                         5208, 5210, 5211, 5212, 5213, 5214, 5215, 5216, 5217, 5218, 5219, 5220, 5221, 5222, 5223, 5224,
                         5225, 5226, 5230, 5231, 5235, 5310, 5320, 5321, 5322, 5323, 5330, 5332, 5340, 5410, 5412, 5414,
                         5415, 5416, 5417, 5418, 7011, 7012, 7013, 7014, 7015, 7016, 7017, 7018, 7019, 7020, 7021, 7023,
                         7024, 7025, 7026, 7027, 7028, 7029, 7030, 7031, 7032, 7033, 7034, 7035, 7036, 7037, 7038, 7039,
                         7040, 7041, 7042, 7043, 7044, 7045, 7046, 7047, 7048, 7049, 7050, 7051, 7052, 7053, 7054, 7055,
                         7056, 7057, 7110, 7112, 7114, 7117, 7211, 7212, 7213, 7214, 7215, 7216, 7217, 7218, 7219, 7220,
                         7221, 7222, 7223, 7224, 7225, 7226, 7227, 7228, 7229, 7230, 7231, 7232, 7233, 7234, 7235]
        self.kegg_ids = [str(int) for int in self.kegg_ids]
        self.kegg_ids = [s.zfill(5) for s in self.kegg_ids]

        self.kegg_ids = ",".join(self.kegg_ids)

    def check_software_avail(self):
        try:
            subprocess.call([f'{ROOT}/lib/Flye-2.9/bin/flye', '-h'], stdout=open(os.devnull, 'w'),
                            stderr=subprocess.STDOUT)
        except FileNotFoundError:
            self.logger.error("Flye executable not found.")

        try:
            subprocess.call(['racon', '-h'], stdout=open(os.devnull, 'w'), stderr=subprocess.STDOUT)
        except FileNotFoundError:
            self.logger.error(
                "Make sure that racon is installed and on the sytem path. For more info visit https://github.com/lbcb-sci/racon")

        # try:
        #     subprocess.call(['prokka', '-h'], stdout=open(os.devnull, 'w'), stderr=subprocess.STDOUT)
        # except FileNotFoundError:
        #     self.logger.error(
        #         "Prokka is not found in PATH. Try installing via conda")
        #     subprocess.call("conda install -c conda-forge -c bioconda -c defaults prokka")

        try:
            subprocess.call(['medaka_cocnsensus', '-h'], stdout=open(os.devnull, 'w'), stderr=subprocess.STDOUT)
        except FileNotFoundError:
            self.logger.error(
                "Make sure that medaka is installed and on the sytem path. For more info visit https://github.com/fenderglass/Flye/blob/flye/docs/INSTALL.md"
                "If you have troubles installing on ubuntu try running ")
            self.logger.error("bzip2 g++ zlib1g-dev libbz2-dev liblzma-dev libffi-dev libncurses5-dev")
            self.logger.error("libcurl4-gnutls-dev libssl-dev curl make cmake wget python3-all-dev")
            self.logger.error("python-virtualenv")
            self.logger.error("first.")

        try:
            subprocess.call(['diamond', 'help'], stdout=open(os.devnull, 'w'), stderr=subprocess.STDOUT)
        except FileNotFoundError:
            self.logger.error(
                "Make sure that racon is installed and on the system path. For more info visit https://github.com/bbuchfink/diamond")

    #

    def run_flye(self, read_file_path, sample_name):
        if not path.exists("pipeline_out"):
            os.system("mkdir pipeline_out")

        # create output dir if it doesn't exist
        cmd = f'{self.flye_path} --nano-raw {read_file_path} --out-dir {self.assembly_out}{sample_name} -t {self.cpus} --meta'
        os.system(cmd)

    def run_racon(self, read_file_path, sample_name):
        overlaps = f"{self.assembly_out}{sample_name}/{sample_name}_overlaps.paf"
        assembly = f"{self.assembly_out}{sample_name}/assembly.fasta"
        racon_out = f"{assembly.removesuffix('.fasta')}_racon.fasta"
        cmd = f"python {self.minimap_path} -t {self.cpus} -x ava-ont {assembly} {read_file_path} > {overlaps}"
        print(cmd)
        os.system(cmd)
        cmd = f"racon -x -6 -g -8 -w 500 -t {self.cpus} {read_file_path} {overlaps} {assembly} > {racon_out}"
        print(cmd)
        os.system(cmd)

        for i in range(3):
            cmd = f"python {self.minimap_path} -t {self.cpus} -x ava-ont {racon_out} {read_file_path} > {overlaps}"
            os.system(cmd)
            cmd = f"racon -x -6 -g -8 -w 500 -t {self.cpus} {read_file_path} {overlaps} {racon_out} > {assembly.removesuffix('.fasta')}_racon_{i}.fasta"
            racon_out = f"{assembly.removesuffix('.fasta')}_racon_{i}.fasta"
            print(cmd)
            os.system(cmd)

    def run_medaka(self, read_file_path, sample_name):
        racon_out = f"{self.assembly_out}{sample_name}/{sample_name}_racon_2.fasta"

        # cmd = '~/miniconda3/etc/profile.d/conda.sh && conda activate medaka'
        # subprocess.call(cmd,shell=True,executable='/bin/bash')

        # os.system("conda activate medaka")
        process = subprocess.Popen(
            "conda run -n medaka medaka_consensus")

        cmd = f"medaka_consensus -i {read_file_path} -d {racon_out} -o {self.assembly_out}/{sample_name}/ -t {self.cpus} -m r941_min_hac_g507"
        subprocess.call(cmd)

    def run_binning(self, sample_name):
        try:
            os.system("diamond help")
        except FileNotFoundError:
            print("Did not find DIAMOND on system path, please install with 'conda install -c bioconda diamond")
            # subprocess.check_call([sys.executable, '-m', 'conda', 'install',
            #                        '-c bioconda diamond'])
            # subprocess.call("conda install -c bioconda diamond")

        if not os.path.exists(f"{ROOT}/src/resources/db/megan-mapping-annotree-June-2021.db"):
            print("Did not find annotree MEGAN mapping fille, trying to download it from the web...")
            URL = "https://software-ab.informatik.uni-tuebingen.de/download/megan-annotree/megan-mapping-annotree-June-2021.db.zip"
            response = requests.get(URL)
            open(f"{ROOT}/src/resources/db/megan-mapping-annotree-June-2021.db.zip", "wb").write(response.content)
            with zipfile.ZipFile(f"{ROOT}/src/resources/db/megan-mapping-annotree-June-2021.db.zip", 'r') as zip_ref:
                zip_ref.extractall(f"{ROOT}/src/resources/db/")
            os.remove(f"{ROOT}/src/resources/db/megan-mapping-annotree-June-2021.db.zip")

        if not os.path.exists(f"{ROOT}/src/resources/db/annotree.dmnd"):
            print("Did not find annotree DIAMOND db, will download and build...")
            URL = "https://software-ab.informatik.uni-tuebingen.de/download/megan-annotree/annotree.fasta.gz"
            response = requests.get(URL)
            open(f"{ROOT}/src/resources/db/annotree.fasta.gz", "wb").write(response.content)
            subprocess.Popen(["diamond", "makedb", "--in", f"{ROOT}/src/resources/db/annotree.fasta.gz",
                              f"--db", f"{ROOT}/src/resources/db/annotree.dmnd", "-p", f"{self.cpus}"])
        diamond_cmd = ["diamond", "blastx", "-d", f"{ROOT}/src/resources/db/annotree.dmnd",
                       "-q", f"{ROOT}/src/resources/pipeline_out/{sample_name}/consensus.fasta", "-o",
                       f"{ROOT}/src/resources/pipeline_out/{sample_name}/consensus.daa", "--outfmt", "100", "-c1",
                       "-b12", "-t", f"{ROOT}/src/resources/pipeline_out/{sample_name}/", "-p", f"{self.cpus}",
                       "--top", "10", "-F15", "--range-culling"]
        with open(os.devnull, 'wb') as devnull:
            subprocess.Popen(diamond_cmd, stdout=devnull, stderr=subprocess.STDOUT)
        meganize_cmd = f"daa-meganizer -i {ROOT}/src/resources/pipeline_out/{sample_name}/consensus.daa" \
                       f" -mdb {ROOT}/src/resources/db/megan-mapping-annotree-June-2021.db -t {self.cpus} --lcaCoveragePercent 51 -lg"
        subprocess.call(meganize_cmd)
        read_extractor_cmd = f"read-extractor -i {ROOT}/src/resources/pipeline_out/{sample_name}/consensus.daa  -o {ROOT}/src/resources/pipeline_out/{sample_name}/bins/%t.fasta -c Taxonomy --frameShiftCorrect"
        subprocess.call(read_extractor_cmd)

    # TODO: integrade daa-meganizer and read-extractor into MMonitor
    # /home3/lucas/megan/tools/daa-meganizer -i $daa -mdb /abscratch/lucas/databases/megan-mapping-annotree-June-2021.db -t 48 --lcaCoveragePercent 51 -lg
    # /home3/lucas/megan/tools/read-extractor -i $daa -o $output_folder/extracted_reads/%t.fasta -c Taxonomy --frameShiftCorrect
    def run_prokka(self, bin_folder_path):
        fasta_files = glob.glob(f"{bin_folder_path}/*.fasta")
        for fasta in fasta_files:
            cmd = f"{ROOT}/lib/prokka-1.14.5/bin/prokka --outdir {bin_folder_path}" \
                  f" --force --prefix $(basename {fasta}) {fasta}  --cpus 0 --addgenes"
            subprocess.call(cmd)

    def create_keggcharter_input(self, path_to_prokka_output):
        keggcharter_sheet = {'taxonomy': ['']}
        df = pd.DataFrame(keggcharter_sheet)
        df_list = []
        df.to_csv(path_to_prokka_output + "keggcharter.tsv", sep='\t')
        for tsv in glob.glob(f"{path_to_prokka_output}/tsvs/*.tsv"):
            print(tsv)
            data = pd.read_csv(tsv, sep='\t')
            tax = tsv.split('.tsv')[0]
            tax = tax.split('/')[-1]
            tax = tax.replace('_', ' ')
            if ".fasta" in tax:
                tax = tax.removesuffix(".fasta")
            print(tax)
            data["taxonomy"] = tax
            df_list.append(data)
        df = pd.concat(df_list)
        df.to_csv(path_to_prokka_output + "keggcharter.tsv", sep='\t')

    def run_keggcharter(self, kegg_out, keggcharter_input):
        # self.create_keggcharter_input(kegg_out,keggcharter_input)
        cmd = f"python {ROOT}/lib/KEGGCharter-0.3.4/keggcharter.py -o {kegg_out} -f {keggcharter_input} -tc taxonomy -ecc EC_number --input-quantification -mm {self.kegg_ids}"
        os.system(cmd)
