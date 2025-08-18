# main.py
#
# Main GUI application
# MODIFIED: Now creates and manages the ResultsTab and handles the data
#           flow from the AnalysisTab to the ResultsTab.

import sys
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from PIL import Image, ImageTk
import numpy as np

# Import our tab modules
from tabs.capture_tab import CaptureTab
from tabs.analysis_tab import AnalysisTab
from tabs.results_tab import ResultsTab # <<< NEW: Import ResultsTab

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
        # <<< MODIFIED: Pass the results handler to AnalysisTab >>>
        self.analysis_tab = AnalysisTab(self.notebook, {}, self.handle_analysis_results)
        self.results_tab = ResultsTab(self.notebook) # <<< NEW: Create ResultsTab instance
        
        self.notebook.add(self.capture_tab, text='Capture')
        self.notebook.add(self.analysis_tab, text='Analysis')
        self.notebook.add(self.results_tab, text='Results') # <<< MODIFIED: Add the real tab
        
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def handle_image_capture(self, saved_image_path):
        """Callback from CaptureTab when an image is saved."""
        messagebox.showinfo("Image Saved", f"Image successfully saved to:\n{saved_image_path}")
        
    def handle_analysis_results(self, results_package):
        """
        <<< NEW >>>
        This is the callback for the AnalysisTab.
        It receives the complete results package and passes it to the ResultsTab.
        """
        if results_package.get("error"):
            messagebox.showerror("Analysis Error", results_package["error"])
            return
            
        # Pass the data to the results tab for display
        self.results_tab.display_results(results_package)
        
        # Switch the view to the Results tab
        self.notebook.select(self.results_tab)
        
    def on_closing(self):
        """Called when the user closes the window."""
        self.capture_tab.cleanup()
        self.analysis_tab.cleanup()
        self.results_tab.cleanup()
        self.destroy()

# --- Main execution block ---
if __name__ == '__main__':
    app = MainWindow()
    app.mainloop()