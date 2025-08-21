# tabs/capture_tab.py
#
# The 'Capture' tab UI.
# FIX: Replaced cv2.convertScaleAbs with a robust NumPy-based method for
# brightness/contrast to prevent color inversion artifacts at low brightness.

import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import os
from datetime import datetime
import threading
import cv2
import numpy as np

from camera_handler import CameraHandler
from video_recorder import VideoRecorder

class CaptureTab(ttk.Frame):
    def __init__(self, parent, config, image_capture_callback):
        super().__init__(parent)
        
        self.config = config
        self.image_capture_callback = image_capture_callback
        self.camera = CameraHandler()
        self.recorder = None
        self.status_checker_id = None
        self.update_id = None

        self.brightness_var = tk.DoubleVar(value=0)
        self.contrast_var = tk.DoubleVar(value=1.0)

        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=0)
        self.rowconfigure(0, weight=1)

        self.create_camera_view()
        self.create_control_panel()
        self.connect_controls()
        
        self.populate_camera_list_async()

    def create_camera_view(self):
        camera_view_frame = ttk.LabelFrame(self, text="Camera Feed")
        camera_view_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        camera_view_frame.columnconfigure(0, weight=1)
        camera_view_frame.rowconfigure(0, weight=1)
        self.camera_label = ttk.Label(camera_view_frame, text="Camera is off.", anchor=tk.CENTER)
        self.camera_label.grid(row=0, column=0, sticky="nsew")
        self.camera_label.photo_image = None

    def create_control_panel(self):
        controls_frame = ttk.LabelFrame(self, text="Controls", padding="10")
        controls_frame.grid(row=0, column=1, sticky="ns", padx=10, pady=10)
        action_frame = ttk.Frame(controls_frame)
        action_frame.pack(fill=tk.X, pady=(0, 20))
        self.stream_button = ttk.Button(action_frame, text="Start Stream")
        self.stream_button.pack(side=tk.LEFT, padx=5, pady=5, expand=True, fill=tk.X)
        self.capture_button = ttk.Button(action_frame, text="Capture Image", state=tk.DISABLED)
        self.capture_button.pack(side=tk.LEFT, padx=5, pady=5, expand=True, fill=tk.X)
        self.record_button = ttk.Button(action_frame, text="Start Recording", state=tk.DISABLED)
        self.record_button.pack(side=tk.LEFT, padx=5, pady=5, expand=True, fill=tk.X)
        settings_frame = ttk.Frame(controls_frame)
        settings_frame.pack(fill=tk.X, anchor='n')
        settings_frame.columnconfigure(1, weight=1)

        row_counter = 0
        ttk.Label(settings_frame, text="Camera:").grid(row=row_counter, column=0, sticky="w", pady=5)
        self.camera_selector = ttk.Combobox(settings_frame, state="readonly")
        self.camera_selector.grid(row=row_counter, column=1, sticky="ew", padx=5); row_counter += 1

        ttk.Label(settings_frame, text="Resolution:").grid(row=row_counter, column=0, sticky="w", pady=5)
        self.resolution_selector = ttk.Combobox(settings_frame, values=["1280x720", "1920x1080", "640x480"], state="readonly")
        self.resolution_selector.set("1280x720")
        self.resolution_selector.grid(row=row_counter, column=1, sticky="ew", padx=5); row_counter += 1

        ttk.Label(settings_frame, text="Brightness:").grid(row=row_counter, column=0, sticky="w", pady=5)
        self.brightness_slider = ttk.Scale(
            settings_frame, from_=-100, to=100, orient=tk.HORIZONTAL,
            variable=self.brightness_var, state=tk.DISABLED
        )
        self.brightness_slider.grid(row=row_counter, column=1, sticky="ew", padx=5); row_counter += 1

        ttk.Label(settings_frame, text="Contrast:").grid(row=row_counter, column=0, sticky="w", pady=5)
        self.contrast_slider = ttk.Scale(
            settings_frame, from_=1.0, to=3.0, orient=tk.HORIZONTAL,
            variable=self.contrast_var, state=tk.DISABLED
        )
        self.contrast_slider.grid(row=row_counter, column=1, sticky="ew", padx=5); row_counter += 1


    def connect_controls(self):
        self.stream_button.config(command=self.toggle_stream)
        self.capture_button.config(command=self.capture_image_and_notify)
        self.record_button.config(command=self.toggle_recording)
        self.camera_selector.bind("<<ComboboxSelected>>", self.on_setting_change)
        self.resolution_selector.bind("<<ComboboxSelected>>", self.on_setting_change)

    def populate_camera_list_async(self):
        self.stream_button.config(state=tk.DISABLED)
        self.camera_selector.set("Scanning for cameras...")
        threading.Thread(target=self._camera_list_worker, daemon=True).start()

    def _camera_list_worker(self):
        available_cameras = self.camera.list_available_cameras()
        self.after(0, self._update_camera_list_ui, available_cameras)

    def _update_camera_list_ui(self, available_cameras):
        if not available_cameras:
            self.camera_selector.set("No cameras found")
            self.camera_selector.config(state=tk.DISABLED)
        else:
            self.camera_map = {name: index for index, name in available_cameras}
            self.camera_selector['values'] = [name for index, name in available_cameras]
            self.camera_selector.current(0)
            self.camera_selector.config(state="readonly")
            self.stream_button.config(state=tk.NORMAL)

    def on_setting_change(self, event=None):
        if self.camera.get_status() == CameraHandler.STATUS_RUNNING:
            self.camera_label.config(image='', text="Restarting Stream...")
            self.toggle_stream() # Stop
            self.after(100, self.toggle_stream) # Start again

    def toggle_stream(self):
        is_running = self.camera.get_status() != CameraHandler.STATUS_STOPPED
        
        if is_running:
            if self.update_id: self.after_cancel(self.update_id); self.update_id = None
            if self.status_checker_id: self.after_cancel(self.status_checker_id); self.status_checker_id = None
            if self.recorder and self.recorder.is_recording(): self.toggle_recording()
            self.camera.stop_stream()
            self.stream_button.config(text="Start Stream")
            self.capture_button.config(state=tk.DISABLED)
            self.record_button.config(state=tk.DISABLED)
            self.brightness_slider.config(state=tk.DISABLED)
            self.contrast_slider.config(state=tk.DISABLED)
            self.brightness_var.set(0)
            self.contrast_var.set(1.0)
            self.camera_label.config(image='', text="Camera is off.")
            self.camera_label.photo_image = None
            self.set_input_state(tk.NORMAL)
        else:
            selected_camera_name = self.camera_selector.get()
            if not selected_camera_name or "Scanning" in selected_camera_name or "No cameras" in selected_camera_name: return
            selected_camera_index = self.camera_map[selected_camera_name]
            res_str = self.resolution_selector.get()
            width, height = map(int, res_str.split('x'))
            self.camera.set_resolution(width, height)
            if self.camera.start_stream(camera_index=selected_camera_index):
                self.set_input_state(tk.DISABLED)
                self.stream_button.config(text="Initializing...", state=tk.DISABLED)
                self.camera_label.config(text="Initializing Camera...")
                self.status_checker_id = self.after(100, self.check_stream_status)
            else:
                messagebox.showerror("Camera Error", "Could not start camera thread.")

    def check_stream_status(self):
        status = self.camera.get_status()
        if status == CameraHandler.STATUS_RUNNING:
            self.stream_button.config(text="Stop Stream", state=tk.NORMAL)
            self.capture_button.config(state=tk.NORMAL)
            self.record_button.config(state=tk.NORMAL)
            self.brightness_slider.config(state=tk.NORMAL)
            self.contrast_slider.config(state=tk.NORMAL)
            self.status_checker_id = None
            self.update_frame()
            print("GUI: Stream is running. Starting frame updates.")
        elif status == CameraHandler.STATUS_ERROR:
            self.stream_button.config(text="Start Stream", state=tk.NORMAL)
            self.camera_label.config(image=None, text="Camera Error.")
            self.brightness_slider.config(state=tk.DISABLED)
            self.contrast_slider.config(state=tk.DISABLED)
            self.set_input_state(tk.NORMAL)
            self.status_checker_id = None
            messagebox.showerror("Camera Error", "Failed to open camera stream. Check connection and try a different resolution.")
        else:
            self.status_checker_id = self.after(100, self.check_stream_status)

    def set_input_state(self, state):
        widget_state = "readonly" if state == tk.NORMAL else tk.DISABLED
        self.camera_selector.config(state=widget_state)
        self.resolution_selector.config(state=widget_state)

    def update_frame(self):
        if self.camera.get_status() != CameraHandler.STATUS_RUNNING:
            return
        
        frame = self.camera.get_frame()
        if frame is not None:
            brightness = self.brightness_var.get()
            contrast = self.contrast_var.get()
            
            # <<< FIX: Use a robust method to apply brightness/contrast >>>
            # The previous method (cv2.convertScaleAbs) caused color inversion artifacts
            # because it takes the absolute value of the result.
            # This new method uses a wider data type for the calculation (int16) to
            # allow for temporary negative values, then clips the result to the
            # valid 0-255 range before converting back to uint8 for display.
            adjusted_frame = np.clip(frame.astype(np.int16) * contrast + brightness, 0, 255).astype(np.uint8)
            
            if self.recorder and self.recorder.is_recording():
                self.recorder.write_frame(adjusted_frame)
            
            img = Image.fromarray(adjusted_frame)
            lw, lh = self.camera_label.winfo_width(), self.camera_label.winfo_height()
            if lw > 1 and lh > 1:
                img.thumbnail((lw, lh), Image.Resampling.LANCZOS)
            
            photo_image = ImageTk.PhotoImage(image=img)
            self.camera_label.config(image=photo_image, text="")
            self.camera_label.photo_image = photo_image
        
        self.update_id = self.after(33, self.update_frame)

    def capture_image_and_notify(self):
        """
        Captures the current frame, applies brightness/contrast, saves it as a PNG, 
        and then notifies the main application with the file path.
        """
        image_data = self.camera.capture_image()
        if image_data is not None:
            try:
                brightness = self.brightness_var.get()
                contrast = self.contrast_var.get()

                # <<< FIX: Apply the same robust adjustment before saving the image >>>
                adjusted_image_data = np.clip(image_data.astype(np.int16) * contrast + brightness, 0, 255).astype(np.uint8)

                output_dir = "output/images"
                os.makedirs(output_dir, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                file_path = os.path.join(output_dir, f"capture_{timestamp}.png")

                img_to_save = Image.fromarray(adjusted_image_data)
                img_to_save.save(file_path)

                print(f"Image captured and saved to: {file_path}")
                self.image_capture_callback(file_path)

            except Exception as e:
                messagebox.showerror("Save Error", f"Failed to save image to file: {e}")
        else:
            messagebox.showwarning("Capture Failed", "Could not capture an image.")
            
    def toggle_recording(self):
        if self.recorder and self.recorder.is_recording():
            self.recorder.stop()
            self.recorder = None
            self.record_button.config(text="Start Recording")
            self.stream_button.config(state=tk.NORMAL)
        else:
            output_dir = "output/videos"
            os.makedirs(output_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = os.path.join(output_dir, f"rec_{timestamp}.mp4")
            frame_size = self.camera.get_frame_size()
            self.recorder = VideoRecorder(file_path, frame_size, fps=30)
            if self.recorder.start():
                self.record_button.config(text="Stop Recording")
                self.stream_button.config(state=tk.DISABLED)
            else:
                messagebox.showerror("Recording Error", "Could not start recorder.")
                self.recorder = None
            
    def cleanup(self):
        if self.update_id: self.after_cancel(self.update_id)
        if self.status_checker_id: self.after_cancel(self.status_checker_id)
        self.camera.stop_stream()
        if self.recorder and self.recorder.is_recording(): self.recorder.stop()