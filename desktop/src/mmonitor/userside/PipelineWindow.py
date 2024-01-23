import tkinter as tk
from threading import Thread

import customtkinter as ctk


class PipelinePopup(ctk.CTkToplevel):

    def __init__(self, parent, gui_ref):
        super().__init__()
        ctk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

        self.parent = parent
        self.gui = gui_ref

        self.taxonomy_nanopore_wgs = tk.BooleanVar()
        self.taxonomy_nanopore_16s_bool = tk.BooleanVar()
        self.assembly = tk.BooleanVar()
        self.correction = tk.BooleanVar()
        self.binning = tk.BooleanVar()
        self.annotation = tk.BooleanVar()
        self.kegg = tk.BooleanVar()

        self.geometry("440x390")
        self.minsize(440, 390)
        self.title("Select analysis steps to perform.")

        frame_taxonomy = ctk.CTkFrame(self, corner_radius=10)
        frame_functional = ctk.CTkFrame(self, corner_radius=10)
        frame_taxonomy.pack(pady=5, padx=10, fill="both", expand=True)
        frame_functional.pack(pady=5, padx=10, fill="both", expand=True)

        label_taxonomy = ctk.CTkLabel(frame_taxonomy, text="Taxonomic analysis")
        label_functional = ctk.CTkLabel(frame_functional, text="Functional analysis")
        label_taxonomy.pack(pady=10)
        label_functional.pack(pady=10)

        # Taxonomy checkboxes
        ctk.CTkCheckBox(frame_taxonomy, text='Quick taxonomy nanopore', variable=self.taxonomy_nanopore_wgs).pack(
            pady=2)
        ctk.CTkCheckBox(frame_taxonomy, text='Quick taxonomy 16s nanopore',
                        variable=self.taxonomy_nanopore_16s_bool).pack(pady=2)

        # Functional analysis checkboxes
        ctk.CTkCheckBox(frame_functional, text='Assembly', variable=self.assembly).pack(pady=2)
        ctk.CTkCheckBox(frame_functional, text='Correction', variable=self.correction).pack(pady=2)
        ctk.CTkCheckBox(frame_functional, text='Binning', variable=self.binning).pack(pady=2)
        ctk.CTkCheckBox(frame_functional, text='Annotation', variable=self.annotation).pack(pady=2)
        ctk.CTkCheckBox(frame_functional, text='KEGG', variable=self.kegg).pack(pady=2)

        # Continue and Quit buttons
        continue_btn = ctk.CTkButton(self, text="Continue", command=self.run_analysis_pipeline, corner_radius=10)
        continue_btn.pack(pady=5)
        quit_btn = ctk.CTkButton(self, text="Quit", command=self.destroy, corner_radius=10)
        quit_btn.pack(pady=5)

    def on_kaiju_selected(self):
        # Assuming you have a way to get the sample_name, e.g., from a GUI component
        sample_name = self.get_selected_sample_name()

        self.gui.handle_kaiju_output(sample_name)


    def run_analysis_pipeline(self):
        # if self.assembly.get() or self.correction.get():
        #     seq_file = filedialog.askopenfilename(title="Please select a sequencing file")

        # if (self.assembly.get() or self.correction.get() or
        #         self.annotation.get() or self.binning.get()):
        #     sample_name = self.gui.ask_sample_name()
        #     self.gui.functional_analysis_runner.check_software_avail()

        if self.taxonomy_nanopore_wgs.get():
            thread_wgs = Thread(target=self.gui.taxonomy_nanopore_wgs)
            thread_wgs.start()

        if self.taxonomy_nanopore_16s_bool.get():
            thread_16s = Thread(target=self.gui.taxonomy_nanopore_16s)
            thread_16s.start()

        # if self.assembly.get():
        #     Wrapped in a lambda to defer execution
        # thread_assembly = Thread(target=lambda: self.gui.functional_analysis_runner.run_flye(seq_file, sample_name))
        # thread_assembly.start()

        # if self.correction.get():
        #     self.gui.functional_analysis_runner.run_racon(seq_file, sample_name)

        # if self.binning.get():
        #     self.gui.functional_analysis_runner.run_binning(sample_name)
        # if self.annotation.get():
        #     bins_path = f"{ROOT}/src/resources/{sample_name}/bins/"
        #     self.gui.functional_analysis_runner.run_prokka(bins_path)

        # if only kegg analysis is selected then the user needs to chose the path to the annotations
        # if self.kegg.get() and not self.assembly.get() and not self.correction.get() and not self.binning.get() and not self.annotation.get():
        #     sample_name = self.gui.ask_sample_name()
        #     pipeline_out = filedialog.askdirectory(
        #         title="Please select the path to the prokka output (folder with tsv files with annotations).")
        #     pipeline_out = f"{pipeline_out}/"
        #     pipeline_out = f"{ROOT}/src/resources/pipeline_out/{sample_name}/"
        #     self.kegg_thread1 = Thread(target=self.functional_analysis_runner.create_keggcharter_input(pipeline_out))
        #     self.kegg_thread1.start()
        #     self.kegg_thread2 = Thread(
        #         self.functional_analysis_runner.run_keggcharter(pipeline_out, f"{pipeline_out}keggcharter.tsv"))
        #     self.kegg_thread2.start()
        #
        # self.destroy()

        # if kegg and annotation is chosen then the user only needs to select the sample name, then the tsv files from the results
        # of the annotations will be used as input for creating keggcharter input and creating kegg maps
    # if self.kegg.get() and self.annotation.get():
    #     sample_name = self.ask_sample_name()
    #     # pipeline_out = filedialog.askdirectory(title="Please select the path to the prokka output (folder with tsv files with annotations).")
    #     pipeline_out = f"{ROOT}/src/resources/pipeline_out/{sample_name}/"
    #     self.kegg_thread1 = Thread(target=self.functional_analysis_runner.create_keggcharter_input(pipeline_out))
    #     self.kegg_thread1.start()
    #     self.kegg_thread2 = Thread(self.functional_analysis_runner.run_keggcharter(pipeline_out, f"{pipeline_out}/keggcharter.tsv"))
    #     self.kegg_thread2.start()
