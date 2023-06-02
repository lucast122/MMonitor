# from tkcalendar import Calendar
import gzip
import os
import tarfile
import tkinter as tk
import urllib.request
from datetime import date
from threading import Thread
from time import sleep
from tkinter import *
from tkinter import messagebox
from tkinter import simpledialog
from tkinter import ttk
from webbrowser import open_new

from PIL import Image, ImageTk
from requests import post

from build import ROOT
from dist.mmonitor.future.moves.tkinter import filedialog
from mmonitor.dashapp.index import Index
from mmonitor.database.mmonitor_db import MMonitorDBInterface
from mmonitor.userside.centrifuge import CentrifugeRunner
from mmonitor.userside.emu import EmuRunner
from mmonitor.userside.functional_analysis import FunctionalAnalysisRunner

# from mmonitor.userside.downloader import Downloader

"""
This file represents the basic gui for the desktop app. It is the entry point for the program and the only way 
for the user to create projects, select files and run MMonitor's computational engine (centrifuge at this moment)
"""


def require_project(func):
    """Decorator that ensures that a database was selected or created by the user."""

    def func_wrapper(*args):
        obj: GUI = args[0]
        if obj.db_path is not None and len(obj.db_path) > 0:
            return func(*args)
        else:
            obj.open_popup("Please first create or choose a project data base.", "No data base chosen")

    return func_wrapper


# def require_centrifuge(func):
#     """Decorator that ensures that a centrifuge index was selected by the user."""
#
#     def func_wrapper(*args):
#         obj: GUI = args[0]
#         if obj.centrifuge_index is not None and len(obj.centrifuge_index) > 0:
#             return func(*args)
#         else:
#             obj.open_popup("Please first select a centrifuge index before analyzing files.", "Centrifuge error")
#
#     return func_wrapper


def calendar_picker(but_exit=None):
    tkobj = tk.Tk()
    # setting up the geomentry
    tkobj.geometry("500x500")
    tkobj.title("Calendar picker")
    # creating a calender object
    tkc = Calendar(tkobj, selectmode="day", year=2022, month=1, date=1)
    # display on main window
    tkc.pack(pady=40)

    # getting date from the calendar
    def fetch_date():
        date.config(text="Selected Date is: " + tkc.get_date())

    # add button to load the date clicked on calendar
    but = tk.Button(tkobj, text="Select Date", command=fetch_date, bg="black", fg='white')
    # displaying button on the main display
    but.pack()

    but_exit = tk.Button(tkobj, text="Exit", command=tkobj.destroy, bg="black", fg='white')
    # displaying button on the main display
    but_exit.pack()

    # Label for showing date on main display
    date = tk.Label(tkobj, text="", bg='black', fg='white')
    date.pack(pady=20)
    # starting the object
    tkobj.mainloop()
    return tkc.get_date()


