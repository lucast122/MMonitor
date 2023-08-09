# from tkcalendar import Calendar
import gzip
import os
import tarfile
import urllib.request
from threading import Thread
from time import sleep
from tkinter import *
from tkinter import simpledialog
from webbrowser import open_new

from future.moves.tkinter import filedialog
from requests import post
from tkcalendar import Calendar

from build import ROOT
from mmonitor.dashapp.index import Index
from mmonitor.database.mmonitor_db import MMonitorDBInterface
from mmonitor.database.mmonitor_db_mysql_new import MMonitorDBInterfaceMySQL
from mmonitor.userside.DBConfigForm import DataBaseConfigForm
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


import tkinter as tk
from tkinter import messagebox, ttk



class GUI:

    def __init__(self):
        self.db_mysql = MMonitorDBInterfaceMySQL(f"{ROOT}/src/resources/db_config.json")
        # self.db_mysql.create_db()

        # declare data base class variable, to be chosen by user with choose_project()
        self.db: MMonitorDBInterface = None
        # self.db_mysql = None
        self.db_path = None
        self.centrifuge_runner = CentrifugeRunner()
        self.emu_runner = EmuRunner()
        self.functional_analysis_runner = FunctionalAnalysisRunner()
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
        self.sample_date = None

    def init_layout(self):
        self.root.geometry("350x530")
        self.root.title("MMonitor v1.0 beta")
        self.root.minsize(340, 530)

        # Style and theme
        style = ttk.Style()
        style.theme_use("clam")  # Switch to the 'clam' theme for better styling flexibility

        style.configure('TButton',
                        font=("Helvetica", 15),
                        foreground='black',
                        bordercolor="black",
                        background='#FCF6F5',

                        padding=5,
                        borderwidth=1,
                        roundedrelief=True)

        style.map('TButton',
                  foreground=[('pressed', 'white'), ('active', 'black')],
                  background=[('pressed', '!disabled', '#B22222'), ('active', '#B0E0E6')]  # Light blue when active
                  )

        # Placeholder icon
        placeholder_icon = tk.PhotoImage(width=16, height=16)
        placeholder_icon.put(("gray",), to=(0, 0, 15, 15))

        # Header with app title
        header_label = ttk.Label(self.root, text="MMonitor v1.0 beta", font=("Helvetica", 20))
        header_label.pack(pady=10)

        # Categories and buttons

        categories = [
            ("Local", [
                ("Create Local DB", self.create_project),
                ("Choose Local DB", self.choose_project),
                ("Start offline monitoring", self.start_monitoring)
            ]),
            ("Webserver", [
                ("User authentication", self.open_db_config_form)
            ]),
            ("Add Data", [
                ("Add metadata from CSV", self.append_metadata),
                ("Run analysis pipeline", self.checkbox_popup)
            ])
        ]

        # Tooltips for the categories
        category_tooltips = {
            "Local": "Use these function to store everything in a local Database. \n Then after adding data hit 'Start offline monitoring'. ",
            "Webserver": "Click 'User authentication' to provide your username and password for the webserver. \n After authentication"
                         " all data you add will be uploaded to the webserver as well. \n Provide same username and password that you used"
                         " for registration at the MMonitor webpage.",
            "Add Data": "Use this to add data to the local database and the webserver. \n Data can only be added if either"
                        " local database was chosen first or User Authentication was performed. \n If you did both data will be added to local DB and webserver."

        }
        # Calculate the maximum button width based on text length
        button_texts = [btn[0] for cat in categories for btn in cat[1]]
        button_texts.append("Quit")  # Adding Quit button text
        max_text_length = max(map(len, button_texts))
        btn_width = max_text_length + 5  # Adding an offset to account for padding and icon

        style.configure('TLabel',
                        background='#990011',  # red color
                        foreground='white',  # text color
                        font=("Helvetica", 18),
                        width=btn_width - 5,  # set the width
                        padding=5,
                        anchor='Center')

        for category, btns in categories:
            cat_label = ttk.Label(self.root, text=category, font=("Helvetica", 22), anchor="center")
            cat_label.pack(pady=10)

            # Attach tooltips if available
            if category in category_tooltips:
                self.create_tooltip(cat_label, category_tooltips[category])

            for text, cmd in btns:
                btn = ttk.Button(self.root, text=text, command=cmd, image=placeholder_icon, compound="left",
                                 width=btn_width)
                btn.image = placeholder_icon  # Keep a reference
                btn.pack(pady=2)

        # Quit button
        quit_btn = ttk.Button(self.root, text="Quit", command=self.stop_app, image=placeholder_icon, compound="left",
                              width=btn_width)
        quit_btn.image = placeholder_icon
        quit_btn.pack(pady=20)
        # create_tooltip(local_label, "This is the tooltip text for the Local category.")
        # create_tooltip(webserver_label, "This is the tooltip text for the Webserver category.")

    def create_tooltip(self, widget, text):
        tooltip = ToolTip(widget, text)
        widget.bind("<Enter>", tooltip.show_tip)
        widget.bind("<Leave>", tooltip.hide_tip)

    def ask_create_subproject(self):
        # Create the root window but don't show it
        top = tk.Toplevel(self.root)
        top.geometry("700x300")

        # Ask the user if they want to create a subproject
        answer = messagebox.askyesno("Create Subproject", "Do you want to create a subproject?")

        # If the user selects 'Yes'
        if answer:
            subproject_name = simpledialog.askstring("Input", "What is the name of your subproject?")
            return subproject_name
        else:
            return None

    def open_calendar(self):
        calendar_window = tk.Toplevel()
        calendar_window.title("Choose a Date")

        # Use a StringVar to hold our date
        selected_date_var = tk.StringVar()

        calendar = Calendar(calendar_window, selectmode="day")
        calendar.pack(pady=20)

        def on_date_select():
            selected_date_var.set(calendar.get_date())
            calendar_window.destroy()
            calendar_window.quit()

        select_button = tk.Button(calendar_window, text="Select Date", command=on_date_select)
        select_button.pack(pady=20)

        calendar_window.mainloop()

        return selected_date_var.get()

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

    # @require_project
    def append_metadata(self):
        csv_file = filedialog.askopenfilename(
            initialdir='projects/',
            title="Choose csv file containing metadata to append",
            filetypes=(("csv", "*.csv"), ("all files", "*.*"))
        )
        if csv_file is not None and len(csv_file) > 0:
            self.db_mysql.append_metadata_from_csv(csv_file)

        # ceck if a file exists and if not asks the user to download it. gets used to check if db are all present
        # TODO: also add checksum check to make sure the index is completely downloaded, if not remove file and download again
    def check_emu_db_exists(self):
        if not os.path.exists(f"{ROOT}/src/resources/emu_db/emu.tar"):
            response = messagebox.askquestion("Emu database not found.",
                                              "Emu DB not found. Do you want to download it?")
            if response == "yes":
                try:
                    # download emu db from web if it doesn't exist
                    self.download_file_from_web(f"{ROOT}/src/resources/emu_db/emu.tar","https://software-ab.cs.uni-tuebingen.de/download/MMonitor/emu.tar")
                    self.unzip_tar(f"{ROOT}/src/resources/emu_db/emu.tar",f"{ROOT}/src/resources/emu_db/")

                except FileNotFoundError as e:
                    self.open_popup("Could not download the EMU DB. Please contact the MMonitor developer for help", "Could not find emu db")


                
    def download_file_from_web(self,filepath,url):
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
                self.download_file_from_web(filepath,url)

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
    def taxonomy_nanopore_wgs(self):
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
        files = self.centrifuge_runner.get_files_from_folder(folder)

        sample_name = simpledialog.askstring(
            "Input sample name",
            "What should the sample be called?",
            parent=self.root
        )

        print("Before opening the calendar...")
        sample_date = self.open_calendar()
        print(f"Selected date: {sample_date}")
        print("After the calendar is closed...")

        self.centrifuge_runner.run_centrifuge(files, sample_name)
        self.centrifuge_runner.make_kraken_report()

        self.db.update_table_with_kraken_out(f"{ROOT}/src/resources/pipeline_out/{sample_name}_kraken_out", "species",
                                             sample_name, "project", sample_date)

    def taxonomy_nanopore_16s(self):


        self.check_emu_db_exists()
        folder = filedialog.askdirectory(
            initialdir='/',
            title="Choose directory containing sequencing data"
        )
        files = self.emu_runner.get_files_from_folder(folder)

        sample_name = self.ask_sample_name()

        project_name = simpledialog.askstring(
            "Input project name",
            "What should the project be called?",
            parent=self.root
        )

        subproject_name = self.ask_create_subproject()
        print(sample_name)
        print("Before opening the calendar...")
        sample_date = self.open_calendar()
        print(f"Selected date: {sample_date}")
        print("After the calendar is closed...")

        self.emu_runner.run_emu(files, sample_name)
        emu_out_path = f"{ROOT}/src/resources/pipeline_out/{sample_name}/"
        # emu_out_path = f"{ROOT}/src/resources/pipeline_out/subset/"
        # self.db.update_table_with_emu_out(emu_out_path,"species",sample_name,"project",self.sample_date)
        # project_name="R1"
        self.db_mysql.update_django_with_emu_out(emu_out_path, "species", sample_name, project_name, sample_date,
                                                 subproject_name)



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
            self.functional_analysis_runner.check_software_avail()
        if self.taxonomy_nanopore_wgs.get():
            self.taxonomy_nanopore_wgs()

        if self.taxonomy_nanopore_16s_bool.get():
            self.taxonomy_nanopore_16s()
            self.display_popup_message("Analysis complete. You can start monitoring now.")
        if self.assembly.get():
            self.functional_analysis_runner.run_flye(seq_file, sample_name)
        if self.correction.get():
            self.functional_analysis_runner.run_racon(seq_file, sample_name)
            # self.func.run_medaka(seq_file, sample_name) TODO: FIX MEDAKA
        if self.binning.get():
            self.functional_analysis_runner.run_binning(sample_name)
        if self.annotation.get():
            bins_path = f"{ROOT}/src/resources/{sample_name}/bins/"
            self.functional_analysis_runner.run_prokka(bins_path)
        # if only kegg analysis is selected then the user needs to chose the path to the annotations
        if self.kegg.get() and not self.assembly.get() and not self.correction.get() and not self.binning.get() and not self.annotation.get():
            # sample_name = self.ask_sample_name()
            pipeline_out = filedialog.askdirectory(
                title="Please select the path to the prokka output (folder with tsv files with annotations).")
            pipeline_out = f"{pipeline_out}/"
            # pipeline_out = f"{ROOT}/src/resources/pipeline_out/{sample_name}/"
            self.kegg_thread1 = Thread(target=self.functional_analysis_runner.create_keggcharter_input(pipeline_out))
            self.kegg_thread1.start()
            self.kegg_thread2 = Thread(self.functional_analysis_runner.run_keggcharter(pipeline_out, f"{pipeline_out}keggcharter.tsv"))
            self.kegg_thread2.start()
            self.display_popup_message("Analysis complete. You can start monitoring now.")

            # if kegg and annotation is chosen then the user only needs to select the sample name, then the tsv files from the results
            # of the annotations will be used as input for creating keggcharter input and creating kegg maps
        if self.kegg.get() and self.annotation.get():
            sample_name = self.ask_sample_name()
            # pipeline_out = filedialog.askdirectory(title="Please select the path to the prokka output (folder with tsv files with annotations).")
            pipeline_out = f"{ROOT}/src/resources/pipeline_out/{sample_name}/"
            self.kegg_thread1 = Thread(target=self.functional_analysis_runner.create_keggcharter_input(pipeline_out))
            self.kegg_thread1.start()
            self.kegg_thread2 = Thread(self.functional_analysis_runner.run_keggcharter(pipeline_out, f"{pipeline_out}/keggcharter.tsv"))
            self.kegg_thread2.start()

    def display_popup_message(self, message):
        root = tk.Tk()
        root.withdraw()
        messagebox.showinfo("Process Completed", message)
        root.destroy()

    @require_project
    def start_monitoring(self):
        try:
            self.dashapp = Index(self.db)
            self.monitor_thread = Thread(target=self.dashapp.run_server, args=(False,))
            self.monitor_thread.start()
        except IndexError:
            self.display_popup_message(
                "No data found in database. Please first run analysis pipeline to fill DB with data.")
            return

        sleep(1)
        open_new('http://localhost:8050')

    def start_app(self):
        self.root.mainloop()

    def stop_app(self):
        if self.monitor_thread is not None and self.monitor_thread.is_alive():
            post('http://localhost:8050/shutdown')
            self.monitor_thread.join()
        self.root.destroy()

    def open_db_config_form(self):
        db_config_form = DataBaseConfigForm(self.root)
        print(db_config_form.last_config)


class ToolTip:
    def __init__(self, widget, tip_text):
        self.widget = widget
        self.tip_text = tip_text
        self.tip_window = None

    def show_tip(self, event=None):
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25

        self.tip_window = tk.Toplevel(self.widget)
        self.tip_window.wm_overrideredirect(True)
        self.tip_window.wm_geometry(f"+{x}+{y}")

        label = tk.Label(self.tip_window, text=self.tip_text, foreground="black", background="#ffffe0", relief="solid",
                         borderwidth=1,
                         font=("Helvetica", "16", "normal"))
        label.pack(ipadx=1)

    def hide_tip(self, event=None):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None
