# tabs/analysis_tab.py

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import queue
import time
import os
import cv2
from PIL import Image, ImageTk
import numpy as np
import well_analyzer

class AnalysisTab(ttk.Frame):
    def __init__(self, parent, config, results_callback):
        super().__init__(parent)
        
        self.config = config
        self.results_callback = results_callback
        self.video_path = None
        self.results_queue = queue.Queue()

        # --- Video Playback State ---
        self.video_capture = None
        self.is_playing = False
        self.stop_playback_flag = threading.Event()
        self.current_frame = None
        self.total_frames = 0
        self.fps = 30
        self.frame_lock = threading.Lock()
        self.photo_image = None
        self.video_lock = threading.Lock()
        self._after_id = None

        # --- Layout ---
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=0)
        self.rowconfigure(0, weight=1)

        self.main_pane = ttk.PanedWindow(self, orient=tk.VERTICAL)
        self.main_pane.grid(row=0, column=0, sticky="nsew", padx=10, pady=(10,0))

        self.create_preview_section(self.main_pane)
        # The report section is no longer needed for display, but we'll leave a small placeholder
        placeholder_frame = ttk.LabelFrame(self.main_pane, text="Status", padding="10")
        self.main_pane.add(placeholder_frame, weight=1)
        self.status_label = ttk.Label(placeholder_frame, text="Run analysis to view results in the 'Results' tab.", anchor='center')
        self.status_label.pack(expand=True, fill='both')

        self.create_controls_section()
        self.connect_controls()

        self.progress_bar = ttk.Progressbar(self, orient='horizontal', mode='indeterminate')

    def create_preview_section(self, parent_pane):
        preview_frame = ttk.LabelFrame(parent_pane, text="Media Preview", padding="10")
        preview_frame.columnconfigure(0, weight=1); preview_frame.rowconfigure(0, weight=1)
        parent_pane.add(preview_frame, weight=3)
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

    def create_controls_section(self):
        controls_frame = ttk.LabelFrame(self, text="Analysis Controls", padding="10")
        controls_frame.grid(row=0, column=1, sticky="ns", padx=(0, 10), pady=10)
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
        sample_rate = int(self.sample_rate_spinbox.get())
        self.set_ui_state(tk.DISABLED)
        self.status_label.config(text="Analysis in progress... please wait.")
        self.progress_bar.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=(5,10))
        self.progress_bar.start()
        
        analysis_thread = threading.Thread(
            target=self._analysis_thread_worker, 
            args=(self.video_path, threshold, min_area, metric_mode, sample_rate), 
            daemon=True
        )
        analysis_thread.start()
        self.after(100, self.check_analysis_queue)

    def _analysis_thread_worker(self, video_path, threshold, min_area, metric_mode, sample_rate):
        """
        Calls the new orchestrator function and puts the entire result package in the queue.
        """
        try:
            results_package = well_analyzer.run_full_analysis(
                video_path, threshold, min_area, metric_mode, sample_rate
            )
            self.results_queue.put(results_package)
        except Exception as e:
            # Package the error to be handled by the main thread
            self.results_queue.put({"error": f"A critical error occurred in the analysis thread:\n{e}"})

    def check_analysis_queue(self):
        """
        Checks for the results package and passes it to the main window's callback.
        """
        try:
            result = self.results_queue.get_nowait()
            self.progress_bar.stop()
            self.progress_bar.grid_remove()
            self.set_ui_state(tk.NORMAL)
            self.status_label.config(text="Analysis complete. See 'Results' tab for details.")
            
            # Use the callback to send the full result package to the main window
            if self.results_callback:
                self.results_callback(result)
                
        except queue.Empty:
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
                with self.frame_lock: self.current_frame = frame
                self.display_current_frame()
                self.progress_slider.config(to=self.total_frames - 1)
            else:
                self.preview_label.config(text="Could not read first frame.", image='')
                return
        except Exception as e:
            messagebox.showerror("Error", f"Could not load video: {e}")
            self.clear_media()
            return
        self.set_ui_state(tk.NORMAL)
        self.play_pause_button.config(state=tk.NORMAL)
        self.progress_slider.config(state=tk.NORMAL)
        self.loop_video_checkbutton.config(state=tk.NORMAL)
        self.status_label.config(text="Video loaded. Adjust parameters and run analysis.")

    def clear_media(self):
        self.stop_playback()
        with self.video_lock:
            if self.video_capture: self.video_capture.release(); self.video_capture = None
        self.video_path = None
        self.preview_label.config(image='', text="Load a video to see a preview.")
        self.set_ui_state(tk.DISABLED)
        self.play_pause_button.config(text="▶ Play", state=tk.DISABLED)
        self.progress_slider.set(0)
        self.progress_slider.config(state=tk.DISABLED)
        self.loop_video_checkbutton.config(state=tk.DISABLED)
        self.status_label.config(text="Load a video to begin.")
        
    def toggle_play_pause(self):
        if self.is_playing:
            self.is_playing = False
            self.play_pause_button.config(text="▶ Play")
            if self._after_id: self.after_cancel(self._after_id); self._after_id = None
        else:
            self.is_playing = True
            self.play_pause_button.config(text="❚❚ Pause")
            if not self._after_id: self._after_id = self.after(int(1000 / self.fps), self.update_video_frame)

    def start_playback(self): pass # Playback is handled by the after loop now

    def stop_playback(self):
        self.is_playing = False
        if self._after_id: self.after_cancel(self._after_id); self._after_id = None
            
    def update_video_frame(self):
        if not self.is_playing: self._after_id = None; return
        ret = False
        with self.video_lock:
            if self.video_capture and self.video_capture.isOpened():
                ret, frame = self.video_capture.read()
        if ret:
            with self.frame_lock: self.current_frame = frame
            self.display_current_frame()
            current_pos = int(self.video_capture.get(cv2.CAP_PROP_POS_FRAMES))
            self.progress_slider.set(current_pos)
        else:
            if self.loop_video_var.get():
                self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
            else:
                self.is_playing = False; self.play_pause_button.config(text="▶ Play")
        if self.is_playing: self._after_id = self.after(int(1000 / self.fps), self.update_video_frame)

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
        if self.is_playing: return
        with self.video_lock:
            if self.video_capture and self.video_capture.isOpened():
                frame_num = int(float(value))
                self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
                ret, frame = self.video_capture.read()
                if ret:
                    with self.frame_lock: self.current_frame = frame
                    self.display_current_frame()
                    
    def cleanup(self): self.stop_playback()

    def set_ui_state(self, state):
        self.load_button.config(state=tk.NORMAL if state == tk.DISABLED else tk.DISABLED)
        video_loaded_state = tk.NORMAL if self.video_path and state == tk.NORMAL else tk.DISABLED
        self.clear_button.config(state=video_loaded_state)
        self.run_button.config(state=video_loaded_state)
        self.threshold_spinbox.config(state=state)
        self.min_area_spinbox.config(state=state)
        self.metric_selector.config(state="readonly" if state == tk.NORMAL else tk.DISABLED)
        self.sample_rate_spinbox.config(state=state)