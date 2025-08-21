# video_recorder.py
#
# A dedicated class to handle the logic of recording video frames to a file.
# Uses OpenCV's VideoWriter.

import cv2
import os
from datetime import datetime

class VideoRecorder:
    def __init__(self, file_path, frame_size, fps=30):
        """
        Initializes the Video Recorder.
        Args:
            file_path (str): The full path where the video will be saved.
            frame_size (tuple): A tuple of (width, height) for the video frames.
            fps (int): The frames per second for the output video.
        """
        self.file_path = file_path
        self.frame_size = frame_size
        self.fps = fps
        self.video_writer = None
        self._is_recording = False

    def start(self):
        """
        Starts the recording process by initializing the VideoWriter.
        Returns:
            bool: True if recording started successfully, False otherwise.
        """
        try:
            # Ensure the output directory exists
            output_dir = os.path.dirname(self.file_path)
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            # Define the codec for MP4 files. 'mp4v' is a good cross-platform choice.
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            
            # Create the VideoWriter object
            self.video_writer = cv2.VideoWriter(
                self.file_path, fourcc, self.fps, self.frame_size
            )

            if not self.video_writer.isOpened():
                print(f"Error: Could not open VideoWriter for path: {self.file_path}")
                return False

            self._is_recording = True
            print(f"Recording started. Output will be saved to: {self.file_path}")
            return True

        except Exception as e:
            print(f"An error occurred while starting the recorder: {e}")
            return False

    def write_frame(self, frame):
        """
        Writes a single frame to the video file.
        The frame should be in RGB format.
        """
        if not self._is_recording or self.video_writer is None:
            return

        try:
            # OpenCV's VideoWriter expects frames in BGR format.
            bgr_frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            self.video_writer.write(bgr_frame)
        except Exception as e:
            print(f"Error writing frame: {e}")
            self.stop() # Stop recording if an error occurs

    def stop(self):
        """Stops the recording and releases the video file."""
        if not self._is_recording:
            return

        self._is_recording = False
        if self.video_writer:
            self.video_writer.release()
            self.video_writer = None
            print(f"Recording stopped. Video saved successfully.")
            
    def is_recording(self):
        """Returns the recording status."""
        return self._is_recording