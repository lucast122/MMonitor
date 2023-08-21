import os
import tkinter as tk
from tkinter import ttk, filedialog

from tkcalendar import Calendar


class InputWindow:
    def __init__(self, parent, emu_runner):
        self.selected_date = None
        self.sample_name = None
        self.project_name = None
        self.subproject_name = None
        self.parent = parent
        self.emu_runner = emu_runner
        self.file_paths = []  # Store full paths of selected files

        # Toplevel window
        self.top = tk.Toplevel(parent)
        self.top.title("Sample Data Input")
        self.top.geometry("500x920")
        self.top.minsize(500, 920)

        padding_y = 5
        label_width = 30
        ttk.Label(self.top, text="Sample Name", font='Helvetica 10 bold').pack(pady=padding_y)
        self.sample_name_entry = ttk.Entry(self.top, width=label_width)
        self.sample_name_entry.pack(pady=padding_y)

        ttk.Label(self.top, text="Project Name", font='Helvetica 10 bold').pack(pady=padding_y)
        self.project_name_entry = ttk.Entry(self.top, width=label_width)
        self.project_name_entry.pack(pady=padding_y)
        # Trace change in project_name_entry to mirror its content into subproject_name_entry
        self.project_name_entry.bind("<KeyRelease>", self.mirror_project_name)

        ttk.Label(self.top, text="Subproject Name", font='Helvetica 10 bold').pack(pady=padding_y)
        self.subproject_name_entry = ttk.Entry(self.top, width=label_width)
        self.subproject_name_entry.pack(pady=padding_y)

        ttk.Label(self.top, text="Sample Date", font='Helvetica 10 bold').pack(pady=padding_y)
        self.date_btn = ttk.Button(self.top, text="Select Date", command=self.open_calendar)
        self.date_btn.pack(pady=padding_y)

        ttk.Label(self.top, text="Files", font='Helvetica 10 bold').pack(pady=padding_y)
        self.file_display = tk.Text(self.top, width=500, height=30, wrap="word",
                                    state=tk.DISABLED)  # Adjusted size and made read-only
        self.file_display.pack(pady=padding_y)

        ttk.Button(self.top, text="Add Sequencing Data", command=self.add_data).pack(pady=padding_y)
        ttk.Button(self.top, text="Submit", command=self.submit).pack(pady=padding_y)
        ttk.Button(self.top, text="Quit", command=self.quit).pack(pady=padding_y)

    def mirror_project_name(self, event):
        # Get the current value of project name entry and set it to subproject name entry
        project_name = self.project_name_entry.get()
        self.subproject_name_entry.delete(0, tk.END)
        self.subproject_name_entry.insert(0, project_name)

    def open_calendar(self):
        def on_close():
            selected_date = cal.selection_get()
            self.date_btn.config(text=selected_date.strftime("%Y-%m-%d"))
            self.selected_date = selected_date
            date_win.destroy()

        date_win = tk.Toplevel(self.top)
        date_win.title("Select a Date")

        cal = Calendar(date_win, selectmode='day')
        cal.pack(pady=20, padx=20)

        ttk.Button(date_win, text="OK", command=on_close).pack(pady=20)

    def add_data(self):
        folder = filedialog.askdirectory(initialdir='/', title="Choose directory containing sequencing data")
        files = [f for f in self.emu_runner.get_files_from_folder(folder) if
                 f.endswith(("fastq", "fasta", "fq", "fa", 'fastq.gz', "fasta.gz", "fa.gz", "fq.gz"))]

        self.file_display.config(state=tk.NORMAL)  # Temporarily set the Text widget to normal mode to insert data
        for file in files:
            self.file_paths.append(file)  # Store full path
            self.file_display.insert(tk.END, os.path.basename(file) + "\n")  # Only display the file name
        self.file_display.config(state=tk.DISABLED)  # Set the Text widget back to read-only mode

    def submit(self):
        self.sample_name = self.sample_name_entry.get()
        self.project_name = self.project_name_entry.get()
        self.subproject_name = self.subproject_name_entry.get()

        self.top.destroy()

    def quit(self):
        self.top.destroy()
