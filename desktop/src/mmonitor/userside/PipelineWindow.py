import tkinter as tk
from threading import Thread
from tkinter import ttk, filedialog


class PipelinePopup:

    def __init__(self, parent, gui_ref):
        self.parent = parent
        self.gui = gui_ref

        # Variables for checkboxes
        self.taxonomy_nanopore_wgs = tk.BooleanVar()
        self.taxonomy_nanopore_16s_bool = tk.BooleanVar()
        self.assembly = tk.BooleanVar()
        self.correction = tk.BooleanVar()
        self.binning = tk.BooleanVar()
        self.annotation = tk.BooleanVar()
        self.kegg = tk.BooleanVar()

        # Create Toplevel popup
        self.top = tk.Toplevel(parent)
        self.top.geometry("440x350")
        self.top.title("Select analysis steps to perform.")

        frame_taxonomy = tk.LabelFrame(self.top, padx=10, pady=2, text="Taxonomic analysis")
        frame_functional = tk.LabelFrame(self.top, padx=10, pady=2, text="Functional analysis")
        frame_taxonomy.pack(pady=5, padx=10)
        frame_functional.pack(pady=5, padx=10)

        button_width = 30
        padding_y = 5

        # Taxonomy checkboxes
        ttk.Checkbutton(frame_taxonomy, text='Quick taxonomy nanopore', variable=self.taxonomy_nanopore_wgs,
                        width=button_width).pack()
        ttk.Checkbutton(frame_taxonomy, text='Quick taxonomy 16s nanopore', variable=self.taxonomy_nanopore_16s_bool,
                        width=button_width).pack()

        # Functional analysis checkboxes
        ttk.Checkbutton(frame_functional, text='Assembly', variable=self.assembly, width=button_width).pack()
        ttk.Checkbutton(frame_functional, text='Correction', variable=self.correction, width=button_width).pack()
        ttk.Checkbutton(frame_functional, text='Binning', variable=self.binning, width=button_width).pack()
        ttk.Checkbutton(frame_functional, text='Annotation', variable=self.annotation, width=button_width).pack()
        ttk.Checkbutton(frame_functional, text='KEGG', variable=self.kegg, width=button_width).pack()

        # Continue and Quit buttons
        ttk.Button(self.top, text="Continue", width=10, command=self.run_analysis_pipeline).pack(pady=padding_y)
        ttk.Button(self.top, text="Quit", command=self.top.destroy, width=10).pack(pady=padding_y)

    def on_kaiju_selected(self):
        # Assuming you have a way to get the sample_name, e.g., from a GUI component
        sample_name = self.get_selected_sample_name()

        self.gui.handle_kaiju_output(sample_name)


    def run_analysis_pipeline(self):
        # Assuming `self.pipeline_popup` is your instance of `PipelinePopup`
        if self.assembly.get() or self.correction.get():
            seq_file = filedialog.askopenfilename(title="Please select a sequencing file")

        if (self.assembly.get() or self.correction.get() or
                self.annotation.get() or self.binning.get()):
            sample_name = self.gui.ask_sample_name()
            self.gui.functional_analysis_runner.check_software_avail()

        if self.taxonomy_nanopore_wgs.get():
            thread_wgs = Thread(target=self.gui.taxonomy_nanopore_wgs)
            thread_wgs.start()

        if self.taxonomy_nanopore_16s_bool.get():
            thread_16s = Thread(target=self.gui.taxonomy_nanopore_16s)
            thread_16s.start()


        if self.assembly.get():
            self.gui.functional_analysis_runner.run_flye(seq_file, sample_name)
        if self.correction.get():
            self.gui.functional_analysis_runner.run_racon(seq_file, sample_name)

        if self.binning.get():
            self.gui.functional_analysis_runner.run_binning(sample_name)
        if self.annotation.get():
            bins_path = f"{ROOT}/src/resources/{sample_name}/bins/"
            self.gui.functional_analysis_runner.run_prokka(bins_path)

        # if only kegg analysis is selected then the user needs to chose the path to the annotations
        if self.kegg.get() and not self.assembly.get() and not self.correction.get() and not self.binning.get() and not self.annotation.get():
            sample_name = self.gui.ask_sample_name()
            pipeline_out = filedialog.askdirectory(
                title="Please select the path to the prokka output (folder with tsv files with annotations).")
            pipeline_out = f"{pipeline_out}/"
            pipeline_out = f"{ROOT}/src/resources/pipeline_out/{sample_name}/"
            self.kegg_thread1 = Thread(target=self.functional_analysis_runner.create_keggcharter_input(pipeline_out))
            self.kegg_thread1.start()
            self.kegg_thread2 = Thread(
                self.functional_analysis_runner.run_keggcharter(pipeline_out, f"{pipeline_out}keggcharter.tsv"))
            self.kegg_thread2.start()

        self.top.destroy()

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
