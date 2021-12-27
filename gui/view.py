import tkinter as tk
from tkinter import filedialog, simpledialog

from gui import server
from gui.centrifuge import CentrifugeRunner
from gui.mmonitor_db import MMonitorDBInterface


class View:
    """
    This class represents the basic gui for the desktop app. It is the entry point for the program and the only way
    for the user to create projects, select files and run MMonitor's computational engine (centrifuge at this moment)
    """

    def __init__(self):
        self.root = self.create_gui()
        self.centrifuge_index = None
        self.db_path = None
        self.db = None
        self.cent = CentrifugeRunner()
        self.cent.check_centrifuge()

    def create_project(self):
        filename = filedialog.asksaveasfilename(initialdir='projects/', title="Choose place to safe the project data")
        filename += ".sqlite3"
        self.db_path = filename
        self.db = MMonitorDBInterface(filename)
        self.db.create_db(filename)

    def choose_project(self):
        self.db_path = filedialog.askopenfilename(initialdir='projects/', title="Choose project data base to use",
                                                  filetypes=(("sqlite", "*.sqlite3"), ("all files", "*.*")))
        self.db = MMonitorDBInterface(self.db_path)

    def analyze_fastq_in_folder(self):
        """
        Choose folder containing sequencing data
        TODO: check if there is white space in path that causes problem
        """
        if self.centrifuge_index is None:
            self.open_popup("Please first select a centrifuge index before analyzing files.", "Centrifuge error")
            return
        user_dir = filedialog.askdirectory(initialdir='/', title="Choose directory containing sequencing data")
        files = self.cent.get_files_from_folder(user_dir)

        sample_name = simpledialog.askstring("Input sample name", "What should the sample be called?", parent=self.root)
        self.cent.run_centrifuge(files, self.centrifuge_index, sample_name)

        self.cent.make_kraken_report(self.centrifuge_index)
        self.db.update_table_with_kraken_out(f"classifier_out/{sample_name}_kraken_out", "S", sample_name, "project")

    def open_popup(self, text, title):
        top = tk.Toplevel(self.root)
        top.geometry("700x200")
        top.title(title)
        tk.Label(top, text=text, font='Mistral 18 bold').place(x=150, y=80)
        ok_button = tk.Button(top, text="Okay", command=top.destroy)
        ok_button.pack()

    def choose_index(self):
        self.centrifuge_index = filedialog.askopenfilename(
            initialdir='projects/',
            title="Choose project data base to use",
            filetypes=(("sqlite", "*.sqlite3"), ("all files", "*.*"))
        )

    def create_gui(self):
        root = tk.Tk()
        root.geometry("250x250")
        root.title("MMonitor v0.1.0. alpha")
        root.resizable(width=False, height=False)

        # create buttons
        create_project = tk.Button(root, text="Create Project", padx=10, pady=5, fg='white', bg='#254D25',
                                   command=self.create_project)
        create_project.pack()

        choose_project = tk.Button(root, text="Choose Project", padx=10, pady=5, fg='white', bg='#254D25',
                                   command=self.choose_project)
        choose_project.pack()

        choose_index = tk.Button(root, text="Choose centrifuge index", padx=10, pady=5, fg='white', bg='#254D25',
                                 command=self.choose_index)
        choose_index.pack()

        analyze_fastq = tk.Button(root, text="Analyze fastq in folder", padx=10, pady=5, fg='white', bg='#254D25',
                                  command=self.analyze_fastq_in_folder)
        analyze_fastq.pack()

        start_monitoring = tk.Button(root, text="Start monitoring", padx=10, pady=5, fg='white', bg='#254D25',
                                     command=server.start)
        start_monitoring.pack()

        tk.Button(root, text="Quit", command=root.destroy).pack()

        return root

    def run(self):
        self.root.mainloop()
