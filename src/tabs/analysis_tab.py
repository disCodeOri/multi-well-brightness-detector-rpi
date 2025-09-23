# tabs/analysis_tab.py

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import queue
import os
import cv2
from PIL import Image, ImageTk
import numpy as np
from collections import Counter
import well_analyzer

class AnalysisTab(ttk.Frame):
    def __init__(self, parent, config, results_callback):
        super().__init__(parent)
        
        self.config = config
        self.results_callback = results_callback
        self.media_path = None # Generic path for video or image
        self.is_image_mode = False # Flag to track media type
        
        self.results_queue = queue.Queue()
        self.calibration_queue = queue.Queue()
        self.background_level = 0
        self.cal_value_var = tk.StringVar(value="0")

        # Video-specific state
        self.video_capture = None
        self.is_playing = False
        self.total_frames = 0
        self.fps = 30
        self._after_id = None

        # General state for holding the currently displayed image/frame
        self.current_image = None
        self.frame_lock = threading.Lock()
        self.photo_image = None
        self.video_lock = threading.Lock()

        # --- Layout ---
        self.columnconfigure(0, weight=1); self.columnconfigure(1, weight=0)
        self.rowconfigure(0, weight=1)
        self.main_pane = ttk.PanedWindow(self, orient=tk.VERTICAL)
        self.main_pane.grid(row=0, column=0, sticky="nsew", padx=10, pady=(10,0))

        self.create_preview_section(self.main_pane)
        placeholder_frame = ttk.LabelFrame(self.main_pane, text="Status", padding="10")
        self.main_pane.add(placeholder_frame, weight=1)
        self.status_label = ttk.Label(placeholder_frame, text="Load a video or image to begin.", anchor='center')
        self.status_label.pack(expand=True, fill='both')
        self.create_controls_section()
        self.connect_controls()
        self.progress_bar = ttk.Progressbar(self, orient='horizontal', mode='indeterminate')

    def create_preview_section(self, parent_pane):
        # This function remains unchanged
        preview_frame = ttk.LabelFrame(parent_pane, text="Media Preview", padding="10")
        preview_frame.columnconfigure(0, weight=1); preview_frame.rowconfigure(0, weight=1)
        parent_pane.add(preview_frame, weight=3)
        self.preview_label = ttk.Label(preview_frame, text="Load a video or image to see a preview.", anchor=tk.CENTER)
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
        # This function remains unchanged
        controls_frame = ttk.LabelFrame(self, text="Analysis Controls", padding="10")
        controls_frame.grid(row=0, column=1, sticky="ns", padx=(0, 10), pady=10)
        action_frame = ttk.Frame(controls_frame, padding=(0, 0, 0, 10)); action_frame.pack(fill=tk.X)
        self.load_button = ttk.Button(action_frame, text="Load Media"); self.load_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))
        self.clear_button = ttk.Button(action_frame, text="Clear", state=tk.DISABLED); self.clear_button.pack(side=tk.LEFT, expand=True, fill=tk.X)
        cal_frame = ttk.LabelFrame(controls_frame, text="Background Calibration", padding="10"); cal_frame.pack(fill=tk.X, pady=(5, 15))
        self.calibrate_button = ttk.Button(cal_frame, text="Calibrate (Video Only)", state=tk.DISABLED, command=self.start_calibration); self.calibrate_button.pack(fill=tk.X, pady=(0, 10))
        cal_edit_frame = ttk.Frame(cal_frame); cal_edit_frame.pack(fill=tk.X); cal_edit_frame.columnconfigure(0, weight=1)
        ttk.Label(cal_edit_frame, text="Value:").grid(row=0, column=0, sticky="w")
        self.cal_value_spinbox = ttk.Spinbox(cal_edit_frame, from_=0, to=255, width=6, textvariable=self.cal_value_var, state="readonly"); self.cal_value_spinbox.grid(row=0, column=1, padx=5)
        self.cal_edit_button = ttk.Button(cal_edit_frame, text="Edit", width=6, state=tk.DISABLED, command=self.toggle_cal_value_edit); self.cal_edit_button.grid(row=0, column=2)
        settings_frame = ttk.Frame(controls_frame, padding=(0, 5, 0, 15)); settings_frame.pack(fill=tk.X); settings_frame.columnconfigure(1, weight=1)
        row_counter = 0
        ttk.Label(settings_frame, text="Min Well Area:").grid(row=row_counter, column=0, sticky="w", pady=5)
        self.min_area_spinbox = ttk.Spinbox(settings_frame, from_=10, to=1000, width=7); self.min_area_spinbox.set("100"); self.min_area_spinbox.grid(row=row_counter, column=1, sticky="ew", padx=5); row_counter += 1
        ttk.Label(settings_frame, text="Brightness Metric:").grid(row=row_counter, column=0, sticky="w", pady=5)
        self.metric_selector = ttk.Combobox(settings_frame, values=["Average Intensity", "Peak Intensity"], state="readonly"); self.metric_selector.current(0); self.metric_selector.grid(row=row_counter, column=1, sticky="ew", padx=5); row_counter += 1
        ttk.Label(settings_frame, text="Sample Rate (Video):").grid(row=row_counter, column=0, sticky="w", pady=5)
        self.sample_rate_spinbox = ttk.Spinbox(settings_frame, from_=1, to=100, width=7); self.sample_rate_spinbox.set("1"); self.sample_rate_spinbox.grid(row=row_counter, column=1, sticky="ew", padx=5); row_counter += 1
        self.run_button = ttk.Button(controls_frame, text="Run Analysis", state=tk.DISABLED); style = ttk.Style(); style.configure('Accent.TButton', font=('TkDefaultFont', 10, 'bold')); self.run_button.config(style='Accent.TButton'); self.run_button.pack(fill=tk.X, pady=(10, 0))

    def connect_controls(self):
        # This function remains unchanged
        self.load_button.config(command=self.load_media)
        self.clear_button.config(command=self.clear_media)
        self.run_button.config(command=self.start_analysis)
        
    def load_media(self):
        # --- MODIFIED to accept both image and video files ---
        filetypes = (
            ("All Media Files", "*.mp4 *.avi *.mov *.png *.jpg *.jpeg *.bmp"),
            ("Video Files", "*.mp4 *.avi *.mov"),
            ("Image Files", "*.png *.jpg *.jpeg *.bmp")
        )
        filepath = filedialog.askopenfilename(title="Select a Media File", filetypes=filetypes)
        if not filepath: return
        
        self.clear_media()
        self.media_path = filepath
        file_ext = os.path.splitext(self.media_path)[1].lower()

        try:
            if file_ext in ['.mp4', '.avi', '.mov']:
                self.is_image_mode = False
                with self.video_lock:
                    self.video_capture = cv2.VideoCapture(self.media_path)
                    if not self.video_capture.isOpened(): raise IOError("Cannot open video file")
                    self.total_frames = int(self.video_capture.get(cv2.CAP_PROP_FRAME_COUNT))
                    self.fps = self.video_capture.get(cv2.CAP_PROP_FPS); self.fps = self.fps if self.fps > 0 else 30
                    ret, frame = self.video_capture.read()
                if ret:
                    with self.frame_lock: self.current_image = frame
                    self.display_current_frame(); self.progress_slider.config(to=self.total_frames - 1)
                else: raise IOError("Could not read first frame of video.")
            
            elif file_ext in ['.png', '.jpg', '.jpeg', '.bmp']:
                self.is_image_mode = True
                frame = cv2.imread(self.media_path)
                if frame is None: raise IOError("Could not read image file.")
                with self.frame_lock: self.current_image = frame
                self.display_current_frame()

            else:
                raise TypeError(f"Unsupported file type: {file_ext}")

        except Exception as e:
            messagebox.showerror("Error", f"Could not load media: {e}"); self.clear_media(); return

        self.set_ui_state(tk.NORMAL)
        self.status_label.config(text="Media loaded. Calibrate background, then run analysis.")

    def start_analysis(self):
        if not self.media_path: messagebox.showerror("Error", "No media file loaded."); return
        if self.is_playing: self.toggle_play_pause()
        
        try:
            self.background_level = int(self.cal_value_var.get())
        except (ValueError, tk.TclError):
            messagebox.showerror("Invalid Value", "Calibration value must be a number."); return

        min_area = int(self.min_area_spinbox.get())
        metric_str = self.metric_selector.get()
        metric_mode = 'peak' if metric_str == "Peak Intensity" else 'average'
        
        self.set_ui_state(tk.DISABLED)
        self.status_label.config(text="Analysis in progress... please wait.")
        self.progress_bar.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=(5,10)); self.progress_bar.start()
        
        # --- MODIFIED: Choose worker based on media type ---
        if self.is_image_mode:
            thread_target = self._image_analysis_thread_worker
            thread_args = (self.media_path, self.background_level, min_area, metric_mode)
        else: # Is video mode
            sample_rate = int(self.sample_rate_spinbox.get())
            thread_target = self._video_analysis_thread_worker
            thread_args = (self.media_path, self.background_level, min_area, metric_mode, sample_rate)

        analysis_thread = threading.Thread(target=thread_target, args=thread_args, daemon=True)
        analysis_thread.start()
        self.after(100, self.check_analysis_queue)

    def _video_analysis_thread_worker(self, video_path, background_level, min_area, metric_mode, sample_rate):
        """Worker for video analysis."""
        try:
            results_package = well_analyzer.run_full_analysis(video_path, background_level, min_area, metric_mode, sample_rate)
            self.results_queue.put(results_package)
        except Exception as e:
            self.results_queue.put({"error": f"A critical error occurred: {e}"})

    def _image_analysis_thread_worker(self, image_path, background_level, min_area, metric_mode):
        """--- NEW worker for single images ---"""
        try:
            results_package = well_analyzer.run_single_image_analysis(image_path, background_level, min_area, metric_mode)
            self.results_queue.put(results_package)
        except Exception as e:
            self.results_queue.put({"error": f"A critical error occurred: {e}"})

    def clear_media(self):
        self.stop_playback()
        with self.video_lock:
            if self.video_capture: self.video_capture.release(); self.video_capture = None
        self.media_path = None; self.is_image_mode = False; self.current_image = None
        self.background_level = 0; self.cal_value_var.set("0")
        self.preview_label.config(image='', text="Load a video or image to see a preview.")
        self.set_ui_state(tk.DISABLED)
        self.status_label.config(text="Load a video or image to begin.")

    def set_ui_state(self, state):
        # --- MODIFIED to handle image vs. video mode ---
        self.load_button.config(state=tk.NORMAL if state == tk.DISABLED else tk.DISABLED)
        media_loaded_state = tk.NORMAL if self.media_path and state == tk.NORMAL else tk.DISABLED
        
        # General controls
        self.clear_button.config(state=media_loaded_state)
        self.run_button.config(state=media_loaded_state)
        self.cal_edit_button.config(state=media_loaded_state)
        self.min_area_spinbox.config(state=state)
        self.metric_selector.config(state="readonly" if state == tk.NORMAL else tk.DISABLED)
        
        # Video-specific controls (enabled only if media is loaded AND it's a video)
        is_video = media_loaded_state == tk.NORMAL and not self.is_image_mode
        self.play_pause_button.config(state=tk.NORMAL if is_video else tk.DISABLED)
        self.progress_slider.config(state=tk.NORMAL if is_video else tk.DISABLED)
        self.loop_video_checkbutton.config(state=tk.NORMAL if is_video else tk.DISABLED)
        self.sample_rate_spinbox.config(state=tk.NORMAL if is_video else tk.DISABLED)
        self.calibrate_button.config(state=tk.NORMAL if is_video else tk.DISABLED)

    def display_current_frame(self):
        with self.frame_lock:
            if self.current_image is None: return
            frame_to_show = cv2.cvtColor(self.current_image, cv2.COLOR_BGR2RGB)
        
        self.preview_label.update_idletasks()
        lw, lh = self.preview_label.winfo_width(), self.preview_label.winfo_height()
        if lw > 1 and lh > 1:
            img_pil = Image.fromarray(frame_to_show)
            img_pil.thumbnail((lw, lh), Image.Resampling.LANCZOS)
            self.photo_image = ImageTk.PhotoImage(image=img_pil); self.preview_label.config(image=self.photo_image)

    # --- No changes to the functions below, they remain as they were ---
    def check_analysis_queue(self):
        try:
            result = self.results_queue.get_nowait(); self.progress_bar.stop(); self.progress_bar.grid_remove()
            self.set_ui_state(tk.NORMAL); self.status_label.config(text="Analysis complete. See 'Results' tab.")
            if self.results_callback: self.results_callback(result)
        except queue.Empty: self.after(100, self.check_analysis_queue)
    def toggle_cal_value_edit(self):
        if self.cal_value_spinbox.cget('state') == 'readonly': self.cal_value_spinbox.config(state=tk.NORMAL); self.cal_edit_button.config(text="Lock")
        else:
            try:
                new_val = int(self.cal_value_var.get());
                if not (0 <= new_val <= 255): raise ValueError
                self.background_level = new_val; self.cal_value_spinbox.config(state="readonly"); self.cal_edit_button.config(text="Edit")
                self.status_label.config(text=f"Manual calibration value set to {self.background_level}.")
            except (ValueError, tk.TclError): messagebox.showerror("Invalid Input", "Please enter a whole number between 0 and 255."); self.cal_value_var.set(str(self.background_level))
    def start_calibration(self):
        if self.is_playing: self.toggle_play_pause()
        instructions = ("Calibrate background level?\n\nPlease ensure:\n  1. The well plate holder is closed.\n  2. There are no active or glowing wells.\n\nClick OK to analyze the first few seconds of the video.")
        if messagebox.askokcancel("Calibration Instructions", instructions):
            self.status_label.config(text="Calibrating background level..."); self.set_ui_state(tk.DISABLED)
            cal_thread = threading.Thread(target=self._calibration_worker, daemon=True); cal_thread.start(); self.after(100, self.check_calibration_queue)
    def _calibration_worker(self):
        try:
            with self.video_lock:
                if not self.video_capture or not self.video_capture.isOpened(): self.calibration_queue.put({'error': "Video is not loaded."}); return
                self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
            mode_values = []; num_frames_to_check = min(150, int(self.fps * 5))
            for _ in range(num_frames_to_check):
                with self.video_lock: ret, frame = self.video_capture.read()
                if not ret: break
                gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY); hist = cv2.calcHist([gray_frame], [0], None, [256], [0, 256]); mode_values.append(np.argmax(hist))
            if not mode_values: self.calibration_queue.put({'error': "Could not read frames for calibration."}); return
            final_background_level = Counter(mode_values).most_common(1)[0][0]; self.calibration_queue.put({'level': final_background_level})
        except Exception as e: self.calibration_queue.put({'error': f"Calibration failed: {e}"})
    def check_calibration_queue(self):
        try:
            result = self.calibration_queue.get_nowait(); self.set_ui_state(tk.NORMAL)
            if 'error' in result and result['error']: messagebox.showerror("Calibration Error", result['error']); self.status_label.config(text="Calibration failed.")
            else: self.background_level = result['level']; self.cal_value_var.set(str(self.background_level)); self.status_label.config(text="Calibration complete."); messagebox.showinfo("Success", f"Calibration complete. Background level set to {self.background_level}.")
        except queue.Empty: self.after(100, self.check_calibration_queue)
    def toggle_play_pause(self):
        if self.is_playing: self.is_playing = False; self.play_pause_button.config(text="▶ Play");
        else: self.is_playing = True; self.play_pause_button.config(text="❚❚ Pause"); self.update_video_frame()
    def stop_playback(self):
        self.is_playing = False;
        if self._after_id: self.after_cancel(self._after_id); self._after_id = None
    def update_video_frame(self):
        if not self.is_playing: self._after_id = None; return
        ret, frame = False, None
        with self.video_lock:
            if self.video_capture and self.video_capture.isOpened(): ret, frame = self.video_capture.read()
        if ret:
            with self.frame_lock: self.current_image = frame
            self.display_current_frame(); self.progress_slider.set(int(self.video_capture.get(cv2.CAP_PROP_POS_FRAMES)))
        elif self.loop_video_var.get(): self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
        else: self.is_playing = False; self.play_pause_button.config(text="▶ Play")
        if self.is_playing: self._after_id = self.after(int(1000 / self.fps), self.update_video_frame)
    def on_slider_move(self, value):
        if self.is_playing: return
        with self.video_lock:
            if self.video_capture and self.video_capture.isOpened():
                frame_num = int(float(value)); self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
                ret, frame = self.video_capture.read()
                if ret:
                    with self.frame_lock:
                        self.current_image = frame
                    self.display_current_frame()
    def cleanup(self): self.stop_playback()