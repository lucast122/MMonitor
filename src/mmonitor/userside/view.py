import tkinter as tk
from tkinter import filedialog, Text
import os
from mmonitor.database.mmonitor_db import MMonitorDBInterface
from mmonitor.userside.centrifuge import CentrifugeRunner
from tkinter import simpledialog
from mmonitor.database.mmonitor_db import MMonitorDBInterface
from mmonitor.dashapp.index import DashBaseApp
from mmonitor import __main__
import threading
from tkinter import ttk

import sys

from threading import Timer

"""
This file represents the basic gui for the desktop app. It is the entry point for the program and the only way 
for the user to create projects, select files and run MMonitor's computational engine (centrifuge at this moment)
"""


db = None # declare data base class variable, to be chosen by user with choose_project()
db_path = None
centrifuge_index = None
cent = CentrifugeRunner()
cent.check_centrifuge()


def create_project():
    global db
    global db_path
    filename = filedialog.asksaveasfilename(initialdir='projects/', title ="Choose place to safe the project data")
    filename +=".sqlite3"
    db_path = filename
    print(db_path)
    db = MMonitorDBInterface(filename)
    db.create_db(filename)

def choose_project():
    global db_path
    global db
    db_path = filedialog.askopenfilename(initialdir='projects/', title ="Choose project data base to use",
                                          filetypes = (("sqlite", "*.sqlite3"), ("all files", "*.*")))
    print(db_path)
    db = MMonitorDBInterface(db_path)
    print(db)



# choose folder containing sequencing data TODO: check if there is white space in path that causes problem
def analyze_fastq_in_folder():
    if centrifuge_index is None:
        open_popup("Please first select a centrifuge index before analyzing files.",
                   "Centrifuge error")
        return
    global db
    dir = filedialog.askdirectory(initialdir='/', title ="Choose directory containing sequenicng data")
    files = cent.get_files_from_folder(dir)
    print(files)

    sample_name = simpledialog.askstrixng("Input sample name", "What should the sample be called?",
                                          parent=root)
    cent.run_centrifuge(files, centrifuge_index, sample_name)


    
    cent.make_kraken_report(centrifuge_index)
    db.update_table_with_kraken_out(f"classifier_out/{sample_name}_kraken_out", "S",sample_name,"project")

def start_monitoring():
    # global db_path
    # __main__.main(db_path)
    if db_path is None:
        open_popup("Please first create or choose a project data base.","No data base chosen")
        return
    else:
        threading.Thread(target=__main__.main,args=(db_path,)).start()


def open_popup(text,title):
    top = tk.Toplevel(root)
    top.geometry("700x200")
    top.title(title)
    tk.Label(top, text=text, font=('Mistral 18 bold')).place(x=150, y=80)
    ok_button = tk.Button(top, text="Okay", command=top.destroy)
    ok_button.pack()

def choose_index():
    global centrifuge_index
    centrifuge_index = filedialog.askopenfilename(initialdir='projects/', title ="Choose project data base to use",
                                          filetypes = (("sqlite", "*.sqlite3"), ("all files", "*.*")))




root = tk.Tk()
root.geometry("250x250")
root.title("MMonitor v0.1.0. alpha")
root.resizable(width=False,height=False)
# canvas = tk.Canvas(root, height= 200, width= 200, bg= '#254D25').pack()



# create buttons
create_project = tk.Button(root, text= "Create Project", padx=10, pady=5, fg ='white', bg= '#254D25', command=create_project)
create_project.pack()

choose_project= tk.Button(root, text= "Choose Project", padx=10, pady=5, fg ='white', bg= '#254D25', command=choose_project)
choose_project.pack()

# button that lets user choose folder containing .fasta or .fastq files to process

choose_index= tk.Button(root, text= "Choose centrifuge index", padx=10, pady=5, fg ='white', bg= '#254D25', command = choose_index)
choose_index.pack()

analyze_fastq = tk.Button(root, text= "Analyze fastq in folder", padx=10, pady=5, fg ='white', bg= '#254D25', command = analyze_fastq_in_folder)
analyze_fastq.pack()

# load_metadata= tk.Button(root, text= "Load metadata", padx=10, pady=5, fg ='white', bg= '#254D25', command = load_metadata)
# choose_index.pack()


start_monitoring= tk.Button(root, text= "Start monitoring", padx=10, pady=5, fg ='white', bg= '#254D25', command = start_monitoring)
start_monitoring.pack()

quit_button = tk.Button(root, text="Quit", command=root.destroy).pack()

# log = tk.Text(root, bg= '#000000', width = 50, height =10).pack()



root.mainloop()