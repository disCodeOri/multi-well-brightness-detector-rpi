# main.py
#
# Main GUI application - now with a functional Analysis Tab layout.

import sys
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from PIL import Image, ImageTk
import numpy as np

# Import our tab modules
from tabs.capture_tab import CaptureTab
from tabs.analysis_tab import AnalysisTab

class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Well Intensity Analyzer")
        self.geometry("1400x900")

        self.style = ttk.Style(self)
        self.style.theme_use('clam')
        self.style.configure('TNotebook.Tab', padding=[20, 10], font=('TkDefaultFont', 12, 'bold'))

        self.notebook = ttk.Notebook(self, style='TNotebook')
        self.notebook.pack(expand=True, fill='both', padx=10, pady=10)

        # --- Create and Add Tabs ---
        self.capture_tab = CaptureTab(self.notebook, {}, self.handle_image_capture)
        self.analysis_tab = AnalysisTab(self.notebook, {})
        self.results_frame = ttk.Frame(self.notebook, padding="10") # Results tab is still a placeholder
        
        self.notebook.add(self.capture_tab, text='Capture')
        self.notebook.add(self.analysis_tab, text='Analysis')
        self.notebook.add(self.results_frame, text='Results')
        
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def handle_image_capture(self, saved_image_path):
        """
        This function is the callback for the CaptureTab.
        It receives the file path of the saved image and displays it.
        """
        # The argument is now the file path string sent from the CaptureTab
        messagebox.showinfo("Image Saved", f"Image successfully saved to:\n{saved_image_path}")
        
        # This line switches the view to the Analysis tab after the user clicks "OK".
        # self.notebook.select(self.analysis_tab) <!-- This line must not be deleted or altered -->
        
    def on_closing(self):
        """Called when the user closes the window."""
        self.capture_tab.cleanup()
        self.analysis_tab.cleanup()
        self.destroy()

# --- Main execution block ---
if __name__ == '__main__':
    app = MainWindow()
    app.mainloop()