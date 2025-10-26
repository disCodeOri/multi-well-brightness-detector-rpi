# src/tabs/capture_tab.py

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
from PIL import Image, ImageTk
import os
from datetime import datetime
import threading
import json
import cv2
import numpy as np

from camera_handler import CameraHandler
from video_recorder import VideoRecorder
from interval_scheduler import IntervalScheduler

class IntervalDialog(tk.Toplevel):
    """Dialog for creating and managing complex interval patterns."""
    def __init__(self, parent, config):
        super().__init__(parent)
        self.title("Configure Intervals")
        self.config = config
        self.result = None
        self.transient(parent)
        self.grab_set()

        self.phases = config.get("phases", [])
        
        self.create_widgets()
        self.populate_tree()
        self.update_total_time()
        
        self.protocol("WM_DELETE_WINDOW", self.cancel)
        self.wait_window(self)

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(expand=True, fill=tk.BOTH)

        tree_frame = ttk.Frame(main_frame)
        tree_frame.pack(expand=True, fill=tk.BOTH, pady=(0, 10))
        
        self.tree = ttk.Treeview(tree_frame, columns=("Name", "Action", "Duration"), show="headings")
        self.tree.heading("Name", text="Name")
        self.tree.heading("Action", text="Action")
        self.tree.heading("Duration", text="Duration (s)")
        self.tree.column("Duration", width=100, anchor=tk.CENTER)
        self.tree.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=5)
        
        btn_add = ttk.Button(button_frame, text="Add", command=self.add_phase)
        btn_add.pack(side=tk.LEFT, padx=2)
        btn_edit = ttk.Button(button_frame, text="Edit", command=self.edit_phase)
        btn_edit.pack(side=tk.LEFT, padx=2)
        btn_del = ttk.Button(button_frame, text="Delete", command=self.delete_phase)
        btn_del.pack(side=tk.LEFT, padx=2)
        btn_up = ttk.Button(button_frame, text="Move Up", command=lambda: self.move_phase(-1))
        btn_up.pack(side=tk.LEFT, padx=(10, 2))
        btn_down = ttk.Button(button_frame, text="Move Down", command=lambda: self.move_phase(1))
        btn_down.pack(side=tk.LEFT, padx=2)

        repeat_frame = ttk.Frame(main_frame)
        repeat_frame.pack(fill=tk.X, pady=10)
        ttk.Label(repeat_frame, text="Repeat Count (0 = infinite):").pack(side=tk.LEFT)
        self.repeat_spinbox = ttk.Spinbox(repeat_frame, from_=0, to=9999, width=7)
        self.repeat_spinbox.set(self.config.get("repeat_count", 0))
        self.repeat_spinbox.pack(side=tk.LEFT, padx=5)
        
        self.total_time_label = ttk.Label(repeat_frame, text="Total time per cycle: 0s")
        self.total_time_label.pack(side=tk.RIGHT, padx=5)

        file_frame = ttk.Frame(main_frame)
        file_frame.pack(fill=tk.X, pady=5)
        btn_load = ttk.Button(file_frame, text="Load Pattern...", command=self.load_pattern)
        btn_load.pack(side=tk.LEFT, padx=2)
        btn_save = ttk.Button(file_frame, text="Save Pattern...", command=self.save_pattern)
        btn_save.pack(side=tk.LEFT, padx=2)

        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill=tk.X, pady=(10, 0))
        btn_ok = ttk.Button(action_frame, text="Save", command=self.save_config)
        btn_ok.pack(side=tk.RIGHT, padx=2)
        btn_cancel = ttk.Button(action_frame, text="Cancel", command=self.cancel)
        btn_cancel.pack(side=tk.RIGHT, padx=2)

    def populate_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for phase in self.phases:
            self.tree.insert('', tk.END, values=(phase['name'], phase['action'], phase['duration']))

    def add_phase(self):
        dialog = PhaseDialog(self)
        if dialog.result:
            self.phases.append(dialog.result)
            self.populate_tree()
            self.update_total_time()

    def edit_phase(self):
        selected = self.tree.selection()
        if not selected: return
        
        index = self.tree.index(selected[0])
        phase_data = self.phases[index]
        
        dialog = PhaseDialog(self, phase_data)
        if dialog.result:
            self.phases[index] = dialog.result
            self.populate_tree()
            self.update_total_time()

    def delete_phase(self):
        selected = self.tree.selection()
        if not selected: return
        if messagebox.askyesno("Confirm", "Are you sure you want to delete the selected phase?"):
            index = self.tree.index(selected[0])
            del self.phases[index]
            self.populate_tree()
            self.update_total_time()

    def move_phase(self, direction):
        selected = self.tree.selection()
        if not selected: return
        
        index = self.tree.index(selected[0])
        new_index = index + direction
        
        if 0 <= new_index < len(self.phases):
            self.phases.insert(new_index, self.phases.pop(index))
            self.populate_tree()
            new_item_id = self.tree.get_children()[new_index]
            self.tree.selection_set(new_item_id)

    def update_total_time(self):
        total_seconds = sum(p.get('duration', 0) for p in self.phases)
        m, s = divmod(total_seconds, 60)
        h, m = divmod(m, 60)
        self.total_time_label.config(text=f"Total time per cycle: {h:02d}:{m:02d}:{s:02d}")

    def save_config(self):
        self.result = {
            "phases": self.phases,
            "repeat_count": int(self.repeat_spinbox.get())
        }
        self.destroy()
        
    def cancel(self):
        self.result = None
        self.destroy()

    def load_pattern(self):
        filepath = filedialog.askopenfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            title="Load Interval Pattern"
        )
        if not filepath: return
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            if "phases" in data and "repeat_count" in data:
                self.phases = data["phases"]
                self.repeat_spinbox.set(data["repeat_count"])
                self.populate_tree()
                self.update_total_time()
            else:
                messagebox.showerror("Error", "Invalid pattern file format.")
        except Exception as e:
            messagebox.showerror("Error", f"Could not load file: {e}")

    def save_pattern(self):
        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            title="Save Interval Pattern"
        )
        if not filepath: return
        try:
            pattern_data = {
                "phases": self.phases,
                "repeat_count": int(self.repeat_spinbox.get())
            }
            with open(filepath, 'w') as f:
                json.dump(pattern_data, f, indent=4)
            messagebox.showinfo("Success", "Pattern saved successfully.")
        except Exception as e:
            messagebox.showerror("Error", f"Could not save file: {e}")

