# generate_test_video.py
#
# A script to create a synthetic video of glowing wells for testing the
# well_analyzer.py script.

import cv2
import numpy as np
import os
import random

# --- CONFIGURATION ---
OUTPUT_FILENAME = 'test_wells_video.avi'
VIDEO_WIDTH = 1280
VIDEO_HEIGHT = 720
FPS = 30
DURATION_SECONDS = 10

# --- Well Simulation Parameters ---
# Define the grid of wells (rows, columns)
WELL_GRID = (3, 4) 
WELL_RADIUS = 30  # pixels
PEAK_BRIGHTNESS = 255  # How bright the wells get (0-255)
BACKGROUND_COLOR = (0, 0, 0) # Pure black
NOISE_LEVEL = 0  # Set to 0 for no noise, positive number for noise

# How long the glow pulse lasts for each well, in frames. A larger number
# means a slower, longer glow.
GLOW_DURATION_FRAMES = 60 


def generate_filename(is_video=True):
    """Generate standardized filename with current parameters."""
    # Get background color value (assuming all RGB values are same since it's grayscale)
    bg_val = BACKGROUND_COLOR[0]
    
    # Create the parameter string
    params = [
        f"w{VIDEO_WIDTH}h{VIDEO_HEIGHT}",
        f"fps{FPS}",
        f"t{DURATION_SECONDS}",
        f"grid{WELL_GRID[0]}x{WELL_GRID[1]}",
        f"rad{WELL_RADIUS}",
        f"glow{GLOW_DURATION_FRAMES}",
        f"noise{NOISE_LEVEL}",
        f"br{bg_val}",
        f"p{PEAK_BRIGHTNESS}"
    ]
    
    # Join parameters with spaces
    param_string = ' '.join(params)
    
    # Create base filename
    base_name = "test_wells_video" if is_video else "test_wells_img"
    
    # Add appropriate extension
    extension = ".avi" if is_video else ".png"
    
    return f"{base_name} {param_string}{extension}"


def generate_video():
    """Generates and saves the synthetic video."""
    global OUTPUT_FILENAME  # Allow modification of global variable
    OUTPUT_FILENAME = generate_filename(is_video=True)
    
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
    fourcc = cv2.VideoWriter_fourcc(*'FFV1') # Codec for .avi files ("avc1" codec is for .mp4)
    out = cv2.VideoWriter(OUTPUT_FILENAME, fourcc, FPS, (VIDEO_WIDTH, VIDEO_HEIGHT))
    
    if not out.isOpened():
        print("Error: Could not open video writer.")
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


