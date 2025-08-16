# tabs/analysis_tab.py
#
# A complete 'Analysis' tab with a fully functional video player for preview.
# NEW: Implemented a resizable PanedWindow between the video preview and the report section.
# NEW: Added a "Sample Rate" control to process only every Nth frame, improving performance.

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import queue
import time
import os
import cv2
from PIL import Image, ImageTk
import numpy as np

# Import the analysis functions from your backend script
import well_analyzer

class AnalysisTab(ttk.Frame):
    def __init__(self, parent, config):
        super().__init__(parent)
        
        self.config = config
        self.video_path = None
        self.results_queue = queue.Queue()

        # --- Video Playback State ---
        self.video_capture = None
        self.playback_thread = None
        self.is_playing = False
        self.stop_playback_flag = threading.Event()
        self.current_frame = None
        self.total_frames = 0
        self.fps = 30
        self.frame_lock = threading.Lock()
        self.photo_image = None
        self.video_lock = threading.Lock()
        self._after_id = None

        # --- Configure Grid Layout for the main tab ---
        self.columnconfigure(0, weight=1) # Left side (the new pane)
        self.columnconfigure(1, weight=0) # Right side (controls)
        self.rowconfigure(0, weight=1)    # Main content row

        # <<< NEW: Create the main resizable pane for the left side >>>
        self.main_pane = ttk.PanedWindow(self, orient=tk.VERTICAL)
        self.main_pane.grid(row=0, column=0, sticky="nsew", padx=10, pady=(10,0))

        # --- Create and add sections to the pane ---
        # The creation methods will now add their frames to the main_pane
        self.create_preview_section(self.main_pane)
        self.create_report_section(self.main_pane)
        
        # --- Create the controls section on the right side ---
        self.create_controls_section()
        self.connect_controls()

        # Progress bar will be placed at the bottom
        self.progress_bar = ttk.Progressbar(self, orient='horizontal', mode='indeterminate')

    def create_preview_section(self, parent_pane):
        # The parent is now the PanedWindow
        preview_frame = ttk.LabelFrame(parent_pane, text="Media Preview", padding="10")
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(0, weight=1)

        # <<< NEW: Add the created frame to the parent pane >>>
        # The weight determines how the space is distributed when resizing.
        parent_pane.add(preview_frame, weight=3) # Give preview more initial space

        self.preview_label = ttk.Label(preview_frame, text="Load a video to see a preview.", anchor=tk.CENTER)
        self.preview_label.grid(row=0, column=0, sticky="nsew")

        playback_controls_frame = ttk.Frame(preview_frame)
        playback_controls_frame.grid(row=1, column=0, sticky="ew", pady=(5,0))
        playback_controls_frame.columnconfigure(1, weight=1)
        self.play_pause_button = ttk.Button(playback_controls_frame, text="▶ Play", state=tk.DISABLED, command=self.toggle_play_pause)
        self.play_pause_button.grid(row=0, column=0, padx=(0, 5))
        self.progress_slider = ttk.Scale(playback_controls_frame, from_=0, to=100, orient=tk.HORIZONTAL, state=tk.DISABLED, command=self.on_slider_move)
        self.progress_slider.grid(row=0, column=1, sticky="ew")
        self.loop_video_var = tk.BooleanVar(value=False)
        self.loop_video_checkbutton = ttk.Checkbutton(playback_controls_frame, text="Loop", variable=self.loop_video_var, state=tk.DISABLED)
        self.loop_video_checkbutton.grid(row=0, column=2, padx=(5,0))

    def create_report_section(self, parent_pane):
        # The parent is now the PanedWindow
        report_frame = ttk.LabelFrame(parent_pane, text="Analysis Report", padding="10")
        report_frame.columnconfigure(0, weight=1)
        report_frame.rowconfigure(0, weight=1)
        
        # <<< NEW: Add the created frame to the parent pane >>>
        parent_pane.add(report_frame, weight=1) # Give report less initial space

        self.report_display = tk.Text(report_frame, height=8, wrap=tk.WORD, state=tk.DISABLED, bg="#2b2b2b", fg="white", relief=tk.FLAT)
        self.report_display.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(report_frame, orient=tk.VERTICAL, command=self.report_display.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.report_display.config(yscrollcommand=scrollbar.set)

    def create_controls_section(self):
        # This frame grids itself to the main tab window, on the right
        controls_frame = ttk.LabelFrame(self, text="Analysis Controls", padding="10")
        controls_frame.grid(row=0, column=1, sticky="ns", padx=(0, 10), pady=10)
        
        # (Rest of this method is unchanged)
        action_frame = ttk.Frame(controls_frame, padding=(0, 0, 0, 10))
        action_frame.pack(fill=tk.X)
        self.load_button = ttk.Button(action_frame, text="Load Media")
        self.load_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))
        self.clear_button = ttk.Button(action_frame, text="Clear", state=tk.DISABLED)
        self.clear_button.pack(side=tk.LEFT, expand=True, fill=tk.X)
        settings_frame = ttk.Frame(controls_frame, padding=(0, 5, 0, 15))
        settings_frame.pack(fill=tk.X)
        settings_frame.columnconfigure(1, weight=1)
        row_counter = 0
        ttk.Label(settings_frame, text="Threshold:").grid(row=row_counter, column=0, sticky="w", pady=5)
        self.threshold_spinbox = ttk.Spinbox(settings_frame, from_=1, to=254, width=7)
        self.threshold_spinbox.set("120")
        self.threshold_spinbox.grid(row=row_counter, column=1, sticky="ew", padx=5); row_counter += 1
        ttk.Label(settings_frame, text="Min Well Area:").grid(row=row_counter, column=0, sticky="w", pady=5)
        self.min_area_spinbox = ttk.Spinbox(settings_frame, from_=10, to=1000, width=7)
        self.min_area_spinbox.set("100")
        self.min_area_spinbox.grid(row=row_counter, column=1, sticky="ew", padx=5); row_counter += 1
        ttk.Label(settings_frame, text="Brightness Metric:").grid(row=row_counter, column=0, sticky="w", pady=5)
        self.metric_selector = ttk.Combobox(settings_frame, values=["Average Intensity", "Peak Intensity"], state="readonly")
        self.metric_selector.current(0)
        self.metric_selector.grid(row=row_counter, column=1, sticky="ew", padx=5); row_counter += 1
        
        # <<< NEW: Add Sample Rate Spinbox >>>
        ttk.Label(settings_frame, text="Sample Rate:").grid(row=row_counter, column=0, sticky="w", pady=5)
        self.sample_rate_spinbox = ttk.Spinbox(settings_frame, from_=1, to=100, width=7)
        self.sample_rate_spinbox.set("1")
        self.sample_rate_spinbox.grid(row=row_counter, column=1, sticky="ew", padx=5); row_counter += 1

        self.run_button = ttk.Button(controls_frame, text="Run Analysis", state=tk.DISABLED)
        style = ttk.Style()
        style.configure('Accent.TButton', font=('TkDefaultFont', 10, 'bold'))
        self.run_button.config(style='Accent.TButton')
        self.run_button.pack(fill=tk.X, pady=(10, 0))
        
    def connect_controls(self):
        self.load_button.config(command=self.load_media)
        self.clear_button.config(command=self.clear_media)
        self.run_button.config(command=self.start_analysis)
        
    def start_analysis(self):
        if not self.video_path: messagebox.showerror("Error", "No video file loaded."); return
        if self.is_playing: self.toggle_play_pause()
        threshold = int(self.threshold_spinbox.get())
        min_area = int(self.min_area_spinbox.get())
        metric_str = self.metric_selector.get()
        metric_mode = 'peak' if metric_str == "Peak Intensity" else 'average'
        sample_rate = int(self.sample_rate_spinbox.get()) # <<< NEW: Get sample rate
        self.set_ui_state(tk.DISABLED)
        self.progress_bar.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=(5,10))
        self.progress_bar.start()
        # <<< MODIFIED: Pass sample_rate to the worker thread >>>
        analysis_thread = threading.Thread(
            target=self._analysis_thread_worker, 
            args=(self.video_path, threshold, min_area, metric_mode, sample_rate), 
            daemon=True
        )
        analysis_thread.start()
        self.after(100, self.check_analysis_queue)

    def load_media(self):
        filepath = filedialog.askopenfilename(title="Select a Video File", filetypes=(("Video Files", "*.mp4 *.avi *.mov"), ("All files", "*.*")))
        if not filepath: return
        self.clear_media()
        self.video_path = filepath
        try:
            with self.video_lock:
                self.video_capture = cv2.VideoCapture(self.video_path)
                if not self.video_capture.isOpened(): raise IOError("Cannot open video file")
                self.total_frames = int(self.video_capture.get(cv2.CAP_PROP_FRAME_COUNT))
                self.fps = self.video_capture.get(cv2.CAP_PROP_FPS)
                if self.fps == 0: self.fps = 30
                ret, frame = self.video_capture.read()
            if ret:
                self.current_frame = frame
                self.display_current_frame()
                self.progress_slider.config(to=self.total_frames - 1)
            else:
                self.preview_label.config(text="Could not read first frame.", image='')
                return
        except Exception as e:
            messagebox.showerror("Error", f"Could not load video: {e}")
            self.clear_media()
            return
        self.run_button.config(state=tk.NORMAL)
        self.clear_button.config(state=tk.NORMAL)
        self.play_pause_button.config(state=tk.NORMAL)
        self.progress_slider.config(state=tk.NORMAL)
        self.loop_video_checkbutton.config(state=tk.NORMAL)

    def clear_media(self):
        self.stop_playback()
        with self.video_lock:
            if self.video_capture:
                self.video_capture.release()
                self.video_capture = None
        self.video_path = None
        self.preview_label.config(image='', text="Load a video to see a preview.")
        self.run_button.config(state=tk.DISABLED)
        self.clear_button.config(state=tk.DISABLED)
        self.play_pause_button.config(text="▶ Play", state=tk.DISABLED)
        self.progress_slider.set(0)
        self.progress_slider.config(state=tk.DISABLED)
        self.loop_video_checkbutton.config(state=tk.DISABLED)
        self.report_display.config(state=tk.NORMAL)
        self.report_display.delete('1.0', tk.END)
        self.report_display.config(state=tk.DISABLED)

    def toggle_play_pause(self):
        if self.is_playing:
            self.is_playing = False
            self.play_pause_button.config(text="▶ Play")
            if self._after_id:
                self.after_cancel(self._after_id)
                self._after_id = None
        else:
            self.is_playing = True
            self.play_pause_button.config(text="❚❚ Pause")
            if self.playback_thread is None or not self.playback_thread.is_alive():
                self.start_playback()
            else:
                if not self._after_id:
                    self._after_id = self.after(int(1000 / self.fps), self.update_video_frame)

    def start_playback(self):
        if not self.video_capture: return
        self.stop_playback_flag.clear()
        self.playback_thread = threading.Thread(target=self._video_playback_loop, daemon=True)
        self.playback_thread.start()
        self._after_id = self.after(int(1000 / self.fps), self.update_video_frame)

    def stop_playback(self):
        self.is_playing = False
        self.stop_playback_flag.set()
        if self._after_id:
            self.after_cancel(self._after_id)
            self._after_id = None
        if self.playback_thread and self.playback_thread.is_alive():
            self.playback_thread.join(timeout=1.0)
        self.playback_thread = None

    def _video_playback_loop(self):
        while not self.stop_playback_flag.is_set():
            if self.is_playing:
                start_time = time.time()
                with self.video_lock:
                    if not self.video_capture: break
                    ret, frame = self.video_capture.read()
                    if not ret:
                        if self.loop_video_var.get():
                            self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
                            continue
                        else:
                            self.is_playing = False
                            self.after(0, lambda: self.play_pause_button.config(text="▶ Play"))
                            self.after(0, lambda: self.progress_slider.set(self.total_frames - 1))
                            continue
                with self.frame_lock:
                    self.current_frame = frame
                elapsed = time.time() - start_time
                sleep_time = (1.0 / self.fps) - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)
            else:
                time.sleep(0.01)

    def update_video_frame(self):
        if self.stop_playback_flag.is_set() or not self.is_playing:
            self._after_id = None
            return
        self.display_current_frame()
        current_pos = 0
        with self.video_lock:
            if self.video_capture and self.video_capture.isOpened():
                 current_pos = int(self.video_capture.get(cv2.CAP_PROP_POS_FRAMES))
        self.progress_slider.set(current_pos)
        self._after_id = self.after(int(1000 / self.fps), self.update_video_frame)
            
    def display_current_frame(self):
        with self.frame_lock:
            if self.current_frame is None: return
            frame_to_show = self.current_frame.copy()
        self.preview_label.update_idletasks()
        lw, lh = self.preview_label.winfo_width(), self.preview_label.winfo_height()
        if lw > 1 and lh > 1:
            img = cv2.cvtColor(frame_to_show, cv2.COLOR_BGR2RGB)
            img_pil = Image.fromarray(img)
            img_pil.thumbnail((lw, lh), Image.Resampling.LANCZOS)
            self.photo_image = ImageTk.PhotoImage(image=img_pil)
            self.preview_label.config(image=self.photo_image)
    
    def on_slider_move(self, value):
        with self.video_lock:
            if self.video_capture and self.video_capture.isOpened():
                frame_num = int(float(value))
                self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
                ret, frame = self.video_capture.read()
                if ret:
                    with self.frame_lock:
                        self.current_frame = frame
                    self.display_current_frame()
                    
    def cleanup(self):
        self.stop_playback()

    def _analysis_thread_worker(self, video_path, threshold, min_area, metric_mode, sample_rate):
        try:
            # Note: find_well_locations should scan all frames to be robust.
            well_rois, _ = well_analyzer.find_well_locations(video_path, threshold, min_area)
            if not well_rois:
                self.results_queue.put("Error: No wells detected. Try adjusting parameters.")
                return
            
            # <<< MODIFIED: Pass sample_rate to tracking and analysis functions >>>
            intensity_data = well_analyzer.track_well_intensities(video_path, well_rois, metric_mode, sample_rate)
            peak_results = well_analyzer.analyze_peaks(intensity_data, metric_mode, sample_rate)
            
            # Format the report based on the metric mode
            report = "--- Analysis Report ---\n\n"
            metric_name = "Average" if metric_mode == 'average' else "Peak"
            
            for result in peak_results:
                report += f"Well {result['well_id'] + 1}: {metric_name} Intensity of {result['intensity']:.2f} at Frame {result['frame']}\n"
                
            self.results_queue.put(report)
        except Exception as e:
            self.results_queue.put(f"An error occurred during analysis:\n{e}")

    def check_analysis_queue(self):
        try:
            result = self.results_queue.get_nowait()
            self.progress_bar.stop()
            self.progress_bar.grid_remove()
            self.set_ui_state(tk.NORMAL)
            self.report_display.config(state=tk.NORMAL)
            self.report_display.delete('1.0', tk.END)
            self.report_display.insert(tk.END, result)
            self.report_display.config(state=tk.DISABLED)
        except queue.Empty:
            self.after(100, self.check_analysis_queue)

    def set_ui_state(self, state):
        self.load_button.config(state=state)
        video_loaded_state = tk.NORMAL if self.video_path and state == tk.NORMAL else tk.DISABLED
        self.clear_button.config(state=video_loaded_state)
        self.run_button.config(state=video_loaded_state)
        self.play_pause_button.config(state=video_loaded_state)
        self.progress_slider.config(state=video_loaded_state)
        self.loop_video_checkbutton.config(state=video_loaded_state)
        self.threshold_spinbox.config(state=state)
        self.min_area_spinbox.config(state=state)
        self.metric_selector.config(state=state)
        self.sample_rate_spinbox.config(state=state) # <<< NEW: Set state for the new spinbox