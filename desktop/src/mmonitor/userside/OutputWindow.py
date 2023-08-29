import sys
import tkinter as tk


class OutputWindow(tk.Toplevel):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)

        # Set title
        self.title("Output Window")

        # Create a scrollbar
        scrollbar = tk.Scrollbar(self)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Create a text widget
        self.text = tk.Text(self, wrap=tk.NONE, yscrollcommand=scrollbar.set)
        self.text.pack(expand=True, fill=tk.BOTH)

        # Configure scrollbar for text widget
        scrollbar.config(command=self.text.yview)

        # Redirect stdout to this window
        sys.stdout = self

    def write(self, txt):
        # Append text to the text widget
        self.text.insert(tk.END, txt)
        # Auto-scroll to the end
        self.text.see(tk.END)
        # Update the GUI (needed if writing in a loop or another thread)
        self.text.update_idletasks()

    def close(self):
        # Restore stdout to its original state
        sys.stdout = sys.__stdout__
        self.destroy()


# Example of usage
if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()  # Hide the main window

    output_win = OutputWindow()
    print("Starting process...")
    for i in range(10):
        print(f"Processing {i}...")
    print("Process completed!")

    root.mainloop()
