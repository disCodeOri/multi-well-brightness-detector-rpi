# well_analyzer.py

import cv2
import numpy as np
import os
from datetime import datetime

# --- CONFIGURATION (for standalone testing) ---
VIDEO_PATH = 'testing/test_wells_video.mp4'
IMAGE_PATH = 'output/images/capture_example.png' # Example path for testing
MIN_WELL_AREA = 100
SAMPLE_RATE = 1
DEFAULT_BACKGROUND_LEVEL = 0


def _find_wells_from_image(image, background_level, min_area):
    """
    --- NEW REUSABLE CORE FUNCTION ---
    This is the core logic, refactored from the old find_well_locations.
    It takes a single grayscale image and finds all well contours within it.
    """
    print("-> Finding wells in the provided image...")
    # Perform background subtraction using the provided level
    background_subtracted_frame = cv2.subtract(image, int(background_level))

    # Apply Otsu's thresholding on the CLEANED image
    optimal_threshold, thresh = cv2.threshold(background_subtracted_frame, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    print(f"-> Optimal threshold on corrected image: {optimal_threshold}")

    kernel = np.ones((5,5), np.uint8)
    separated_wells_mask = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=2)

    contours, _ = cv2.findContours(separated_wells_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    well_rois = []
    for contour in contours:
        if cv2.contourArea(contour) > min_area:
            x, y, w, h = cv2.boundingRect(contour)
            well_rois.append((x, y, w, h))

    print(f"-> Found {len(well_rois)} potential wells.")
    well_rois.sort(key=lambda r: (r[1], r[0]))

    return well_rois


def find_well_locations(video_path, background_level, min_area):
    """
    --- MODIFIED ---
    Now generates the max intensity frame from a video and then calls the core function.
    """
    print(f"Step 1: Creating max intensity projection for '{video_path}'...")

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
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

    # Call the core well-finding logic on the generated summary image
    well_rois = _find_wells_from_image(max_intensity_frame, background_level, min_area)

    return well_rois, max_intensity_frame


def track_well_intensities(video_path, well_rois, metric_mode='average', sample_rate=1):
    # This function remains unchanged
    print(f"Step 2: Tracking intensities (mode: {metric_mode})...")
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened(): return []
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
    # This function remains unchanged
    print(f"Step 3: Analyzing for peak intensities...")
    peak_results = []
    for i, well_data in enumerate(intensity_data):
        if not well_data: continue
        well_data_np = np.array(well_data)
        max_intensity = np.max(well_data_np)
        sampled_frame_index = np.argmax(well_data_np)
        actual_frame_index = sampled_frame_index * sample_rate
        peak_results.append({
            'well_id': i, 'intensity': max_intensity, 'frame': actual_frame_index, 'metric_mode': metric_mode
        })
    print("-> Analysis complete.")
    return peak_results


def run_full_analysis(video_path, background_level, min_area, metric_mode, sample_rate):
    """
    This is the top-level orchestrator for VIDEOS.
    """
    print("\n--- Starting Full Well Intensity Analysis (Video) ---")

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened(): return {"error": f"Could not open video file: {video_path}"}
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)); fps = cap.get(cv2.CAP_PROP_FPS); cap.release()
    duration_seconds = total_frames / fps if fps > 0 else 0

    well_rois, max_intensity_frame = find_well_locations(video_path, background_level, min_area)
    if not well_rois:
        return {"error": "No wells were detected. Try adjusting the Min Well Area."}

    average_intensity_data = track_well_intensities(video_path, well_rois, 'average', sample_rate)
    peak_intensity_data = track_well_intensities(video_path, well_rois, 'peak', sample_rate)
    primary_intensity_data = average_intensity_data if metric_mode == 'average' else peak_intensity_data
    peak_results = analyze_peaks(primary_intensity_data, metric_mode, sample_rate)

    summary_text = f"--- Analysis Report ---\n"
    summary_text += f"Video Source: {os.path.basename(video_path)}\n"
    summary_text += f"Wells Detected: {len(well_rois)}\n"
    summary_text += f"Metric: {'Average' if metric_mode == 'average' else 'Peak'} Intensity\n\n"
    for result in peak_results:
        summary_text += f"Well {result['well_id'] + 1}: Intensity of {result['intensity']:.2f} at Frame {result['frame']}\n"

    master_results = {
        "numerical_data": peak_results, "intensity_data": primary_intensity_data,
        "average_intensity_data": average_intensity_data, "peak_intensity_data": peak_intensity_data,
        "well_rois": well_rois, "max_intensity_frame": max_intensity_frame,
        "summary_text": summary_text, "video_path": video_path, "sample_rate": sample_rate,
        "metric_mode": metric_mode, "analysis_timestamp": datetime.now().isoformat(),
        "total_frames": total_frames, "fps": fps, "duration_seconds": duration_seconds, "error": None
    }
    print("\n--- Video Analysis Complete: Raw data package assembled. ---")
    return master_results