class PhaseDialog(tk.Toplevel):
    """Sub-dialog for adding/editing a single phase."""
    def __init__(self, parent, phase=None):
        super().__init__(parent)
        self.title("Edit Phase" if phase else "Add Phase")
        self.result = None
        self.transient(parent)
        self.grab_set()

        self.name_var = tk.StringVar()
        self.action_var = tk.StringVar()
        self.duration_var = tk.IntVar()

        if phase:
            self.name_var.set(phase.get("name", ""))
            self.action_var.set(phase.get("action", "Wait"))
            self.duration_var.set(phase.get("duration", 60))

        self.create_widgets()
        self.protocol("WM_DELETE_WINDOW", self.cancel)
        self.wait_window(self)
        
    def create_widgets(self):
        frame = ttk.Frame(self, padding="10")
        frame.pack(expand=True, fill=tk.BOTH)
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="Name:").grid(row=0, column=0, sticky="w", pady=5)
        name_entry = ttk.Entry(frame, textvariable=self.name_var)
        name_entry.grid(row=0, column=1, sticky="ew", padx=5)

        ttk.Label(frame, text="Action:").grid(row=1, column=0, sticky="w", pady=5)
        action_combo = ttk.Combobox(frame, textvariable=self.action_var, values=["Record", "Wait"], state="readonly")
        action_combo.grid(row=1, column=1, sticky="ew", padx=5)
        action_combo.set("Record" if not self.action_var.get() else self.action_var.get())

        ttk.Label(frame, text="Duration (s):").grid(row=2, column=0, sticky="w", pady=5)
        duration_spinbox = ttk.Spinbox(frame, from_=1, to=86400, textvariable=self.duration_var, width=10)
        duration_spinbox.grid(row=2, column=1, sticky="w", padx=5)
        if not self.duration_var.get(): self.duration_var.set(10)

        button_frame = ttk.Frame(frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=(10, 0))
        ttk.Button(button_frame, text="OK", command=self.ok).pack(side=tk.RIGHT, padx=2)
        ttk.Button(button_frame, text="Cancel", command=self.cancel).pack(side=tk.RIGHT)

    def ok(self):
        self.result = {
            "name": self.name_var.get() or "Untitled Phase",
            "action": self.action_var.get(),
            "duration": self.duration_var.get()
        }
        self.destroy()

    def cancel(self):
        self.result = None
        self.destroy()