class GUI:

    def __init__(self):
        # declare data base class variable, to be chosen by user with choose_project()
        self.db: MMonitorDBInterface = None
        self.db_path = None
        self.cent = CentrifugeRunner()
        self.emu = EmuRunner()
        self.func = FunctionalAnalysisRunner()
        self.dashapp = None
        self.monitor_thread = None
        self.root = Tk()
        self.init_layout()
        self.taxonomy_nanopore_wgs = tk.BooleanVar()
        self.taxonomy_nanopore_16s_bool = tk.BooleanVar()
        self.assembly = tk.BooleanVar()
        self.correction = tk.BooleanVar()
        self.binning = tk.BooleanVar()
        self.annotation = tk.BooleanVar()
        self.kegg = tk.BooleanVar()


    def init_layout(self):

        self.root.geometry("300x300")
        self.root.title("MMonitor v0.1.0 alpha")
        self.root.resizable(width=False, height=False)
        ico = Image.open(f"{ROOT}/src/resources/images/mmonitor_logo.png")
        photo = ImageTk.PhotoImage(ico)

        self.root.wm_iconphoto(False, photo)

        self.width = 20
        self.height = 1
        # create buttons

        # uni tuebingen colours
        # #B22222 red
        # #444E57 grey
        button_bg = '#444E57'
        button_active_bg = "#444E57"
        tk.Button(self.root, text="Create Project", command=self.create_project,
                  padx=10, pady=5, width=self.width, height=self.height, fg='black', bg=button_bg,
                  activebackground=button_active_bg, ).pack()
        tk.Button(self.root, text="Choose Project", command=self.choose_project,
                  padx=10, pady=5, width=self.width, height=self.height, fg='black', bg=button_bg,
                  activebackground=button_active_bg).pack()
        # tk.Button(self.root, text="Choose centrifuge index", command=self.choose_index,
        #           padx=10, pady=5, width=self.width,height=self.height, fg='white', bg='#254D25').pack()
        # # tk.Button(self.root, text="Analyze fastq in folder", command=self.analyze_fastq_in_folder,
        #           padx=10, pady=5, width=self.width,height=self.height, fg='white', bg='#254D25').pack()
        tk.Button(self.root, text="Add metadata from CSV", command=self.append_metadata,
                  padx=10, pady=5, width=self.width, height=self.height, fg='black', bg=button_bg,
                  activebackground=button_active_bg).pack()
        tk.Button(self.root, text="Run analysis pipeline", command=self.checkbox_popup,
                  padx=10, pady=5, width=self.width, height=self.height, fg='black', bg=button_bg,
                  activebackground=button_active_bg).pack()

        tk.Button(self.root, text="Start monitoring", command=self.start_monitoring,
                  padx=10, pady=5, width=self.width, height=self.height, fg='black', bg=button_bg,
                  activebackground=button_active_bg).pack()
        tk.Button(self.root, text="Quit",
                  padx=10, pady=5, width=self.width, height=self.height, fg='black', bg=button_bg,
                  activebackground=button_active_bg,
                  command=self.stop_app).pack()

        # console = Console(self.root)

    def open_popup(self, text, title):
        top = tk.Toplevel(self.root)
        top.geometry("700x300")
        top.title(title)
        tk.Label(top, text=text, font='Mistral 18 bold').place(x=150, y=80)
        tk.Button(top, text="Okay", command=top.destroy).pack()

    def create_project(self):
        filename = filedialog.asksaveasfilename(
            initialdir='projects/',
            title="Choose place to safe the project data"
        )
        filename += ".sqlite3"
        self.db_path = filename
        self.db = MMonitorDBInterface(filename)
        self.db.create_db(filename)

    def choose_project(self):

        self.db_path = filedialog.askopenfilename(
            initialdir='projects/',
            title="Choose project data base to use",
            filetypes=(("sqlite", "*.sqlite3"), ("all files", "*.*"))
        )
        self.db = MMonitorDBInterface(self.db_path)
        # self.db = "mmonitor.sqlite3"

    # def choose_index(self):
    #     self.centrifuge_index = filedialog.askopenfilename(
    #         initialdir='projects/',
    #         title="Choose project data base to use",
    #         filetypes=(("sqlite", "*.sqlite3"), ("all files", "*.*"))
    #     )

    @require_project
    def append_metadata(self):
        csv_file = filedialog.askopenfilename(
            initialdir='projects/',
            title="Choose csv file containing metadata to append",
            filetypes=(("csv", "*.csv"), ("all files", "*.*"))
        )
        if csv_file is not None and len(csv_file) > 0:
            self.db.append_metadata_from_csv(csv_file)

        # ceck if a file exists and if not asks the user to download it. gets used to check if db are all present
        # TODO: also add checksum check to make sure the index is completely downloaded, if not remove file and download again

    def check_file_exists(self, filepath, url):
        if os.path.exists(f"{ROOT}/src/resources/dec22.tar"):
            if not os.path.exists(f"{ROOT}/src/resources/dec22.1.cf"):
                response = messagebox.askquestion("Centrifuge index not decompressed",
                                                  "Index is compressed. Do you want to decompress it?")
                if response == "yes":
                    try:
                        self.unzip_tar(f"{ROOT}/src/resources/dec22.tar", f"{ROOT}/src/resources/")
                    except FileNotFoundError as e:
                        print(f"Requested file not found")
            if not os.path.exists(f"{ROOT}/src/resources/dec22.1.cf") and os.path.exists(
                    f"{ROOT}/src/resources/dec22.1.cf.gz"):
                try:
                    self.unzip_gz(f"{ROOT}/src/resources/dec22.1.cf.gz")
                    self.unzip_gz(f"{ROOT}/src/resources/dec22.2.cf.gz")
                    self.unzip_gz(f"{ROOT}/src/resources/dec22.3.cf.gz")
                    self.unzip_gz(f"{ROOT}/src/resources/dec22.4.cf.gz")
                except FileNotFoundError as e:
                    print(f"Requested files not found.")





        else:
            response = messagebox.askquestion("Centrifuge index not found",
                                              "Centrifuge index not found. Do you want to download it?"
                                              " Might take some time, the tool is unusable while download.")
            if response == "yes":
                with urllib.request.urlopen(url) as response:
                    # get file size from content-length header
                    file_size = int(response.info().get("Content-Length"))
                    # create progress bar widget
                    progress = ttk.Progressbar(self.root, orient="horizontal", length=250, mode="determinate")
                    progress.pack()
                    progress["maximum"] = file_size
                    progress["value"] = 0

                    def update_progress(count, block_size, total_size):
                        progress["value"] = count * block_size
                        self.root.update_idletasks()

                    # download file and update progress bar
                    urllib.request.urlretrieve(url, filepath, reporthook=update_progress)
                    progress.destroy()
                messagebox.showinfo("Download complete", "Download complete. Unpacking files...")

    def unzip_tar(self, file, out_folder):
        my_tar = tarfile.open(file, mode='r')
        my_tar.extractall(out_folder)  # specify which folder to extract to
        my_tar.close()

    def unzip_gz(self, file):
        with gzip.open(file, 'rb') as f:
            file_content = f.read()
            gzip.decompress(file_content)

    # choose folder containing sequencing data
    # TODO: check if there is white space in path that causes problem
    @require_project
    # @require_centrifuge
    def analyze_fastq_in_folder(self):
        # check if centrifuge index exists, if not download it using check_file_exists method
        centrifuge_index = "dec22"
        download_thread = Thread(target=self.check_file_exists(f"{ROOT}/src/resources/{centrifuge_index}.tar",
                                                               "https://software-ab.cs.uni-tuebingen.de/download/MMonitor/dec22.tar"))
        download_thread.start()
        self.unzip_tar(f"{ROOT}/src/resources/dec22.tar", f"{ROOT}/src/resources/")
        self.unzip_gz(f"{ROOT}/src/resources/dec22.1.cf.gz")
        self.unzip_gz(f"{ROOT}/src/resources/dec22.2.cf.gz")
        self.unzip_gz(f"{ROOT}/src/resources/dec22.3.cf.gz")
        self.unzip_gz(f"{ROOT}/src/resources/dec22.4.cf.gz")

        folder = filedialog.askdirectory(
            initialdir='/',
            title="Choose directory containing sequencing data"
        )
        files = self.cent.get_files_from_folder(folder)

        sample_name = simpledialog.askstring(
            "Input sample name",
            "What should the sample be called?",
            parent=self.root
        )

        # sample_date = calendar_picker()
        sample_date = date.today()
        self.cent.run_centrifuge(files, sample_name)
        self.cent.make_kraken_report()

    def taxonomy_nanopore_16s(self):
        folder = filedialog.askdirectory(
            initialdir='/',
            title="Choose directory containing sequencing data"
        )
        files = self.emu.get_files_from_folder(folder)

    def checkbox_popup(self):

        # open checkbox to ask what the user wants to run (in case of rerunning)
        top = tk.Toplevel(self.root)
        top.geometry("420x245")
        top.title("Select analysis steps to perform.")
        frame_taxonomy = tk.LabelFrame(top, padx=10, pady=2, text="Taxonomic analysis")
        frame_functional = tk.LabelFrame(top, padx=10, pady=2, text="Functional analysis")
        frame_taxonomy.pack(pady=5, padx=10)
        frame_functional.pack(pady=5, padx=10)
        button_width = 100

        # taxonomy checkboxes
        c6 = ttk.Checkbutton(frame_taxonomy, text='Quick taxonomy nanopore', variable=self.taxonomy_nanopore_wgs,
                             width=button_width).pack()
        c8 = ttk.Checkbutton(frame_taxonomy, text='Quick taxonomy 16s nanopore',
                             variable=self.taxonomy_nanopore_16s_bool,
                             width=button_width).pack()

        # functional analysis checkboxes
        c1 = ttk.Checkbutton(frame_functional, text='Assembly', variable=self.assembly, width=button_width).pack()
        c2 = ttk.Checkbutton(frame_functional, text='Correction', variable=self.correction, width=button_width).pack()
        c3 = ttk.Checkbutton(frame_functional, text='Binning', variable=self.binning, width=button_width).pack()
        c4 = ttk.Checkbutton(frame_functional, text='Annotation', variable=self.annotation, width=button_width).pack()
        c5 = ttk.Checkbutton(frame_functional, text='KEGG', variable=self.kegg, width=button_width).pack()
        c7 = tk.Button(top, text="Continue", command=lambda: [self.run_analysis_pipeline(), top.destroy()]).pack()

    def ask_sample_name(self):
        sample_name = simpledialog.askstring(
            "Input sample name",
            "What should the sample be called?",
            parent=self.root
        )
        return sample_name

    # @require_project
    def run_analysis_pipeline(self):
        if self.assembly.get() or self.correction.get():
            seq_file = filedialog.askopenfilename(title="Please select a sequencing file")
        if self.assembly.get() or self.correction.get() or self.annotation.get() or self.binning.get():
            sample_name = self.ask_sample_name()
            self.func.check_software_avail()
        if self.taxonomy_nanopore_wgs.get():
            self.analyze_fastq_in_folder()
        if self.taxonomy_nanopore_16s_bool.get():
            self.taxonomy_nanopore_16()
        if self.assembly.get():
            self.func.run_flye(seq_file, sample_name)
        if self.correction.get():
            self.func.run_racon(seq_file, sample_name)
            # self.func.run_medaka(seq_file, sample_name) TODO: FIX MEDAKA
        if self.binning.get():
            self.func.run_binning(sample_name)
        if self.annotation.get():
            bins_path = f"{ROOT}/src/resources/{sample_name}/bins/"
            self.func.run_prokka(bins_path)
        # if only kegg analysis is selected then the user needs to chose the path to the annotations
        if self.kegg.get() and not self.assembly.get() and not self.correction.get() and not self.binning.get() and not self.annotation.get():
            # sample_name = self.ask_sample_name()
            pipeline_out = filedialog.askdirectory(
                title="Please select the path to the prokka output (folder with tsv files with annotations).")
            pipeline_out = f"{pipeline_out}/"
            # pipeline_out = f"{ROOT}/src/resources/pipeline_out/{sample_name}/"
            self.kegg_thread1 = Thread(target=self.func.create_keggcharter_input(pipeline_out))
            self.kegg_thread1.start()
            self.kegg_thread2 = Thread(self.func.run_keggcharter(pipeline_out, f"{pipeline_out}keggcharter.tsv"))
            self.kegg_thread2.start()

            # if kegg and annotation is chosen then the user only needs to select the sample name, then the tsv files from the results
            # of the annotations will be used as input for creating keggcharter input and creating kegg maps
        if self.kegg.get() and self.annotation.get():
            sample_name = self.ask_sample_name()
            # pipeline_out = filedialog.askdirectory(title="Please select the path to the prokka output (folder with tsv files with annotations).")
            pipeline_out = f"{ROOT}/src/resources/pipeline_out/{sample_name}/"
            self.kegg_thread1 = Thread(target=self.func.create_keggcharter_input(pipeline_out))
            self.kegg_thread1.start()
            self.kegg_thread2 = Thread(self.func.run_keggcharter(pipeline_out, f"{pipeline_out}/keggcharter.tsv"))
            self.kegg_thread2.start()

    @require_project
    def start_monitoring(self):
        self.dashapp = Index(self.db)
        self.monitor_thread = Thread(target=self.dashapp.run_server, args=(False,))
        self.monitor_thread.start()

        sleep(1)
        open_new('http://localhost:8050')

    def start_app(self):
        self.root.mainloop()

    def stop_app(self):
        if self.monitor_thread is not None and self.monitor_thread.is_alive():
            post('http://localhost:8050/shutdown')
            self.monitor_thread.join()
        self.root.destroy()
