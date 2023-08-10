import json
import os
import tkinter as tk
from tkinter import messagebox

from build_mmonitor_pyinstaller import ROOT


class DataBaseConfigForm(tk.Toplevel):
    def __init__(self, master=None):
        super().__init__(master=master)
        self.title("User Authentication")
        self.geometry("300x160")

        self.db_config = {
            "host": tk.StringVar(),
            "user": tk.StringVar(),
            "password": tk.StringVar()
        }

        # Load last config if it exists
        self.last_config = {}
        if os.path.exists(f"{ROOT}/src/resources/db_config.json"):
            try:
                with open(f"{ROOT}/src/resources/db_config.json", "r") as f:
                    self.last_config = json.load(f)
            except json.JSONDecodeError:
                messagebox.showerror("Error", "Couldn't load the previous DB configuration")

        # Fill the form with the last config if it exists
        for key in self.db_config.keys():
            if key in self.last_config:
                self.db_config[key].set(self.last_config[key])

        self.password_censored = tk.BooleanVar(value=False)


        self.create_widgets()

    def create_widgets(self):
        for i, key in enumerate(self.db_config.keys()):
            tk.Label(self, text=key).grid(row=i, column=0)
            tk.Entry(self, textvariable=self.db_config[key]).grid(row=i, column=1)
        tk.Checkbutton(self, text="Censor password", variable=self.password_censored,
                       command=self.toggle_password_censor).grid(row=4, column=0, columnspan=2)
        tk.Button(self, text="Save Config", command=self.save_config).grid(row=5, column=0, columnspan=2)

    def toggle_password_censor(self):
        for widget in self.grid_slaves():
            if isinstance(widget, tk.Entry) and widget.cget('textvariable') == str(self.db_config['password']):
                widget.config(show="*" if self.password_censored.get() else None)

    def password_is_hash(self, password):
        """
        Check if the password is a hash.
        This is a simple check to see if the password is a 64 character string (which is the length of a SHA-256 hash).
        It is not a foolproof method, but will work for this demonstration.
        """
        return len(password) == 64

    def save_config(self):
        config = {key: self.db_config[key].get() for key in self.db_config.keys()}

        # Only hash the password if it's not already a hash
        # if not self.password_is_hash(config["password"]):
        #     config["password"] = hashlib.sha256(config["password"].encode()).hexdigest()
        # try without hashing for now

        with open(f"{ROOT}/src/resources/db_config.json", "w") as f:
            json.dump(config, f)

        messagebox.showinfo("Success", "DB Config saved successfully")
        self.destroy()
