# tabs/results_tab.py
#
# NEW FILE
# A fully functional, interactive "Results Explorer" tab.

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import numpy as np
import os
import shutil
import csv

class ResultsTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        
        self.results_data = None
        self.current_pil_image = None # For brightness/contrast adjustments
        self.photo_image = None
        
        self.brightness_var = tk.DoubleVar(value=0)
        self.contrast_var = tk.DoubleVar(value=1.0)
        
        # --- Define the Main Layout (Vertical Paned Window) ---
        self.main_pane = ttk.PanedWindow(self, orient=tk.VERTICAL)
        self.main_pane.pack(expand=True, fill='both', padx=10, pady=10)
        
        # --- Construct the Top Pane (Visuals) ---
        self.create_top_pane()
        
        # --- Construct the Bottom Pane (Data & Actions) ---
        self.create_bottom_pane()

        # Connect controls that need to be connected at creation time
        self.brightness_slider.config(command=self.apply_brightness_contrast)
        self.contrast_slider.config(command=self.apply_brightness_contrast)

    def create_top_pane(self):
        top_frame = ttk.Frame(self.main_pane)
        self.main_pane.add(top_frame, weight=3)
        
        # Horizontal splitter for Treeview and Preview
        top_pane = ttk.PanedWindow(top_frame, orient=tk.HORIZONTAL)
        top_pane.pack(expand=True, fill='both')

        # Left side: Treeview for well data
        tree_frame = ttk.LabelFrame(top_pane, text="Detected Wells", padding=5)
        top_pane.add(tree_frame, weight=1)
        
        self.tree = ttk.Treeview(tree_frame, columns=("Well ID", "Peak Intensity", "Frame #"), show="headings")
        self.tree.heading("Well ID", text="Well ID")
        self.tree.heading("Peak Intensity", text="Peak Intensity")
        self.tree.heading("Frame #", text="Frame #")
        self.tree.column("Well ID", width=80, anchor=tk.CENTER)
        self.tree.column("Peak Intensity", width=120, anchor=tk.CENTER)
        self.tree.column("Frame #", width=100, anchor=tk.CENTER)
        self.tree.pack(expand=True, fill='both')
        self.tree.bind('<<TreeviewSelect>>', self.on_well_select)

        # Right side: Image preview and controls
        preview_frame = ttk.LabelFrame(top_pane, text="Peak Frame Preview", padding=5)
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(0, weight=1)
        top_pane.add(preview_frame, weight=3)

        self.preview_label = ttk.Label(preview_frame, text="No results loaded.", anchor=tk.CENTER)
        self.preview_label.grid(row=0, column=0, columnspan=2, sticky="nsew")
        
        ttk.Label(preview_frame, text="Brightness:").grid(row=1, column=0, sticky='e', pady=(5,0))
        self.brightness_slider = ttk.Scale(preview_frame, from_=-100, to=100, orient=tk.HORIZONTAL, variable=self.brightness_var, state=tk.DISABLED)
        self.brightness_slider.grid(row=1, column=1, sticky='ew', padx=5, pady=(5,0))

        ttk.Label(preview_frame, text="Contrast:").grid(row=2, column=0, sticky='e')
        self.contrast_slider = ttk.Scale(preview_frame, from_=0.1, to=3.0, orient=tk.HORIZONTAL, variable=self.contrast_var, state=tk.DISABLED)
        self.contrast_slider.grid(row=2, column=1, sticky='ew', padx=5)

    def create_bottom_pane(self):
        bottom_frame = ttk.Frame(self.main_pane)
        self.main_pane.add(bottom_frame, weight=1)
        bottom_frame.columnconfigure(0, weight=1)
        bottom_frame.rowconfigure(0, weight=1)

        # Top part: Analysis Details Text
        text_frame = ttk.LabelFrame(bottom_frame, text="Analysis Details", padding=5)
        text_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 5))
        text_frame.rowconfigure(0, weight=1)
        text_frame.columnconfigure(0, weight=1)

        self.summary_text = tk.Text(text_frame, height=6, wrap=tk.WORD, state=tk.DISABLED, bg="#2b2b2b", fg="white")
        self.summary_text.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.summary_text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.summary_text.config(yscrollcommand=scrollbar.set)

        # Bottom part: Action buttons
        button_frame = ttk.LabelFrame(bottom_frame, text="Export", padding=10)
        button_frame.grid(row=1, column=0, sticky="ew")
        
        self.save_frame_btn = ttk.Button(button_frame, text="Save Selected Frame", state=tk.DISABLED, command=self.save_selected_frame)
        self.save_frame_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        
        self.save_all_frames_btn = ttk.Button(button_frame, text="Save All Peak Frames", state=tk.DISABLED, command=self.save_all_peak_frames)
        self.save_all_frames_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        
        self.save_csv_btn = ttk.Button(button_frame, text="Save Data (CSV)", state=tk.DISABLED, command=self.save_data_csv)
        self.save_csv_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        
        self.clear_btn = ttk.Button(button_frame, text="Clear Results", state=tk.DISABLED, command=self.clear_results)
        self.clear_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)

    def display_results(self, results_package):
        """Main entry point for populating the tab with analysis results."""
        self.clear_results() # Start from a clean slate
        self.results_data = results_package
        
        # Populate the Treeview
        for item in self.results_data['numerical_data']:
            self.tree.insert('', tk.END, values=(f"Well {item['well_id']+1}", f"{item['intensity']:.2f}", item['frame']))

        # Populate the summary text
        self.summary_text.config(state=tk.NORMAL)
        self.summary_text.delete('1.0', tk.END)
        self.summary_text.insert(tk.END, self.results_data['summary_text'])
        self.summary_text.config(state=tk.DISABLED)

        # Load the first well's image and select it in the tree
        if self.tree.get_children():
            first_item = self.tree.get_children()[0]
            self.tree.selection_set(first_item)
            self.tree.focus(first_item)
        
        # Enable controls
        self.set_controls_state(tk.NORMAL)

    def on_well_select(self, event):
        """Called when a user selects a well in the Treeview."""
        selected_items = self.tree.selection()
        if not selected_items: return
        
        selected_item = selected_items[0]
        item_data = self.tree.item(selected_item)
        well_id_str = item_data['values'][0] # e.g., "Well 1"
        well_index = int(well_id_str.split(' ')[1]) - 1

        if self.results_data and well_index < len(self.results_data['visuals']['peak_frames_paths']):
            image_path = self.results_data['visuals']['peak_frames_paths'][well_index]
            self._load_image_to_preview(image_path)

    def _load_image_to_preview(self, image_path):
        """Helper to load an image file into the preview label."""
        try:
            self.current_pil_image = Image.open(image_path).convert("RGB")
            # Reset sliders for new image
            self.brightness_var.set(0)
            self.contrast_var.set(1.0)
            self.apply_brightness_contrast()
        except Exception as e:
            self.preview_label.config(image='', text=f"Error loading image:\n{e}")
            self.current_pil_image = None
    
    def apply_brightness_contrast(self, event=None):
        """Applies software brightness/contrast to the current PIL image."""
        if self.current_pil_image is None: return

        brightness = self.brightness_var.get()
        contrast = self.contrast_var.get()
        
        # Use NumPy for robust adjustment
        img_np = np.array(self.current_pil_image).astype(np.int16)
        adjusted_np = np.clip(img_np * contrast + brightness, 0, 255).astype(np.uint8)
        adjusted_pil = Image.fromarray(adjusted_np)

        self.preview_label.update_idletasks()
        lw, lh = self.preview_label.winfo_width(), self.preview_label.winfo_height()
        if lw > 1 and lh > 1:
            adjusted_pil.thumbnail((lw, lh), Image.Resampling.LANCZOS)
        
        self.photo_image = ImageTk.PhotoImage(image=adjusted_pil)
        self.preview_label.config(image=self.photo_image, text="")

    def save_selected_frame(self):
        """Saves the currently displayed (and adjusted) frame."""
        if not self.photo_image:
            messagebox.showwarning("Save Error", "No image is currently displayed.")
            return

        filepath = filedialog.asksaveasfilename(
            title="Save Frame As",
            defaultextension=".png",
            filetypes=(("PNG Image", "*.png"), ("JPEG Image", "*.jpg"), ("All files", "*.*"))
        )
        if not filepath: return

        try:
            # Re-create the full-resolution adjusted image for saving
            brightness = self.brightness_var.get()
            contrast = self.contrast_var.get()
            img_np = np.array(self.current_pil_image).astype(np.int16)
            adjusted_np = np.clip(img_np * contrast + brightness, 0, 255).astype(np.uint8)
            img_to_save = Image.fromarray(adjusted_np)
            img_to_save.save(filepath)
            messagebox.showinfo("Success", f"Image saved successfully to:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Save Error", f"Could not save the image: {e}")

    def save_all_peak_frames(self):
        """Copies all original peak frame images to a user-selected directory."""
        if not self.results_data: return
        
        directory = filedialog.askdirectory(title="Select Directory to Save All Frames")
        if not directory: return

        try:
            paths = self.results_data['visuals']['peak_frames_paths']
            for i, src_path in enumerate(paths):
                filename = os.path.basename(src_path)
                dest_path = os.path.join(directory, filename)
                shutil.copy(src_path, dest_path)
            messagebox.showinfo("Success", f"Successfully saved {len(paths)} peak frames to:\n{directory}")
        except Exception as e:
            messagebox.showerror("Save Error", f"An error occurred while saving files: {e}")
            
    def save_data_csv(self):
        """Saves the numerical analysis data to a CSV file."""
        if not self.results_data: return

        filepath = filedialog.asksaveasfilename(
            title="Save Data As CSV",
            defaultextension=".csv",
            filetypes=(("CSV File", "*.csv"), ("All files", "*.*"))
        )
        if not filepath: return
        
        try:
            data = self.results_data['numerical_data']
            headers = data[0].keys()
            with open(filepath, 'w', newline='') as output_file:
                writer = csv.DictWriter(output_file, fieldnames=headers)
                writer.writeheader()
                writer.writerows(data)
            messagebox.showinfo("Success", f"Data saved successfully to:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Save Error", f"Could not save the CSV file: {e}")

    def clear_results(self):
        """Resets the tab to its initial state."""
        self.results_data = None
        self.current_pil_image = None
        self.photo_image = None
        
        # Clear Treeview
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        # Clear preview
        self.preview_label.config(image='', text="No results loaded.")
        
        # Clear text box
        self.summary_text.config(state=tk.NORMAL)
        self.summary_text.delete('1.0', tk.END)
        self.summary_text.config(state=tk.DISABLED)
        
        # Reset sliders
        self.brightness_var.set(0)
        self.contrast_var.set(1.0)
        
        # Disable controls
        self.set_controls_state(tk.DISABLED)

    def set_controls_state(self, state):
        """Helper to enable/disable all interactive widgets."""
        self.brightness_slider.config(state=state)
        self.contrast_slider.config(state=state)
        self.save_frame_btn.config(state=state)
        self.save_all_frames_btn.config(state=state)
        self.save_csv_btn.config(state=state)
        self.clear_btn.config(state=state)

    def cleanup(self):
        """Placeholder for cleanup logic if needed in the future."""
        pass