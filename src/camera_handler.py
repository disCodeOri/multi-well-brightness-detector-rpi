# camera_handler.py
#
# Handles all interactions with the camera.
# --- MODIFIED TO USE PICAMERA2 ON RASPBERRY PI ---
# 1. Intelligently detects if running on a Raspberry Pi with picamera2 available.
# 2. Uses the robust picamera2 library for native, high-performance camera access.
# 3. Retains the old OpenCV/GStreamer method as a fallback for other Linux/Windows/macOS systems.
# --- FIX: Added .close() to properly release the RPi camera on stream stop. ---

import threading
import time
import sys
import os
import cv2

# --- NEW: Attempt to import picamera2 and check availability ---
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
        self.picam2 = None # For picamera2 instance
        self.frame = None
        self.thread = None
        self.lock = threading.Lock()
        self.status = self.STATUS_STOPPED
        self.is_running_signal = threading.Event()

        self.camera_index = 0
        self.width = 1280
        self.height = 720
        
        # --- Check if we are on a Raspberry Pi ---
        self.is_rpi = PICAMERA_AVAILABLE and sys.platform.startswith('linux')
        print(f"Raspberry Pi detected: {self.is_rpi}")


    def list_available_cameras(self):
        """
        Scans for available cameras.
        On Raspberry Pi, this now uses the picamera2 library.
        """
        print("Scanning for available cameras...")
        if self.is_rpi:
            # --- High-performance Raspberry Pi method ---
            print("Using picamera2 scan method.")
            try:
                cameras = Picamera2.global_camera_info()
                if not cameras:
                    return []
                return [(i, f"Cam {i} ({cam.get('Model', 'Unknown')})") for i, cam in enumerate(cameras)]
            except Exception as e:
                print(f"Could not list Pi cameras: {e}")
                return []
        elif sys.platform.startswith('linux'):
            # --- Old Linux method as fallback ---
            print("Using Linux /dev/video* scan method.")
            available_cameras = []
            for i in range(10):
                if os.path.exists(f"/dev/video{i}"):
                    available_cameras.append((i, f"Camera {i} (/dev/video{i})"))
            return available_cameras
        else:
            # --- Fallback method for Windows/macOS ---
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

    def _capture_loop(self):
        """
        Initializes and runs the capture loop.
        Uses picamera2 on Raspberry Pi for optimal performance.
        """
        try:
            if self.is_rpi:
                # --- Raspberry Pi Capture Loop using picamera2 ---
                print(f"Using picamera2 backend for camera index {self.camera_index}")
                self.picam2 = Picamera2(self.camera_index)
                config = self.picam2.create_preview_configuration(
                    main={"size": (self.width, self.height)}
                )
                self.picam2.configure(config)
                self.picam2.start()
                print("picamera2 stream started successfully.")
            else:
                # --- Fallback for other OSes ---
                print("Using OpenCV backend.")
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
            # --- FIX: Ensure camera is closed even if startup fails ---
            if self.is_rpi and self.picam2:
                try:
                    self.picam2.close()
                except: pass
                self.picam2 = None
            self.is_running_signal.clear()
            return

        # --- Main Capture Loop ---
        while self.is_running_signal.is_set():
            frame_data = None
            try:
                if self.is_rpi:
                    # --- Get frame from picamera2 ---
                    frame_data = self.picam2.capture_array()
                    with self.lock:
                        self.frame = frame_data # Already in RGB format
                else:
                    # --- Get frame from OpenCV ---
                    ret, frame_data = self.cap.read()
                    if ret:
                        with self.lock:
                            # Convert BGR to RGB
                            self.frame = cv2.cvtColor(frame_data, cv2.COLOR_BGR2RGB)
                    else:
                        time.sleep(0.01)
            except Exception:
                # If capture fails mid-stream, break the loop
                self.is_running_signal.clear()


        # --- Cleanup ---
        if self.is_rpi and self.picam2:
            # --- MODIFIED CLEANUP ---
            if self.picam2.started:
                self.picam2.stop()
            self.picam2.close() # <<< CRUCIAL FIX: Properly close the camera to release hardware.
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