# camera_handler.py
#
# Handles all interactions with the camera using OpenCV.
# FINAL RPI FIX:
# 1. Uses os.path.exists on /dev/video* for INSTANT camera scanning on Linux.
# 2. Uses a GStreamer pipeline for INSTANT stream startup on Linux.

import cv2
import threading
import time
import sys
import os # <<< NEW: Import os for file system checks

class CameraHandler:
    STATUS_STOPPED = "STOPPED"
    STATUS_INITIALIZING = "INITIALIZING"
    STATUS_RUNNING = "RUNNING"
    STATUS_ERROR = "ERROR"

    def __init__(self):
        self.cap = None
        self.frame = None
        self.thread = None
        self.lock = threading.Lock()
        self.status = self.STATUS_STOPPED
        self.is_running_signal = threading.Event()

        self.camera_index = 0
        self.width = 1280
        self.height = 720

    def list_available_cameras(self):
        """
        Scans for available cameras.
        On Linux, this is now INSTANT by checking /dev/video* files.
        """
        print("Scanning for available cameras...")
        if sys.platform.startswith('linux'):
            # --- High-performance Linux method ---
            print("Using Linux /dev/video* scan method.")
            available_cameras = []
            for i in range(10):
                device_path = f"/dev/video{i}"
                if os.path.exists(device_path):
                    available_cameras.append((i, f"Camera {i} ({device_path})"))
                    print(f"  - Found {device_path}")
            return available_cameras
        else:
            # --- Fallback method for Windows/macOS ---
            print("Using standard OpenCV scan method.")
            available_cameras = []
            for i in range(5):
                try:
                    cap = cv2.VideoCapture(i)
                    if cap is not None and cap.isOpened():
                        available_cameras.append((i, f"Camera {i}"))
                        cap.release()
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

    def _capture_loop(self):
        """
        Initializes and runs the capture loop.
        On Linux, uses a GStreamer pipeline for fast startup.
        """
        try:
            if sys.platform.startswith('linux'):
                # --- High-performance GStreamer pipeline for Linux/RPi ---
                print("Using GStreamer pipeline for fast startup.")
                pipeline = (
                    f"v4l2src device=/dev/video{self.camera_index} ! "
                    f"video/x-raw, width={self.width}, height={self.height}, framerate=30/1 ! "
                    "videoconvert ! "
                    "video/x-raw, format=BGR ! appsink drop=true"
                )
                self.cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
            else:
                # --- Fallback for other OSes ---
                print("Using default backend.")
                self.cap = cv2.VideoCapture(self.camera_index)
                if self.cap:
                    self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                    self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)

            if not self.cap or not self.cap.isOpened():
                raise IOError(f"Cannot open camera with index {self.camera_index}")

            with self.lock:
                self.status = self.STATUS_RUNNING
            print("Thread: Initialization complete. Stream is running.")

        except Exception as e:
            print(f"ERROR in camera thread: {e}")
            with self.lock:
                self.status = self.STATUS_ERROR
            self.is_running_signal.clear()
            return

        # --- Main "Latest Frame" Capture Loop ---
        while self.is_running_signal.is_set():
            ret, frame = self.cap.read()
            if ret:
                with self.lock:
                    self.frame = frame
            else:
                time.sleep(0.01)

        # --- Cleanup ---
        if self.cap:
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
                return cv2.cvtColor(self.frame.copy(), cv2.COLOR_BGR2RGB)
        return None

    def get_status(self):
        with self.lock:
            return self.status

    def capture_image(self):
        return self.get_frame()

    def get_frame_size(self):
        # With GStreamer, the size is fixed by the pipeline, so we can return our target
        return (self.width, self.height)

    def set_resolution(self, width, height):
        self.width = width
        self.height = height
        print(f"Resolution target set to: {width}x{height}")