def generate_test_frame(preview=True, save_path=None):
    """
    Generates a single random frame with glowing wells.
    
    Args:
        preview (bool): Whether to show the frame in a preview window
        save_path (str): Path to save the image. If None, image won't be saved
    
    Returns:
        numpy.ndarray: The generated frame
    """
    # Create a dark background frame
    frame = np.full((VIDEO_HEIGHT, VIDEO_WIDTH, 3), BACKGROUND_COLOR, dtype=np.uint8)
    
    rows, cols = WELL_GRID
    num_wells = rows * cols
    
    # Calculate well positions
    well_positions = []
    x_spacing = VIDEO_WIDTH / (cols + 1)
    y_spacing = VIDEO_HEIGHT / (rows + 1)
    for r in range(rows):
        for c in range(cols):
            x = int(x_spacing * (c + 1))
            y = int(y_spacing * (r + 1))
            well_positions.append((x, y))
    
    # Randomly set some wells to glow
    for x, y in well_positions:
        # Random intensity between 0 and PEAK_BRIGHTNESS
        intensity = random.randint(0, PEAK_BRIGHTNESS)
        color = (int(intensity), int(intensity), int(intensity))
        cv2.circle(frame, (x, y), WELL_RADIUS, color, -1)
    
    # Add blur for soft glow
    frame = cv2.GaussianBlur(frame, (5, 5), 0)
    
    # Add noise if enabled
    if NOISE_LEVEL > 0:
        noise = np.random.randint(-NOISE_LEVEL, NOISE_LEVEL, frame.shape, dtype=np.int16)
        frame = np.clip(frame.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    
    # Show preview if requested
    if preview:
        cv2.imshow('Test Frame Preview', frame)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    
    # Save if path provided
    if save_path:
        cv2.imwrite(save_path, frame)
        print(f"Frame saved to: {save_path}")
    
    return frame


def create_gui():
    """Creates a GUI window with configuration controls and generation buttons."""
    import tkinter as tk
    from tkinter import ttk, filedialog

    root = tk.Tk()
    root.title("Test Data Generator")
    
    # Make the window larger to accommodate controls
    window_width = 400
    window_height = 500
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = (screen_width - window_width) // 2
    y = (screen_height - window_height) // 2
    root.geometry(f"{window_width}x{window_height}+{x}+{y}")
    root.resizable(False, False)

    # Create main frame with padding
    main_frame = ttk.Frame(root, padding="20")
    main_frame.pack(expand=True, fill='both')

    # Create configuration section
    config_frame = ttk.LabelFrame(main_frame, text="Configuration", padding="10")
    config_frame.pack(fill='x', pady=(0, 20))

    # Function to create a labeled spinbox
    def create_spinbox(parent, label, var, from_, to, increment=1):
        frame = ttk.Frame(parent)
        frame.pack(fill='x', pady=2)
        ttk.Label(frame, text=label + ":", width=20).pack(side='left')
        spinbox = ttk.Spinbox(
            frame,
            from_=from_,
            to=to,
            increment=increment,
            textvariable=var,
            width=10
        )
        spinbox.pack(side='left', padx=5)
        return spinbox

    # Create variables for all configuration parameters
    vars = {
        'width': tk.IntVar(value=VIDEO_WIDTH),
        'height': tk.IntVar(value=VIDEO_HEIGHT),
        'fps': tk.IntVar(value=FPS),
        'duration': tk.IntVar(value=DURATION_SECONDS),
        'grid_rows': tk.IntVar(value=WELL_GRID[0]),
        'grid_cols': tk.IntVar(value=WELL_GRID[1]),
        'well_radius': tk.IntVar(value=WELL_RADIUS),
        'peak_brightness': tk.IntVar(value=PEAK_BRIGHTNESS),
        'background': tk.IntVar(value=BACKGROUND_COLOR[0]),
        'noise': tk.IntVar(value=NOISE_LEVEL),
        'glow_duration': tk.IntVar(value=GLOW_DURATION_FRAMES)
    }

    # Create spinboxes for all parameters
    create_spinbox(config_frame, "Video/Img Width", vars['width'], 640, 1920)
    create_spinbox(config_frame, "Video/Img Height", vars['height'], 480, 1080)
    create_spinbox(config_frame, "FPS", vars['fps'], 1, 60)
    create_spinbox(config_frame, "Duration (seconds)", vars['duration'], 1, 60)
    create_spinbox(config_frame, "Grid Rows", vars['grid_rows'], 1, 10)
    create_spinbox(config_frame, "Grid Columns", vars['grid_cols'], 1, 10)
    create_spinbox(config_frame, "Well Radius", vars['well_radius'], 5, 100)
    create_spinbox(config_frame, "Peak Brightness", vars['peak_brightness'], 0, 255)
    create_spinbox(config_frame, "Background Color", vars['background'], 0, 255)
    create_spinbox(config_frame, "Noise Level", vars['noise'], 0, 50)
    create_spinbox(config_frame, "Glow Duration", vars['glow_duration'], 1, 300)

    # Create buttons frame
    button_frame = ttk.Frame(main_frame)
    button_frame.pack(fill='x', pady=20)

    def update_config_and_generate_video():
        # Update global variables with current spinbox values
        global VIDEO_WIDTH, VIDEO_HEIGHT, FPS, DURATION_SECONDS
        global WELL_GRID, WELL_RADIUS, PEAK_BRIGHTNESS, BACKGROUND_COLOR
        global NOISE_LEVEL, GLOW_DURATION_FRAMES
        
        VIDEO_WIDTH = vars['width'].get()
        VIDEO_HEIGHT = vars['height'].get()
        FPS = vars['fps'].get()
        DURATION_SECONDS = vars['duration'].get()
        WELL_GRID = (vars['grid_rows'].get(), vars['grid_cols'].get())
        WELL_RADIUS = vars['well_radius'].get()
        PEAK_BRIGHTNESS = vars['peak_brightness'].get()
        BACKGROUND_COLOR = (vars['background'].get(),) * 3
        NOISE_LEVEL = vars['noise'].get()
        GLOW_DURATION_FRAMES = vars['glow_duration'].get()

        # Generate video
        root.withdraw()
        generate_video()
        root.deiconify()

    def update_config_and_generate_frame():
        # Update global variables
        update_config_and_generate_video()  # Reuse the same update function
        
        # Generate frame
        suggested_name = generate_filename(is_video=False)
        save_path = filedialog.asksaveasfilename(
            initialfile=suggested_name,
            defaultextension=".png",
            filetypes=[("PNG files", "*.png"), ("All files", "*.*")],
            title="Save Test Frame As"
        )
        if save_path:
            generate_test_frame(preview=True, save_path=save_path)

    # Create and pack the buttons
    video_btn = ttk.Button(
        button_frame,
        text="Generate Video",
        command=update_config_and_generate_video
    )
    video_btn.pack(pady=5, fill='x')
    
    frame_btn = ttk.Button(
        button_frame,
        text="Generate Single Frame",
        command=update_config_and_generate_frame
    )
    frame_btn.pack(pady=5, fill='x')
    
    return root

if __name__ == '__main__':
    # Replace the argument parsing with the GUI
    root = create_gui()
    root.mainloop()