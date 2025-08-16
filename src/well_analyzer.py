# well_analyzer.py
#
# A script to automatically detect and analyze light intensity from multiple 
# wells in a video feed.
#
# Author: [Your Name]
# Date: [Current Date]
#
# --- LIBRARIES ---
# We use OpenCV for video and image processing, NumPy for efficient calculations,
# and Matplotlib for plotting the results. 'os' is used for file path operations.

import cv2
import numpy as np
import matplotlib.pyplot as plt
import os

# --- CONFIGURATION ---
# These are the key parameters you can tweak for your specific video.
# We put them at the top for easy access.

# Path to the video file you want to analyze.
VIDEO_PATH = 'testing/test_wells_video.mp4'  # <<< IMPORTANT: CHANGE THIS TO YOUR VIDEO FILE

# The directory where results (images, plots) will be saved.
OUTPUT_DIR = 'analysis_results'

# --- Parameters for Well Detection ---
# Brightness threshold (0-255) to identify a pixel as part of a potential well.
# This is the most important parameter to adjust for your specific experiment.
# A higher value means only very bright spots are considered.
WELL_DETECTION_THRESHOLD = 120

# The minimum number of pixels a "hotspot" must have to be considered a well.
# This helps filter out random noise and small artifacts.
MIN_WELL_AREA = 100  # pixels

# <<< NEW: Parameter for analysis sampling >>>
# Process only every Nth frame to speed up analysis on long videos.
# A value of 1 processes every frame. A value of 10 processes frames 0, 10, 20, etc.
SAMPLE_RATE = 1 # For standalone script execution

# --- TOP-DOWN LOGIC ---
# The program is structured into logical, sequential steps.
# 1. find_well_locations(): First, we analyze the whole video to create a
#    "master image" showing all well locations, and we find their bounding boxes.
# 2. track_well_intensities(): Then, we go through the video again, frame by frame,
#    and record the average brightness inside each of the boxes we found.
# 3. analyze_peaks(): With all the brightness data collected, we find the exact
#    moment (frame) and value of the peak intensity for each well.
# 4. generate_visual_report(): Finally, we create a plot and an annotated image
#    to visually present our findings.

def find_well_locations(video_path, threshold_value, min_area):
    """
    Analyzes the entire video to find the static locations of all wells.

    It works by creating a "maximum intensity projection" of the video. This means
    for each pixel, we find the brightest it ever gets throughout the entire video.
    This creates a single image where all well locations are bright, even if they
    peaked at different times. We then find the contours of these bright spots.

    Args:
        video_path (str): The full path to the video file.
        threshold_value (int): The brightness cutoff to identify hotspots.
        min_area (int): The minimum pixel area to be considered a well.

    Returns:
        A list of tuples, where each tuple is a bounding box (x, y, w, h) for a well.
        Returns None if the video cannot be opened.
        Returns the max_intensity_frame for visualization purposes.
    """
    print(f"Step 1: Finding well locations in '{video_path}'...")
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: Could not open video file: {video_path}")
        return None, None

    # Get video properties
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Initialize a black frame to store the maximum intensity of each pixel
    max_intensity_frame = np.zeros((frame_height, frame_width), dtype=np.uint8)

    # Loop through the entire video to create the projection
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Convert frame to grayscale for brightness analysis
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Update the max_intensity_frame
        max_intensity_frame = np.maximum(max_intensity_frame, gray_frame)

    cap.release()
    
    # Now, find the hotspots in our max_intensity_frame
    # Threshold the image to get a binary map of bright areas
    _, thresh = cv2.threshold(max_intensity_frame, threshold_value, 255, cv2.THRESH_BINARY)
    
    # Find the contours (outlines) of the white areas
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    well_rois = []
    for contour in contours:
        # Filter out small contours that are likely noise
        if cv2.contourArea(contour) > min_area:
            # Get the bounding box (x, y, width, height) of the contour
            x, y, w, h = cv2.boundingRect(contour)
            well_rois.append((x, y, w, h))

    print(f"-> Found {len(well_rois)} potential wells.")
    # Sort ROIs from top-to-bottom, then left-to-right for consistent numbering
    well_rois.sort(key=lambda r: (r[1], r[0]))
    
    return well_rois, max_intensity_frame


def track_well_intensities(video_path, well_rois, metric_mode='average', sample_rate=1): # <<< MODIFIED
    """
    Tracks the brightness of each well over time using a specified metric.

    Args:
        video_path (str): The path to the video file.
        well_rois (list): A list of (x, y, w, h) tuples for each well.
        metric_mode (str): The metric to use: 'average' or 'peak'.
        sample_rate (int): The interval at which to process frames (e.g., 1 for every frame).
    """
    print(f"Step 2: Tracking intensities (Sample Rate: {sample_rate}) using '{metric_mode}' metric...") # MODIFIED
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("Error: Could not reopen video file for tracking.")
        return []

    intensity_data = [[] for _ in well_rois]
    frame_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # <<< CRITICAL CHANGE: Only process frame if it matches the sample rate >>>
        if frame_count % sample_rate == 0:
            gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            for i, (x, y, w, h) in enumerate(well_rois):
                well_region = gray_frame[y:y+h, x:x+w]
                
                intensity = 0
                if well_region.size > 0:
                    if metric_mode == 'average':
                        intensity = np.mean(well_region)
                    elif metric_mode == 'peak':
                        intensity = np.max(well_region)
                    else:
                        intensity = np.mean(well_region)
                
                intensity_data[i].append(intensity)
        
        frame_count += 1
        if frame_count % 100 == 0:
            print(f"-> Processed {frame_count} frames...")

    cap.release()
    print(f"-> Intensity tracking complete. Total frames: {frame_count}.")
    return intensity_data

