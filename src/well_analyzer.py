# well_analyzer.py
#
# A script to automatically detect and analyze light intensity from multiple 
# wells in a video feed.
# MODIFIED: This script now acts as a "data factory", producing a comprehensive
# results dictionary for use by a GUI.

import cv2
import numpy as np
import matplotlib.pyplot as plt
import os

# --- CONFIGURATION ---
VIDEO_PATH = 'testing/test_wells_video.mp4'
OUTPUT_DIR = 'analysis_results'
WELL_DETECTION_THRESHOLD = 120
MIN_WELL_AREA = 100
SAMPLE_RATE = 1

def find_well_locations(video_path, threshold_value, min_area):
    """
    Analyzes the entire video to find the static locations of all wells.
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
    Tracks the brightness of each well over time using a specified metric.
    (This function is unchanged)
    """
    print(f"Step 2: Tracking intensities (Sample Rate: {sample_rate}) using '{metric_mode}' metric...")
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
                intensity = 0
                if well_region.size > 0:
                    intensity = np.mean(well_region) if metric_mode == 'average' else np.max(well_region)
                intensity_data[i].append(intensity)
        
        frame_count += 1

    cap.release()
    print(f"-> Intensity tracking complete.")
    return intensity_data

def analyze_peaks(intensity_data, metric_mode='average', sample_rate=1):
    """
    Finds the peak/maximum intensity for each well from its time-series data.
    (This function is unchanged)
    """
    print(f"Step 3: Analyzing for {metric_mode} intensities...")
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


def generate_visual_report(video_path, well_rois, intensity_data, peak_results, max_intensity_frame, output_dir, sample_rate=1):
    """
    <<< MODIFIED >>>
    Generates all visual assets, saves them to disk, and returns a dictionary of their file paths.
    """
    print("Step 4: Generating visual report...")
    os.makedirs(output_dir, exist_ok=True)
    
    # --- Create Intensity Plot ---
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(15, 8))
    for i, well_data in enumerate(intensity_data):
        num_samples = len(well_data)
        frame_numbers = np.arange(num_samples) * sample_rate
        ax.plot(frame_numbers, well_data, label=f'Well {i+1}')
        for peak in peak_results:
            if peak['well_id'] == i:
                ax.plot(peak['frame'], peak['intensity'], 'ro')
                break
    ax.set_title('Well Intensity vs. Time', fontsize=16)
    ax.set_xlabel('Frame Number', fontsize=12)
    ax.set_ylabel('Average Brightness (0-255)', fontsize=12)
    ax.legend(); ax.grid(True, linestyle='--', alpha=0.6)
    plot_path = os.path.join(output_dir, 'intensity_plot.png')
    plt.savefig(plot_path); plt.close(fig)
    print(f"-> Intensity plot saved to '{plot_path}'")

    # --- Create Annotated Image of Well Locations ---
    annotated_image = cv2.cvtColor(max_intensity_frame, cv2.COLOR_GRAY2BGR)
    for i, (x, y, w, h) in enumerate(well_rois):
        cv2.rectangle(annotated_image, (x, y), (x+w, y+h), (0, 255, 0), 2)
        cv2.putText(annotated_image, f'Well {i+1}', (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    image_path = os.path.join(output_dir, 'well_locations.png')
    cv2.imwrite(image_path, annotated_image)
    print(f"-> Annotated well locations image saved to '{image_path}'")
    
    # --- <<< NEW: Create Annotated Images of Peak Frames for each well >>> ---
    peak_frames_paths = []
    cap = cv2.VideoCapture(video_path)
    if cap.isOpened():
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
                peak_frames_paths.append(peak_frame_path)
                print(f"-> Saved peak frame for Well {well_id+1} to '{peak_frame_path}'")
        cap.release()
    else:
        print("Warning: Could not open video to save peak frames.")

    # --- <<< NEW: Return a dictionary of asset paths >>> ---
    return {
        'plot_path': plot_path,
        'well_map_path': image_path,
        'peak_frames_paths': peak_frames_paths
    }

def run_full_analysis(video_path, threshold, min_area, metric_mode, sample_rate):
    """
    <<< NEW >>>
    This is the new top-level orchestrator function intended to be called from the GUI.
    It runs the entire analysis pipeline and returns a single, comprehensive
    "results package" dictionary.
    """
    print("\n--- Starting Full Well Intensity Analysis ---")
    
    output_dir = 'analysis_results'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    # Step 1: Find Wells
    well_rois, max_intensity_frame = find_well_locations(video_path, threshold, min_area)
    if not well_rois:
        return {"error": "No wells were detected. Try adjusting parameters."}

    # Step 2: Track Intensities
    intensity_data = track_well_intensities(video_path, well_rois, metric_mode, sample_rate)

    # Step 3: Analyze Peaks
    peak_results = analyze_peaks(intensity_data, metric_mode, sample_rate)
    
    # Step 4: Generate Visual Report and get asset paths
    visual_assets = generate_visual_report(video_path, well_rois, intensity_data, peak_results, max_intensity_frame, output_dir, sample_rate)

    # Step 5: Assemble the master results dictionary
    summary_text = f"--- Analysis Report ---\n"
    summary_text += f"Video Source: {os.path.basename(video_path)}\n"
    summary_text += f"Wells Detected: {len(well_rois)}\n"
    summary_text += f"Metric: {'Average' if metric_mode == 'average' else 'Peak'} Intensity\n\n"
    for result in peak_results:
        summary_text += f"Well {result['well_id'] + 1}: Intensity of {result['intensity']:.2f} at Frame {result['frame']}\n"
    
    master_results = {
        "visuals": visual_assets,
        "numerical_data": peak_results,
        "summary_text": summary_text,
        "error": None
    }
    
    print("\n--- Analysis Complete: Results package assembled. ---")
    return master_results


def main():
    """Main function to run the full analysis pipeline (for standalone testing)."""
    results = run_full_analysis(VIDEO_PATH, WELL_DETECTION_THRESHOLD, MIN_WELL_AREA, 'average', SAMPLE_RATE)
    if results.get("error"):
        print(f"ERROR: {results['error']}")
    else:
        print("\n--- Standalone Run Report ---")
        print(results['summary_text'])
        print(f"Visuals saved in '{os.path.dirname(results['visuals']['plot_path'])}'")

if __name__ == '__main__':
    main()