from threading import Thread
from time import sleep
from webbrowser import open_new
import tkinter as tk
from tkinter import filedialog
from tkinter import simpledialog
from requests import post

from mmonitor.dashapp.index import Index
from mmonitor.database.mmonitor_db import MMonitorDBInterface
from mmonitor.userside.centrifuge import CentrifugeRunner

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


def require_centrifuge(func):
    """Decorator that ensures that a centrifuge index was selected by the user."""
    def func_wrapper(*args):
        obj: GUI = args[0]
        if obj.centrifuge_index is not None and len(obj.centrifuge_index) > 0:
            return func(*args)
        else:
            obj.open_popup("Please first select a centrifuge index before analyzing files.", "Centrifuge error")
    return func_wrapper


class GUI:

    def __init__(self):
        # declare data base class variable, to be chosen by user with choose_project()
        self.db: MMonitorDBInterface = None
        self.db_path = None
        self.centrifuge_index = None
        self.cent = CentrifugeRunner()
        self.dashapp = None
        self.monitor_thread = None
        self.root = tk.Tk()
        self.init_layout()

    def init_layout(self):

        self.root.geometry("250x250")
        self.root.title("MMonitor v0.1.0. alpha")
        self.root.resizable(width=False, height=False)

        # create buttons
        tk.Button(self.root, text="Create Project", command=self.create_project,
                  padx=10, pady=5, fg='white', bg='#254D25').pack()
        tk.Button(self.root, text="Choose Project", command=self.choose_project,
                  padx=10, pady=5, fg='white', bg='#254D25').pack()
        tk.Button(self.root, text="Choose centrifuge index", command=self.choose_index,
                  padx=10, pady=5, fg='white', bg='#254D25').pack()
        tk.Button(self.root, text="Analyze fastq in folder", command=self.analyze_fastq_in_folder,
                  padx=10, pady=5, fg='white', bg='#254D25').pack()
        tk.Button(self.root, text="Add metadata from CSV", command=self.append_metadata,
                  padx=10, pady=5, fg='white', bg='#254D25').pack()
        tk.Button(self.root, text="Start monitoring", command=self.start_monitoring,
                  padx=10, pady=5, fg='white', bg='#254D25').pack()
        tk.Button(self.root, text="Quit", command=self.stop_app).pack()

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

    def choose_index(self):
        self.centrifuge_index = filedialog.askopenfilename(
            initialdir='projects/',
            title="Choose project data base to use",
            filetypes=(("sqlite", "*.sqlite3"), ("all files", "*.*"))
        )

    @require_project
    def append_metadata(self):
        csv_file = filedialog.askopenfilename(
            initialdir='projects/',
            title="Choose csv file containing metadata to append",
            filetypes=(("csv", "*.csv"), ("all files", "*.*"))
        )
        if csv_file is not None and len(csv_file) > 0:
            self.db.append_metadata_from_csv(csv_file)

    # choose folder containing sequencing data
    # TODO: check if there is white space in path that causes problem
    @require_project
    @require_centrifuge
    def analyze_fastq_in_folder(self):
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
        self.cent.run_centrifuge(files, self.centrifuge_index, sample_name)

        self.cent.make_kraken_report(self.centrifuge_index)
        self.db.update_table_with_kraken_out(f"classifier_out/{sample_name}_kraken_out", "S", sample_name, "project")

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
