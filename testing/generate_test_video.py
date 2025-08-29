# generate_test_video.py
#
# A script to create a synthetic video of glowing wells for testing the
# well_analyzer.py script.

import cv2
import numpy as np
import os
import random

# --- CONFIGURATION ---
OUTPUT_FILENAME = 'test_wells_video.mp4'
VIDEO_WIDTH = 1280
VIDEO_HEIGHT = 720
FPS = 30
DURATION_SECONDS = 10

# --- Well Simulation Parameters ---
# Define the grid of wells (rows, columns)
WELL_GRID = (3, 4) 
WELL_RADIUS = 30  # pixels
PEAK_BRIGHTNESS = 250  # How bright the wells get (0-255)
BACKGROUND_COLOR = (20, 20, 20) # Dark gray, not pure black
NOISE_LEVEL = 10  # Set to 0 for no noise, positive number for noise

# How long the glow pulse lasts for each well, in frames. A larger number
# means a slower, longer glow.
GLOW_DURATION_FRAMES = 60 


def generate_video():
    """Generates and saves the synthetic video."""
    
    total_frames = DURATION_SECONDS * FPS
    rows, cols = WELL_GRID
    num_wells = rows * cols

    print(f"--- Generating Synthetic Test Video ---")
    print(f"Filename: {OUTPUT_FILENAME}")
    print(f"Dimensions: {VIDEO_WIDTH}x{VIDEO_HEIGHT}")
    print(f"Duration: {DURATION_SECONDS}s at {FPS}fps ({total_frames} frames)")
    print(f"Well Grid: {rows}x{cols} ({num_wells} wells)")

    # --- Video Writer Setup ---
    # Define the codec and create VideoWriter object
    # <<< FIXED: Use 'avc1' (H.264) for better compatibility and to avoid decoder errors >>>
    fourcc = cv2.VideoWriter_fourcc(*'avc1') # Codec for .mp4 files
    out = cv2.VideoWriter(OUTPUT_FILENAME, fourcc, FPS, (VIDEO_WIDTH, VIDEO_HEIGHT))
    
    if not out.isOpened():
        print("Error: Could not open video writer.")
        print("This might be because the 'avc1' (H.264) codec is not available on your system.")
        print("Consider installing a codec pack like K-Lite (on Windows) or ensuring FFmpeg is correctly installed.")
        return

    # --- Pre-calculate Well Positions and Peak Times ---
    well_positions = []
    # Calculate spacing for the grid
    x_spacing = VIDEO_WIDTH / (cols + 1)
    y_spacing = VIDEO_HEIGHT / (rows + 1)
    for r in range(rows):
        for c in range(cols):
            x = int(x_spacing * (c + 1))
            y = int(y_spacing * (r + 1))
            well_positions.append((x, y))

    # Assign a random peak frame for each well
    # Ensure peaks are spread out within the video duration
    peak_frames = [random.randint(int(0.1*total_frames), int(0.9*total_frames)) for _ in range(num_wells)]
    
    print("\nSimulating well peaks at frames:", peak_frames)

    # --- Frame Generation Loop ---
    for frame_num in range(total_frames):
        # Create a dark background frame
        frame = np.full((VIDEO_HEIGHT, VIDEO_WIDTH, 3), BACKGROUND_COLOR, dtype=np.uint8)

        # Draw each well with its current brightness
        for i in range(num_wells):
            center_x, center_y = well_positions[i]
            peak_frame = peak_frames[i]
            
            # Calculate brightness using a Gaussian (bell curve) function
            # This creates a smooth rise and fall in intensity around the peak
            exponent = -((frame_num - peak_frame) ** 2) / (2 * (GLOW_DURATION_FRAMES / 2.355) ** 2)
            intensity = PEAK_BRIGHTNESS * np.exp(exponent)
            
            # The color of the well is its intensity
            color = (int(intensity), int(intensity), int(intensity))
            
            # Draw the well on the frame
            cv2.circle(frame, (center_x, center_y), WELL_RADIUS, color, -1)
            # Add a slight blur to make the glow softer
            frame = cv2.GaussianBlur(frame, (5, 5), 0)

        # Add some random noise to the entire frame only if NOISE_LEVEL > 0
        if NOISE_LEVEL > 0:
            noise = np.random.randint(-NOISE_LEVEL, NOISE_LEVEL, frame.shape, dtype=np.int16)
            frame = np.clip(frame.astype(np.int16) + noise, 0, 255).astype(np.uint8)

        # Write the frame to the video file
        out.write(frame)
        
        # Print progress
        if frame_num % (FPS) == 0:
            print(f"-> Generated {frame_num} / {total_frames} frames...")

    # --- Finalize ---
    out.release()
    print("\n--- Video Generation Complete ---")
    print(f"Test video saved as '{OUTPUT_FILENAME}'")


if __name__ == '__main__':
    generate_video()