def run_single_image_analysis(image_path, background_level, min_area, metric_mode):
    """
    --- NEW TOP-LEVEL FUNCTION FOR STATIC IMAGES ---
    Analyzes a single image and packages the results to match the video analysis format.
    """
    print("\n--- Starting Well Intensity Analysis (Single Image) ---")

    image = cv2.imread(image_path)
    if image is None:
        return {"error": f"Could not read image file: {image_path}"}

    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Step 1: Find Wells directly from the image
    well_rois = _find_wells_from_image(gray_image, background_level, min_area)
    if not well_rois:
        return {"error": "No wells were detected in the image."}

    # Step 2: "Track" intensities (for a single image, this is just one measurement per well)
    intensity_data = []
    for (x, y, w, h) in well_rois:
        well_region = gray_image[y:y+h, x:x+w]
        intensity = np.mean(well_region) if metric_mode == 'average' else np.max(well_region)
        intensity_data.append([intensity]) # Pack as a list with one item for consistency

    # Step 3: "Analyze Peaks" (the peak is just the single value we measured)
    peak_results = []
    for i, well_data in enumerate(intensity_data):
        peak_results.append({
            'well_id': i, 'intensity': well_data[0], 'frame': 0, 'metric_mode': metric_mode
        })

    # Step 4: Assemble the master results dictionary, mimicking the video format
    summary_text = f"--- Analysis Report ---\n"
    summary_text += f"Image Source: {os.path.basename(image_path)}\n"
    summary_text += f"Wells Detected: {len(well_rois)}\n"
    summary_text += f"Metric: {'Average' if metric_mode == 'average' else 'Peak'} Intensity\n\n"
    for result in peak_results:
        summary_text += f"Well {result['well_id'] + 1}: Intensity of {result['intensity']:.2f}\n"

    master_results = {
        "numerical_data": peak_results, "intensity_data": intensity_data,
        "average_intensity_data": intensity_data, "peak_intensity_data": intensity_data,
        "well_rois": well_rois,
        "max_intensity_frame": gray_image, # For an image, this is just the image itself
        "summary_text": summary_text,
        "video_path": image_path, # Use the same key for simplicity in the Results tab
        "sample_rate": 1,
        "metric_mode": metric_mode, "analysis_timestamp": datetime.now().isoformat(),
        "total_frames": 1, "fps": 0, "duration_seconds": 0, "error": None
    }

    print("\n--- Image Analysis Complete: Raw data package assembled. ---")
    return master_results


def main():
    """Main function for standalone testing."""
    print("--- TESTING VIDEO ANALYSIS ---")
    video_results = run_full_analysis(VIDEO_PATH, DEFAULT_BACKGROUND_LEVEL, MIN_WELL_AREA, 'average', SAMPLE_RATE)
    if video_results.get("error"):
        print(f"ERROR: {video_results['error']}")
    else:
        print("\n--- Standalone Video Run Report ---")
        print(video_results['summary_text'])

    print("\n\n--- TESTING IMAGE ANALYSIS ---")
    # You would need to create a test image for this to work
    if os.path.exists(IMAGE_PATH):
        image_results = run_single_image_analysis(IMAGE_PATH, DEFAULT_BACKGROUND_LEVEL, MIN_WELL_AREA, 'average')
        if image_results.get("error"):
            print(f"ERROR: {image_results['error']}")
        else:
            print("\n--- Standalone Image Run Report ---")
            print(image_results['summary_text'])
    else:
        print(f"Test image not found at '{IMAGE_PATH}', skipping image analysis test.")


if __name__ == '__main__':
    main()