def analyze_peaks(intensity_data, metric_mode='average', sample_rate=1): # <<< MODIFIED
    """
    Finds the peak/maximum intensity for each well from its time-series data.

    Args:
        intensity_data (list of lists): Brightness data from track_well_intensities.
        metric_mode (str): Either 'average' or 'peak' to match display text.
        sample_rate (int): The sample rate used during tracking, for correct frame calculation.
    """
    print(f"Step 3: Analyzing for {metric_mode} intensities...")
    peak_results = []
    
    for i, well_data in enumerate(intensity_data):
        if not well_data:
            continue
            
        well_data_np = np.array(well_data)
        max_intensity = np.max(well_data_np)
        
        # <<< CRITICAL CHANGE: Multiply index by sample rate to get actual frame number >>>
        sampled_frame_index = np.argmax(well_data_np)
        actual_frame_index = sampled_frame_index * sample_rate
        
        peak_results.append({
            'well_id': i,
            'intensity': max_intensity,
            'frame': actual_frame_index,
            'metric_mode': metric_mode
        })
        
    print("-> Analysis complete.")
    return peak_results


def generate_visual_report(video_path, well_rois, intensity_data, peak_results, max_intensity_frame, output_dir, sample_rate=1): # <<< MODIFIED
    """
    Generates a plot of intensities and an annotated image of the well locations.

    Args:
        (Args are the same as before, with the addition of sample_rate)
        sample_rate (int): The sample rate used, for creating a correct time axis on the plot.
    """
    print("Step 4: Generating visual report...")
    
    # --- Create Intensity Plot ---
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(15, 8))
    
    for i, well_data in enumerate(intensity_data):
        # <<< CRITICAL CHANGE: Create a time axis based on the sample rate >>>
        num_samples = len(well_data)
        frame_numbers = np.arange(num_samples) * sample_rate
        ax.plot(frame_numbers, well_data, label=f'Well {i+1}')
        
        # Mark the peak (peak['frame'] is already the correct, scaled frame number)
        for peak in peak_results:
            if peak['well_id'] == i:
                ax.plot(peak['frame'], peak['intensity'], 'ro') # Red circle
                break

    ax.set_title('Well Intensity vs. Time', fontsize=16)
    ax.set_xlabel('Frame Number', fontsize=12)
    ax.set_ylabel('Average Brightness (0-255)', fontsize=12)
    ax.legend()
    ax.grid(True, linestyle='--', alpha=0.6)
    
    plot_path = os.path.join(output_dir, 'intensity_plot.png')
    plt.savefig(plot_path)
    print(f"-> Intensity plot saved to '{plot_path}'")
    plt.close(fig)

    # --- Create Annotated Image of Well Locations ---
    annotated_image = cv2.cvtColor(max_intensity_frame, cv2.COLOR_GRAY2BGR)
    
    for i, (x, y, w, h) in enumerate(well_rois):
        cv2.rectangle(annotated_image, (x, y), (x+w, y+h), (0, 255, 0), 2)
        cv2.putText(annotated_image, f'Well {i+1}', (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
    image_path = os.path.join(output_dir, 'well_locations.png')
    cv2.imwrite(image_path, annotated_image)
    print(f"-> Annotated well locations image saved to '{image_path}'")
    
    # --- Create Annotated Images of Peak Frames for each well ---
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("Warning: Could not open video to save peak frames.")
        return

    for peak in peak_results:
        well_id = peak['well_id']
        frame_idx = peak['frame']
        intensity = peak['intensity']
        
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        
        if ret:
            (x, y, w, h) = well_rois[well_id]
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            info_text = f"Well {well_id+1} Peak: {intensity:.2f}"
            cv2.putText(frame, info_text, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            peak_frame_path = os.path.join(output_dir, f'peak_frame_well_{well_id+1}.png')
            cv2.imwrite(peak_frame_path, frame)
            print(f"-> Saved peak frame for Well {well_id+1} to '{peak_frame_path}'")

    cap.release()


def main():
    """Main function to run the full analysis pipeline."""
    
    print("--- Starting Well Intensity Analysis ---")
    
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        
    # --- Step 1: Find Wells ---
    well_rois, max_intensity_frame = find_well_locations(VIDEO_PATH, WELL_DETECTION_THRESHOLD, MIN_WELL_AREA)
    
    if not well_rois:
        print("Execution finished: No wells were detected. Try adjusting WELL_DETECTION_THRESHOLD or MIN_WELL_AREA.")
        return

    # --- Step 2: Track Intensities ---
    # <<< MODIFIED: Pass SAMPLE_RATE to tracking function >>>
    intensity_data = track_well_intensities(VIDEO_PATH, well_rois, 'average', SAMPLE_RATE)

    # --- Step 3: Analyze Peaks ---
    # <<< MODIFIED: Pass SAMPLE_RATE to analysis function >>>
    peak_results = analyze_peaks(intensity_data, 'average', SAMPLE_RATE)
    
    # --- Step 4: Report Results ---
    print("\n--- Analysis Report ---")
    for result in peak_results:
        print(f"Well {result['well_id'] + 1}: Peak Intensity of {result['intensity']:.2f} at Frame {result['frame']}")
    print("-----------------------\n")
    
    # --- Step 5: Generate Visuals ---
    # <<< MODIFIED: Pass SAMPLE_RATE to report generation function >>>
    generate_visual_report(VIDEO_PATH, well_rois, intensity_data, peak_results, max_intensity_frame, OUTPUT_DIR, SAMPLE_RATE)
    
    print("\n--- Analysis Complete ---")
    print(f"All reports and images have been saved in the '{OUTPUT_DIR}' directory.")


if __name__ == '__main__':
    main()