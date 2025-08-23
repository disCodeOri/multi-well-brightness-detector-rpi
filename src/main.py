# main.py
#
# Main GUI application

import sys
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from PIL import Image, ImageTk
import numpy as np

# Tab modules imports
from tabs.capture_tab import CaptureTab
from tabs.analysis_tab import AnalysisTab
from tabs.results_tab import ResultsTab

class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Well Intensity Analyzer")

        # --- IMPROVED WINDOW SIZING WITH 16:9 RATIO ---
        # Get the screen dimensions
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        # Define minimum window dimensions (suitable for RPi screens)
        min_width = 800
        min_height = int(min_width * (9/16))  # Calculate height based on 16:9 ratio
        self.minsize(min_width, min_height)

        # Calculate initial window size (70% of screen width, maintaining 16:9 ratio)
        window_width = min(int(screen_width * 0.7), screen_width - 100)  # Leave some margin
        window_height = int(window_width * (9/16))

        # Ensure window isn't too tall for the screen
        if window_height > (screen_height - 100):  # Leave some margin
            window_height = screen_height - 100
            window_width = int(window_height * (16/9))  # Recalculate width to maintain ratio

        # Center the window on the screen
        position_x = (screen_width - window_width) // 2
        position_y = (screen_height - window_height) // 2

        # Set the initial size and position of the window
        self.geometry(f"{window_width}x{window_height}+{position_x}+{position_y}")
        # --- END OF WINDOW SIZING ---

        self.style = ttk.Style(self)
        self.style.theme_use('clam')
        self.style.configure('TNotebook.Tab', padding=[20, 10], font=('TkDefaultFont', 12, 'bold'))

        self.notebook = ttk.Notebook(self, style='TNotebook')
        self.notebook.pack(expand=True, fill='both', padx=10, pady=10)

        # --- Create and Add Tabs ---
        self.capture_tab = CaptureTab(self.notebook, {}, self.handle_image_capture)
        self.analysis_tab = AnalysisTab(self.notebook, {}, self.handle_analysis_results)
        self.results_tab = ResultsTab(self.notebook)
        
        self.notebook.add(self.capture_tab, text='Capture')
        self.notebook.add(self.analysis_tab, text='Analysis')
        self.notebook.add(self.results_tab, text='Results')
        
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def handle_image_capture(self, saved_image_path):
        """Callback from CaptureTab when an image is saved."""
        messagebox.showinfo("Image Saved", f"Image successfully saved to:\n{saved_image_path}")
        
    def handle_analysis_results(self, results_package):
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