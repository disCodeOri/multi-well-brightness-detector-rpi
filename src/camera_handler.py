# src/camera_handler.py

import threading
import time
import sys
import os
import cv2

try:
    from picamera2 import Picamera2
    PICAMERA_AVAILABLE = True
except (ImportError, RuntimeError):
    PICAMERA_AVAILABLE = False

class CameraHandler:
    STATUS_STOPPED = "STOPPED"
    STATUS_INITIALIZING = "INITIALIZING"
    STATUS_RUNNING = "RUNNING"
    STATUS_ERROR = "ERROR"

    def __init__(self):
        self.cap = None
        self.picam2 = None
        self.frame = None
        self.thread = None
        self.lock = threading.Lock()
        self.status = self.STATUS_STOPPED
        self.is_running_signal = threading.Event()

        self.camera_index = 0
        self.width = 1280
        self.height = 720
        self.fps = 30  # Default/target FPS

        self.is_rpi = PICAMERA_AVAILABLE and sys.platform.startswith('linux')
        print(f"Raspberry Pi detected: {self.is_rpi}")

    def list_available_cameras(self):
        print("Scanning for available cameras...")
        if self.is_rpi:
            print("Using picamera2 scan method.")
            try:
                cameras = Picamera2.global_camera_info()
                if not cameras: return []
                return [(i, f"Cam {i} ({cam.get('Model', 'Unknown')})") for i, cam in enumerate(cameras)]
            except Exception as e:
                print(f"Could not list Pi cameras: {e}")
                return []
        elif sys.platform.startswith('linux'):
            print("Using Linux /dev/video* scan method.")
            available_cameras = []
            for i in range(10):
                if os.path.exists(f"/dev/video{i}"):
                    available_cameras.append((i, f"Camera {i} (/dev/video{i})"))
            return available_cameras
        else:
            print("Using standard OpenCV scan method.")
            available_cameras = []
            for i in range(5):
                try:
                    cap_test = cv2.VideoCapture(i)
                    if cap_test and cap_test.isOpened():
                        available_cameras.append((i, f"Camera {i}"))
                        cap_test.release()
                except Exception:
                    continue
            return available_cameras

    def start_stream(self, camera_index):
        if self.is_running_signal.is_set(): return True
        self.camera_index = camera_index
        self.is_running_signal.set()
        with self.lock:
            self.status = self.STATUS_INITIALIZING
            self.frame = None
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()
        return True

    def _measure_actual_fps(self):
        """
        Measures the real-world framerate of the camera.
        This is more reliable than trusting device properties.
        """
        print("Measuring actual camera framerate...")
        num_frames_to_sample = 50
        frames_captured = 0
        start_time = time.time()

        while frames_captured < num_frames_to_sample:
            if not self.is_running_signal.is_set(): break
            
            frame_data = None
            if self.is_rpi:
                frame_data = self.picam2.capture_array()
            else:
                ret, frame_data = self.cap.read()
                if not ret: break
            
            if frame_data is not None:
                frames_captured += 1
                with self.lock:
                    if self.is_rpi: self.frame = frame_data
                    else: self.frame = cv2.cvtColor(frame_data, cv2.COLOR_BGR2RGB)

        end_time = time.time()
        elapsed_time = end_time - start_time
        
        if elapsed_time > 0 and frames_captured > 0:
            measured_fps = frames_captured / elapsed_time
            self.fps = max(1, round(measured_fps * 0.95))
            print(f"-> Actual FPS measured: {measured_fps:.2f}. Using a stable rate of {self.fps} FPS.")
        else:
            print(f"-> FPS measurement failed. Falling back to default {self.fps} FPS.")

    def _capture_loop(self):
        try:
            target_fps = 30 # Always target a high rate; we will measure the actual rate.
            if self.is_rpi:
                print(f"Using picamera2 backend for camera index {self.camera_index}")
                self.picam2 = Picamera2(self.camera_index)
                config = self.picam2.create_preview_configuration(
                    main={"size": (self.width, self.height)},
                    controls={"FrameRate": target_fps}
                )
                self.picam2.configure(config)
                self.picam2.start()
                print(f"picamera2 stream started, targeting {target_fps} FPS.")
            else:
                print("Using OpenCV backend.")
                self.cap = cv2.VideoCapture(self.camera_index)
                if self.cap:
                    self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                    self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                    self.cap.set(cv2.CAP_PROP_FPS, target_fps)
                if not self.cap or not self.cap.isOpened():
                    raise IOError(f"Cannot open camera with index {self.camera_index}")

            with self.lock:
                self.status = self.STATUS_RUNNING
            print("Thread: Initialization complete. Stream is running.")

            self._measure_actual_fps()

        except Exception as e:
            print(f"ERROR in camera thread: {e}")
            with self.lock: self.status = self.STATUS_ERROR
            if self.is_rpi and self.picam2:
                try: self.picam2.close()
                except: pass
                self.picam2 = None
            self.is_running_signal.clear()
            return

        while self.is_running_signal.is_set():
            frame_data = None
            try:
                if self.is_rpi:
                    frame_data = self.picam2.capture_array()
                    with self.lock: self.frame = frame_data
                else:
                    ret, frame_data = self.cap.read()
                    if ret:
                        with self.lock: self.frame = cv2.cvtColor(frame_data, cv2.COLOR_BGR2RGB)
                    else: time.sleep(0.01)
            except Exception:
                self.is_running_signal.clear()

        if self.is_rpi and self.picam2:
            if self.picam2.started: self.picam2.stop()
            self.picam2.close()
            self.picam2 = None
        elif self.cap:
            self.cap.release()
            self.cap = None
            
        with self.lock:
            self.status = self.STATUS_STOPPED
            self.frame = None
        print("Thread: Capture loop finished and camera released.")

    def stop_stream(self):
        print("Stream stop requested.")
        self.is_running_signal.clear()
        if self.thread:
            self.thread.join(timeout=2)
        self.thread = None
        with self.lock:
            self.status = self.STATUS_STOPPED

    def get_frame(self):
        with self.lock:
            if self.frame is not None:
                return self.frame.copy()
        return None

    def get_status(self):
        with self.lock:
            return self.status

    def capture_image(self):
        return self.get_frame()

    def get_frame_size(self):
        return (self.width, self.height)

    def set_resolution(self, width, height):
        self.width = width
        self.height = height
        print(f"Resolution target set to: {width}x{height}")
        
    def get_fps(self):
        return self.fps