class CaptureTab(ttk.Frame):
    def __init__(self, parent, config, image_capture_callback):
        super().__init__(parent)
        
        self.config = config
        self.image_capture_callback = image_capture_callback
        self.camera = CameraHandler()
        self.recorder = None
        self.status_checker_id = None
        self.update_id = None
        self.scheduler = None
        self.is_interval_recording = False

        self.brightness_var = tk.DoubleVar(value=0)
        self.contrast_var = tk.DoubleVar(value=1.0)
        
        self.interval_config = {
           "phases": [{"name": "Record", "action": "Record", "duration": 10}, {"name": "Wait", "action": "Wait", "duration": 50}],
           "repeat_count": 0
        }

        self.columnconfigure(0, weight=1); self.columnconfigure(1, weight=0); self.rowconfigure(0, weight=1)
        self.create_camera_view(); self.create_control_panel(); self.connect_controls()
        self.populate_camera_list_async()

    def create_camera_view(self):
        camera_view_frame = ttk.LabelFrame(self, text="Camera Feed")
        camera_view_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        camera_view_frame.columnconfigure(0, weight=1); camera_view_frame.rowconfigure(0, weight=1)
        self.camera_label = ttk.Label(camera_view_frame, text="Camera is off.", anchor=tk.CENTER)
        self.camera_label.grid(row=0, column=0, sticky="nsew")
        self.camera_label.photo_image = None
        self.interval_status_label = ttk.Label(camera_view_frame, text="", background="black", foreground="white", padding=5, font=('TkDefaultFont', 10, 'bold'))

    def create_control_panel(self):
        controls_frame = ttk.LabelFrame(self, text="Controls", padding="10")
        controls_frame.grid(row=0, column=1, sticky="ns", padx=10, pady=10)
        
        manual_frame = ttk.LabelFrame(controls_frame, text="Manual Control", padding=10)
        manual_frame.pack(fill=tk.X, pady=(0, 10))
        action_frame = ttk.Frame(manual_frame); action_frame.pack(fill=tk.X, pady=(0, 10))
        self.stream_button = ttk.Button(action_frame, text="Start Stream"); self.stream_button.pack(side=tk.LEFT, padx=5, pady=5, expand=True, fill=tk.X)
        self.capture_button = ttk.Button(action_frame, text="Capture Image", state=tk.DISABLED); self.capture_button.pack(side=tk.LEFT, padx=5, pady=5, expand=True, fill=tk.X)
        self.record_button = ttk.Button(action_frame, text="Start Recording", state=tk.DISABLED); self.record_button.pack(side=tk.LEFT, padx=5, pady=5, expand=True, fill=tk.X)
        
        interval_frame = ttk.LabelFrame(controls_frame, text="Interval Recording", padding=10)
        interval_frame.pack(fill=tk.X, pady=10)
        self.interval_button = ttk.Button(interval_frame, text="Start Interval Recording", state=tk.DISABLED, command=self.toggle_interval_recording); self.interval_button.pack(fill=tk.X, pady=5)
        self.configure_intervals_button = ttk.Button(interval_frame, text="Configure Intervals...", command=self.configure_intervals); self.configure_intervals_button.pack(fill=tk.X, pady=5)
        self.interval_status_frame = ttk.Frame(interval_frame, padding=5); self.interval_status_frame.columnconfigure(1, weight=1)
        ttk.Label(self.interval_status_frame, text="Phase:").grid(row=0, column=0, sticky='w'); self.phase_label = ttk.Label(self.interval_status_frame, text="N/A"); self.phase_label.grid(row=0, column=1, sticky='w')
        ttk.Label(self.interval_status_frame, text="Time Left:").grid(row=1, column=0, sticky='w'); self.time_label = ttk.Label(self.interval_status_frame, text="00:00"); self.time_label.grid(row=1, column=1, sticky='w')
        ttk.Label(self.interval_status_frame, text="Cycle:").grid(row=2, column=0, sticky='w'); self.cycle_label = ttk.Label(self.interval_status_frame, text="0 / 0"); self.cycle_label.grid(row=2, column=1, sticky='w')
        
        settings_frame = ttk.LabelFrame(controls_frame, text="Camera Settings", padding="10")
        settings_frame.pack(fill=tk.X, pady=10, anchor='n'); settings_frame.columnconfigure(1, weight=1)
        row_counter = 0
        ttk.Label(settings_frame, text="Camera:").grid(row=row_counter, column=0, sticky="w", pady=5)
        self.camera_selector = ttk.Combobox(settings_frame, state="readonly"); self.camera_selector.grid(row=row_counter, column=1, sticky="ew", padx=5); row_counter += 1
        ttk.Label(settings_frame, text="Resolution:").grid(row=row_counter, column=0, sticky="w", pady=5)
        self.resolution_selector = ttk.Combobox(settings_frame, values=["1280x720", "1920x1080", "640x480"], state="readonly"); self.resolution_selector.set("1280x720"); self.resolution_selector.grid(row=row_counter, column=1, sticky="ew", padx=5); row_counter += 1
        
        ttk.Label(settings_frame, text="Brightness:").grid(row=row_counter, column=0, sticky="w", pady=5)
        self.brightness_slider = ttk.Scale(settings_frame, from_=-100, to=100, orient=tk.HORIZONTAL, variable=self.brightness_var, state=tk.DISABLED); self.brightness_slider.grid(row=row_counter, column=1, sticky="ew", padx=5); row_counter += 1
        ttk.Label(settings_frame, text="Contrast:").grid(row=row_counter, column=0, sticky="w", pady=5)
        self.contrast_slider = ttk.Scale(settings_frame, from_=1.0, to=3.0, orient=tk.HORIZONTAL, variable=self.contrast_var, state=tk.DISABLED); self.contrast_slider.grid(row=row_counter, column=1, sticky="ew", padx=5); row_counter += 1

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
            self.camera_selector.set("No cameras found"); self.camera_selector.config(state=tk.DISABLED)
        else:
            self.camera_map = {name: index for index, name in available_cameras}
            self.camera_selector['values'] = [name for index, name in available_cameras]; self.camera_selector.current(0)
            self.camera_selector.config(state="readonly"); self.stream_button.config(state=tk.NORMAL)

    def on_setting_change(self, event=None):
        if self.camera.get_status() == CameraHandler.STATUS_RUNNING:
            self.camera_label.config(image='', text="Restarting Stream...")
            self.toggle_stream(); self.after(100, self.toggle_stream)

    def toggle_stream(self):
        is_running = self.camera.get_status() != CameraHandler.STATUS_STOPPED
        if is_running:
            if self.is_interval_recording: self.stop_interval_recording_logic()
            if self.update_id: self.after_cancel(self.update_id); self.update_id = None
            if self.status_checker_id: self.after_cancel(self.status_checker_id); self.status_checker_id = None
            if self.recorder and self.recorder.is_recording(): self.toggle_recording()
            self.camera.stop_stream()
            self.stream_button.config(text="Start Stream")
            self.capture_button.config(state=tk.DISABLED); self.record_button.config(state=tk.DISABLED); self.interval_button.config(state=tk.DISABLED)
            self.brightness_slider.config(state=tk.DISABLED); self.contrast_slider.config(state=tk.DISABLED)
            self.brightness_var.set(0); self.contrast_var.set(1.0)
            self.camera_label.config(image='', text="Camera is off."); self.camera_label.photo_image = None
            self.set_input_state(tk.NORMAL)
        else:
            selected_camera_name = self.camera_selector.get()
            if not selected_camera_name or "Scanning" in selected_camera_name or "No cameras" in selected_camera_name: return
            selected_camera_index = self.camera_map[selected_camera_name]
            res_str = self.resolution_selector.get(); width, height = map(int, res_str.split('x'))
            self.camera.set_resolution(width, height)
            if self.camera.start_stream(camera_index=selected_camera_index):
                self.set_input_state(tk.DISABLED); self.stream_button.config(text="Initializing...", state=tk.DISABLED)
                self.camera_label.config(text="Initializing Camera...")
                self.status_checker_id = self.after(100, self.check_stream_status)
            else: messagebox.showerror("Camera Error", "Could not start camera thread.")

    def check_stream_status(self):
        status = self.camera.get_status()
        if status == CameraHandler.STATUS_RUNNING:
            self.stream_button.config(text="Stop Stream", state=tk.NORMAL); self.capture_button.config(state=tk.NORMAL)
            self.record_button.config(state=tk.NORMAL); self.interval_button.config(state=tk.NORMAL)
            self.brightness_slider.config(state=tk.NORMAL); self.contrast_slider.config(state=tk.NORMAL)
            self.status_checker_id = None; self.update_frame(); print("GUI: Stream is running. Starting frame updates.")
        elif status == CameraHandler.STATUS_ERROR:
            self.stream_button.config(text="Start Stream", state=tk.NORMAL); self.camera_label.config(image=None, text="Camera Error.")
            self.brightness_slider.config(state=tk.DISABLED); self.contrast_slider.config(state=tk.DISABLED)
            self.set_input_state(tk.NORMAL); self.status_checker_id = None
            messagebox.showerror("Camera Error", "Failed to open camera stream. Check connection and try a different resolution.")
        else: self.status_checker_id = self.after(100, self.check_stream_status)

    def set_input_state(self, state, is_interval=False):
        widget_state = "readonly" if state == tk.NORMAL else tk.DISABLED
        self.camera_selector.config(state=widget_state); self.resolution_selector.config(state=widget_state)
        if is_interval:
            self.stream_button.config(state=tk.DISABLED); self.capture_button.config(state=tk.DISABLED)
            self.record_button.config(state=tk.DISABLED); self.configure_intervals_button.config(state=tk.DISABLED)
        else:
            self.stream_button.config(state=tk.NORMAL if self.camera.get_status() != CameraHandler.STATUS_STOPPED else state)
            self.capture_button.config(state=tk.DISABLED if self.camera.get_status() == CameraHandler.STATUS_STOPPED else tk.NORMAL)
            self.record_button.config(state=tk.DISABLED if self.camera.get_status() == CameraHandler.STATUS_STOPPED else tk.NORMAL)
            self.configure_intervals_button.config(state=state)

    def update_frame(self):
        if self.camera.get_status() != CameraHandler.STATUS_RUNNING: return
        frame = self.camera.get_frame()
        if frame is not None:
            brightness = self.brightness_var.get(); contrast = self.contrast_var.get()
            adjusted_frame = np.clip(frame.astype(np.int16) * contrast + brightness, 0, 255).astype(np.uint8)
            if self.recorder and self.recorder.is_recording(): self.recorder.write_frame(adjusted_frame)
            img = Image.fromarray(adjusted_frame)
            lw, lh = self.camera_label.winfo_width(), self.camera_label.winfo_height()
            if lw > 1 and lh > 1: img.thumbnail((lw, lh), Image.Resampling.LANCZOS)
            photo_image = ImageTk.PhotoImage(image=img)
            self.camera_label.config(image=photo_image, text=""); self.camera_label.photo_image = photo_image
        delay = max(15, int(1000 / self.camera.get_fps()))
        self.update_id = self.after(delay, self.update_frame)

    def capture_image_and_notify(self):
        image_data = self.camera.capture_image()
        if image_data is not None:
            try:
                brightness = self.brightness_var.get(); contrast = self.contrast_var.get()
                adjusted_image_data = np.clip(image_data.astype(np.int16) * contrast + brightness, 0, 255).astype(np.uint8)
                output_dir = "output/images"; os.makedirs(output_dir, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                file_path = os.path.join(output_dir, f"capture_{timestamp}.png")
                Image.fromarray(adjusted_image_data).save(file_path)
                print(f"Image captured and saved to: {file_path}"); self.image_capture_callback(file_path)
            except Exception as e: messagebox.showerror("Save Error", f"Failed to save image: {e}")
        else: messagebox.showwarning("Capture Failed", "Could not capture an image.")
            
    def toggle_recording(self):
        if self.recorder and self.recorder.is_recording():
            self.recorder.stop(); self.recorder = None
            self.record_button.config(text="Start Recording"); self.stream_button.config(state=tk.NORMAL); self.interval_button.config(state=tk.NORMAL)
        else:
            output_dir = "output/videos"; os.makedirs(output_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S"); file_path = os.path.join(output_dir, f"rec_{timestamp}.mp4")
            frame_size = self.camera.get_frame_size()
            fps = self.camera.get_fps()
            self.recorder = VideoRecorder(file_path, frame_size, fps=fps)
            if self.recorder.start():
                self.record_button.config(text="Stop Recording"); self.stream_button.config(state=tk.DISABLED); self.interval_button.config(state=tk.DISABLED)
            else: messagebox.showerror("Recording Error", "Could not start recorder."); self.recorder = None
                
    def configure_intervals(self):
        dialog = IntervalDialog(self, self.interval_config)
        if dialog.result: self.interval_config = dialog.result; print("Interval configuration updated.")

    def toggle_interval_recording(self):
        if self.is_interval_recording: self.stop_interval_recording_logic()
        else: self.start_interval_recording_logic()

    def start_interval_recording_logic(self):
        if not self.interval_config.get("phases"): messagebox.showwarning("Warning", "No phases configured."); return
        self.is_interval_recording = True
        self.interval_button.config(text="Stop Interval Recording"); self.set_input_state(tk.DISABLED, is_interval=True)
        self.interval_status_frame.pack(fill=tk.X, pady=5); self.interval_status_label.place(relx=0.0, rely=1.0, anchor='sw')
        callbacks = {'on_phase_change': self.on_phase_change, 'on_tick': self.on_tick, 'on_complete': self.on_complete, 'on_error': self.on_error}
        self.scheduler = IntervalScheduler(self.interval_config, callbacks); self.scheduler.start()

    def stop_interval_recording_logic(self):
        if self.scheduler: self.scheduler.stop(); self.scheduler.join(); self.scheduler = None
        if self.recorder and self.recorder.is_recording(): self.recorder.stop(); self.recorder = None
        self.is_interval_recording = False
        self.interval_button.config(text="Start Interval Recording"); self.set_input_state(tk.NORMAL, is_interval=False)
        self.interval_status_frame.pack_forget(); self.interval_status_label.place_forget(); print("Interval recording stopped by user.")

    def on_phase_change(self, phase_name, duration, cycle_num, repeat_count, action):
        def _update_ui():
            if self.recorder and self.recorder.is_recording(): self.recorder.stop(); self.recorder = None
            if action.lower() == 'record':
                output_dir = "output/videos"; os.makedirs(output_dir, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S"); file_path = os.path.join(output_dir, f"interval_rec_{timestamp}.mp4")
                frame_size = self.camera.get_frame_size()
                fps = self.camera.get_fps()
                self.recorder = VideoRecorder(file_path, frame_size, fps=fps)
                if not self.recorder.start(): self.on_error("Failed to start video recorder for new phase."); return
                status_text = f"🔴 RECORDING: {phase_name}"
            else: status_text = f"⏸️ WAITING: {phase_name}"
            self.interval_status_label.config(text=status_text); self.phase_label.config(text=phase_name)
            repeat_str = "∞" if repeat_count == 0 else str(repeat_count)
            self.cycle_label.config(text=f"{cycle_num} / {repeat_str}")
        self.after(0, _update_ui)

    def on_tick(self, time_remaining):
        def _update_ui():
            mins, secs = divmod(time_remaining, 60); self.time_label.config(text=f"{mins:02d}:{secs:02d}")
        self.after(0, _update_ui)

    def on_complete(self):
        def _update_ui():
            messagebox.showinfo("Complete", "Interval recording schedule finished."); self.stop_interval_recording_logic()
        self.after(0, _update_ui)

    def on_error(self, message):
        def _update_ui():
            messagebox.showerror("Scheduler Error", message); self.stop_interval_recording_logic()
        self.after(0, _update_ui)

    def cleanup(self):
        if self.is_interval_recording: self.stop_interval_recording_logic()
        if self.update_id: self.after_cancel(self.update_id)
        if self.status_checker_id: self.after_cancel(self.status_checker_id)
        self.camera.stop_stream()
        if self.recorder and self.recorder.is_recording(): self.recorder.stop()