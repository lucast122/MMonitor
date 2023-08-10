import gzip
import os
import sys
import tarfile
import urllib.request
from threading import Thread
from time import sleep
from tkinter import *
from tkinter import simpledialog
from webbrowser import open_new

from PIL import Image, ImageTk
from future.moves.tkinter import filedialog
from requests import post
from tkcalendar import Calendar

from build_mmonitor_pyinstaller import ROOT, IMAGES_PATH
from mmonitor.dashapp.index import Index
from mmonitor.database.mmonitor_db import MMonitorDBInterface
from mmonitor.database.mmonitor_db_mysql_new import MMonitorDBInterfaceMySQL
from mmonitor.userside.DBConfigForm import DataBaseConfigForm
from mmonitor.userside.InputWindow import InputWindow
from mmonitor.userside.PipelinePopup import PipelinePopup
from mmonitor.userside.centrifuge import CentrifugeRunner
from mmonitor.userside.emu import EmuRunner
from mmonitor.userside.functional_analysis import FunctionalAnalysisRunner

# Some basic variables that might need frequent change
VERSION = "v1.0 beta"
MAIN_WINDOW_X: int = 350
MAIN_WINDOW_Y: int = 630

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

        sys.path.append('/Users/timolucas/PycharmProjects/MMonitor/desktop/')
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
        mmonitor_logo = tk.PhotoImage(file=f"{IMAGES_PATH}/mmonitor_logo.png")
        self.root.iconphoto(True, mmonitor_logo)
        self.init_layout()
        self.taxonomy_nanopore_wgs_bool = tk.BooleanVar()
        self.taxonomy_nanopore_16s_bool = tk.BooleanVar()
        self.assembly = tk.BooleanVar()
        self.correction = tk.BooleanVar()
        self.binning = tk.BooleanVar()
        self.annotation = tk.BooleanVar()
        self.kegg = tk.BooleanVar()
        self.sample_date = None

    def init_layout(self):

        def resize_icon_to_xpx(image_path, x):
            """Utility function to resize the image to 25px while maintaining aspect ratio."""
            img = Image.open(image_path)
            base_width = x
            w_percent = base_width / float(img.width)
            h_size = int(float(img.height) * float(w_percent))
            img = img.resize((base_width, h_size), Image.ANTIALIAS)
            return ImageTk.PhotoImage(img)

        self.root.geometry(f"{MAIN_WINDOW_X}x{MAIN_WINDOW_Y}")
        self.root.title(f"MMonitor {VERSION}")
        self.root.minsize(MAIN_WINDOW_X, MAIN_WINDOW_Y)

        # Style and theme
        style = ttk.Style()
        style.theme_use("default")  # Switch to the 'clam' theme for better styling flexibility

        print(ttk.Style().theme_names())

        style.map('TButton',
                  foreground=[('pressed', 'white'), ('active', 'black')],
                  background=[('pressed', '!disabled', '#B22222'), ('active', '#B0E0E6')]  # Light blue when active
                  )

        # Placeholder icon
        # placeholder_icon = tk.PhotoImage(width=16, height=)
        btn_icon_size = 35
        create_local_db_icon = resize_icon_to_xpx(f'{IMAGES_PATH}/mmonitor_button_add_db.png', btn_icon_size)
        add_db_icon = resize_icon_to_xpx(f'{IMAGES_PATH}/mmonitor_button_import_db.png', btn_icon_size)
        start_offline_monitoring_icon = resize_icon_to_xpx(f'{IMAGES_PATH}/offline_monitoring.png', btn_icon_size)
        user_authentication_icon = resize_icon_to_xpx(f"{IMAGES_PATH}/mmonitor_button4_authenticate.png", btn_icon_size)
        add_metadata_icon = resize_icon_to_xpx(f"{IMAGES_PATH}/mmonitor_button_importcsv.png", btn_icon_size)
        run_analysis_pipeline_icon = resize_icon_to_xpx(f"{IMAGES_PATH}/button_add_data2.png", btn_icon_size)
        quit_icon = resize_icon_to_xpx(f"{IMAGES_PATH}/mmonitor_button_quit.png", btn_icon_size)

        # placeholder_icon.put(("gray",), to=(0, 0, 15, 15))

        # Header with app title
        header_label = ttk.Label(self.root, text=f"Metagenome Monitor {VERSION}", font=("Helvetica", 18))
        header_label.pack(pady=10)

        # Categories and buttons

        categories = [
            ("Local", [
                ("Create Local DB", self.create_project, create_local_db_icon),
                ("Choose Local DB", self.choose_project, add_db_icon),
                ("Start offline monitoring", self.start_monitoring, start_offline_monitoring_icon)
            ]),
            ("Webserver", [
                ("User authentication", self.open_db_config_form, user_authentication_icon)
            ]),
            ("Add Data", [
                ("Add metadata from CSV", self.append_metadata, add_metadata_icon),
                ("Process sequencing files", self.checkbox_popup, run_analysis_pipeline_icon)
            ])
        ]

        # Tooltips for the categories
        category_tooltips = {
            "Local": "Use these function to store everything in a local Database. \n Then after adding data hit 'Start offline monitoring'. ",
            "Webserver": "Click 'User authentication' to provide your username and password for the webserver. \n After authentication"
                         " all data you add will be uploaded to the webserver as well. \n Provide same username and password that you used"
                         " for registration at the MMonitor webpage. Do not change 'host' or 'database'.",
            "Add Data": "Use this to add data to the local database and the webserver. \n Data can only be added if either"
                        " local database was chosen first or User Authentication was performed. \n If you did both data will be added to local DB and webserver.\n"
                        "'Add data from CSV' lets you add a CSV file with metadata. For an example file check out 'meta.csv' in the MMonitor root folder \n"
                        "'Process sequencing files' opens the analysis selection window. In this window select the analysis you want to perform and then click 'Continue'. For taxonomic analysis select only one please."

        }
        # Calculate the maximum button width based on text length
        button_texts = [btn[0] for cat in categories for btn in cat[1]]
        button_texts.append("Quit")  # Adding Quit button text
        max_text_length = max(map(len, button_texts))
        btn_width = max_text_length  # Adding an offset to account for padding and icon
        style = ttk.Style()

        style.configure('TButton',
                        font=("Helvetica", 14),
                        foreground='black',
                        bordercolor="black",
                        background='#FCF6F5',
                        padding=(3, 3, 3, 3),  # left, top, right, bottom padding
                        borderwidth=0,

                        roundedrelief=True)

        style.configure('TLabel',
                        background='#990011',
                        foreground='white',
                        font=("Helvetica", 18),
                        width=btn_width - 5,
                        padding=5,
                        anchor='center')

        for category, btns in categories:
            cat_label = ttk.Label(self.root, text=category, font=("Helvetica", 20), anchor="center")
            cat_label.pack(pady=10)

            if category in category_tooltips:
                self.create_tooltip(cat_label, category_tooltips[category])

            for text, cmd, img in btns:
                btn = ttk.Button(self.root, text=text, command=cmd, image=img, compound="left", style="TButton")
                btn.image = img
                btn.pack(pady=2)

            btn.pack(pady=2)

        # Quit button
        quit_btn = ttk.Button(self.root, text="Quit", command=self.stop_app, image=quit_icon, style="TButton")
        quit_btn.image = quit_icon
        quit_btn.pack(pady=15)

    # create_tooltip(local_label, "This is the tooltip text for the Local category.")
        # create_tooltip(webserver_label, "This is the tooltip text for the Webserver category.")

    def create_tooltip(self, widget, text):
        tooltip = ToolTip(widget, text)
        widget.bind("<Enter>", tooltip.show_tip)
        widget.bind("<Leave>", tooltip.hide_tip)

    def ask_create_subproject(self):
        # Create the root window but don't show it
        top = tk.Toplevel(self.root)
        top.geometry("300x300")

        # Ask the user if they want to create a subproject
        answer = messagebox.askyesno("Create Subproject", "Do you want to create a subproject?")

        # If the user selects 'Yes'
        if answer:
            subproject_name = simpledialog.askstring("Input", "What is the name of your subproject?")
            return subproject_name
        else:
            subproject_name = ""
            return subproject_name
        top.destroy()
        top.quit()


    def open_calendar(self):
        calendar_window = tk.Toplevel()
        calendar_window.title("Choose a Date")

        # Use a StringVar to hold our date
        selected_date_var = tk.StringVar()

        calendar = Calendar(calendar_window, selectmode="day")
        calendar.pack(pady=10)

        def on_date_select():
            selected_date_var.set(calendar.get_date())
            calendar_window.destroy()
            calendar_window.quit()

        select_button = ttk.Button(calendar_window, text="Select Date", command=on_date_select, style="TButton")
        select_button.pack(pady=20)

        # calendar_window.mainloop()

        return selected_date_var.get()

    def open_popup(self, text, title):
        top = tk.Toplevel(self.root)
        top.geometry("400x400")
        top.title(title)
        ttk.Label(top, text=text, font='Helvetica 18 bold').place(x=150, y=80)
        ttk.Button(top, text="Okay", command=top.destroy).pack()

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
    # @require_project
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

        # folder = filedialog.askdirectory(
        #     initialdir='/',
        #     title="Choose directory containing sequencing data"
        # )
        # files = self.centrifuge_runner.get_files_from_folder(folder)
        #
        # sample_name = simpledialog.askstring(
        #     "Input sample name",
        #     "What should the sample be called?",
        #     parent=self.root
        # )
        #
        #
        # sample_date = self.open_calendar()
        win = InputWindow(self.root, self.emu_runner)
        self.root.wait_window(win.top)
        # get entries from input window
        sample_name = str(win.sample_name_entry)  # Get the content of the entry and convert to string
        project_name = str(win.project_name_entry)
        subproject_name = str(win.subproject_name_entry)
        sample_date = win.selected_date.strftime('%Y-%m-%d')  # Convert date to string format
        files = win.file_paths

        self.centrifuge_runner.run_centrifuge(files, sample_name)
        self.centrifuge_runner.make_kraken_report()

        self.db.update_table_with_kraken_out(f"{ROOT}/src/resources/pipeline_out/{sample_name}_kraken_out", "species",
                                             sample_name, project_name, sample_date)

    def taxonomy_nanopore_16s(self):
        self.check_emu_db_exists()
        # create input window to input all relevant sample information and sequencing files
        win = InputWindow(self.root, self.emu_runner)
        self.root.wait_window(win.top)
        # get entries from input window
        sample_name = str(win.sample_name_entry)  # Get the content of the entry and convert to string
        project_name = str(win.project_name_entry)
        subproject_name = str(win.subproject_name_entry)
        sample_date = win.selected_date.strftime('%Y-%m-%d')  # Convert date to string format
        files = win.file_paths

        self.emu_runner.run_emu(files, sample_name)
        emu_out_path = f"{ROOT}/src/resources/pipeline_out/{sample_name}/"
        # emu_out_path = f"{ROOT}/src/resources/pipeline_out/subset/"
        # self.db.update_table_with_emu_out(emu_out_path,"species",sample_name,"project",self.sample_date)

        self.db_mysql.update_django_with_emu_out(emu_out_path, "species", sample_name, project_name, sample_date,
                                                 subproject_name)


    def checkbox_popup(self):
        pipeline_popup = PipelinePopup(self.root,
                                       self)  # Replace run_analysis_pipeline_function with your actual function


    def ask_sample_name(self):
        sample_name = simpledialog.askstring(
            "Input sample name",
            "What should the sample be called?",
            parent=self.root
        )
        return sample_name

    # @require_project

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
