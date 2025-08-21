# well_analyzer.py
#
# MODIFIED: This script is now a pure data processing module. It performs all
# analysis in memory and returns a package of raw data (intensity series, ROIs, etc.)
# It no longer saves any image or plot files.

import cv2
import numpy as np
import os
from datetime import datetime

# --- CONFIGURATION (for standalone testing) ---
VIDEO_PATH = 'testing/test_wells_video.mp4'
WELL_DETECTION_THRESHOLD = 120
MIN_WELL_AREA = 100
SAMPLE_RATE = 1

def find_well_locations(video_path, threshold_value, min_area):
    """
    Analyzes the entire video to find the static locations of all wells.
    Returns the bounding boxes and the max intensity projection frame.
    (This function is unchanged)
    """
    print(f"Step 1: Finding well locations in '{video_path}'...")
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: Could not open video file: {video_path}")
        return None, None

    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    max_intensity_frame = np.zeros((frame_height, frame_width), dtype=np.uint8)

    while True:
        ret, frame = cap.read()
        if not ret: break
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        max_intensity_frame = np.maximum(max_intensity_frame, gray_frame)

    cap.release()
    
    _, thresh = cv2.threshold(max_intensity_frame, threshold_value, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    well_rois = []
    for contour in contours:
        if cv2.contourArea(contour) > min_area:
            x, y, w, h = cv2.boundingRect(contour)
            well_rois.append((x, y, w, h))

    print(f"-> Found {len(well_rois)} potential wells.")
    well_rois.sort(key=lambda r: (r[1], r[0]))
    
    return well_rois, max_intensity_frame


def track_well_intensities(video_path, well_rois, metric_mode='average', sample_rate=1):
    """
    Tracks the brightness of each well over time.
    Returns a list of lists containing the intensity data for each well.
    (This function is unchanged)
    """
    print(f"Step 2: Tracking intensities (mode: {metric_mode})...")
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("Error: Could not reopen video file for tracking.")
        return []

    intensity_data = [[] for _ in well_rois]
    frame_count = 0

    while True:
        ret, frame = cap.read()
        if not ret: break
        
        if frame_count % sample_rate == 0:
            gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            for i, (x, y, w, h) in enumerate(well_rois):
                well_region = gray_frame[y:y+h, x:x+w]
                intensity = np.mean(well_region) if metric_mode == 'average' else np.max(well_region)
                intensity_data[i].append(intensity)
        
        frame_count += 1

    cap.release()
    print(f"-> Intensity tracking complete.")
    return intensity_data

def analyze_peaks(intensity_data, metric_mode='average', sample_rate=1):
    """
    Finds the peak intensity for each well from its time-series data.
    (This function is unchanged)
    """
    print(f"Step 3: Analyzing for peak intensities...")
    peak_results = []
    for i, well_data in enumerate(intensity_data):
        if not well_data: continue
        well_data_np = np.array(well_data)
        max_intensity = np.max(well_data_np)
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


def run_full_analysis(video_path, threshold, min_area, metric_mode, sample_rate):
    """
    This is the top-level orchestrator. It runs the entire analysis pipeline
    and returns a single dictionary containing all RAW data needed by the UI
    for visualization and saving. It now calculates both average and peak intensity data.
    """
    print("\n--- Starting Full Well Intensity Analysis ---")
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return {"error": f"Could not open video file for metadata: {video_path}"}
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    duration_seconds = total_frames / fps if fps > 0 else 0
    cap.release()
    
    # Step 1: Find Wells
    well_rois, max_intensity_frame = find_well_locations(video_path, threshold, min_area)
    if not well_rois:
        return {"error": "No wells were detected. Try adjusting parameters."}

    # Track Intensities for BOTH modes
    average_intensity_data = track_well_intensities(video_path, well_rois, 'average', sample_rate)
    peak_intensity_data = track_well_intensities(video_path, well_rois, 'peak', sample_rate)

    # Step 3: Analyze Peaks based on the user-selected mode for UI display
    primary_intensity_data = average_intensity_data if metric_mode == 'average' else peak_intensity_data
    peak_results = analyze_peaks(primary_intensity_data, metric_mode, sample_rate)
    
    # Step 4: Assemble the master results dictionary with raw data
    summary_text = f"--- Analysis Report ---\n"
    summary_text += f"Video Source: {os.path.basename(video_path)}\n"
    summary_text += f"Wells Detected: {len(well_rois)}\n"
    summary_text += f"Metric: {'Average' if metric_mode == 'average' else 'Peak'} Intensity\n\n"
    for result in peak_results:
        summary_text += f"Well {result['well_id'] + 1}: Intensity of {result['intensity']:.2f} at Frame {result['frame']}\n"
    
    master_results = {
        "numerical_data": peak_results,
        "intensity_data": primary_intensity_data, # For UI consistency
        "average_intensity_data": average_intensity_data, # For Excel export
        "peak_intensity_data": peak_intensity_data, # For Excel export
        "well_rois": well_rois,
        "max_intensity_frame": max_intensity_frame,
        "summary_text": summary_text,
        "video_path": video_path,
        "sample_rate": sample_rate,
        "metric_mode": metric_mode,
        "analysis_timestamp": datetime.now().isoformat(),
        "total_frames": total_frames,
        "fps": fps,
        "duration_seconds": duration_seconds,
        "error": None
    }
    
    print("\n--- Analysis Complete: Raw data package assembled. ---")
    return master_results


def main():
    """Main function for standalone testing."""
    results = run_full_analysis(VIDEO_PATH, WELL_DETECTION_THRESHOLD, MIN_WELL_AREA, 'average', SAMPLE_RATE)
    if results.get("error"):
        print(f"ERROR: {results['error']}")
    else:
        print("\n--- Standalone Run Report ---")
        print(results['summary_text'])

if __name__ == '__main__':
    main()