# Multi-Well Brightness Detector

## Overview

The Multi-Well Brightness Detector is a graphical user interface (GUI) application designed for capturing and analyzing video feeds and static images to track brightness intensity changes in multiple "wells," such as those found in a microplate. The software is optimized for high-performance, native camera access on a Raspberry Pi using the `picamera2` library, but it also includes a fallback mechanism using OpenCV for compatibility with Windows, macOS, and other Linux distributions.

The application allows users to view a live camera feed, record video, and then perform a detailed analysis on a video or image file. The analysis automatically detects the locations of wells, tracks their brightness over time (for videos) or measures it once (for images) using either average or peak intensity metrics. When using the peak intensity metric, the software also identifies the precise coordinates of the brightest pixel. The findings are presented in an interactive results panel with tables, plots, and image previews. The comprehensive results can be exported in various formats, including images, JSON, and Excel.

## Features

### Camera & Capture

- **Live Camera Feed:** View a real-time stream from a connected camera.
- **Raspberry Pi Optimization:** Utilizes the `picamera2` library for efficient, native camera handling on Raspberry Pi. A bug fix ensures the camera hardware is now properly released on stream stop.
- **Cross-Platform Support:** Falls back to OpenCV's `VideoCapture` for compatibility with Windows, macOS, and non-RPi Linux systems.
- **Multi-Camera Detection:** Automatically scans for and lists available cameras.
- **Adjustable Settings:** Control camera resolution, brightness, and contrast in real-time. The brightness/contrast adjustment has been improved to prevent color inversion artifacts at low brightness levels.
- **Image Capture:** Save the current view from the camera feed as a PNG image.
- **Video Recording:** Record the live feed directly to an MP4 video file.

### Analysis

- **Load Existing Media (Videos & Images):** Analyze pre-recorded video files (`.mp4`, `.avi`, `.mov`) or static image files (`.png`, `.jpg`, `.bmp`).
- **Automatic Well Detection:** Intelligently identifies well locations by creating a maximum intensity projection of the video or by analyzing the provided static image.
- **Configurable Parameters:** Fine-tune the analysis with adjustable settings for:
  - **Threshold:** The brightness value for separating wells from the background.
  - **Min Well Area:** The minimum pixel area to be considered a well.
  - **Brightness Metric:** Choose between tracking the "Average Intensity" or "Peak Intensity" within each well. The 'Peak Intensity' metric now also tracks the exact (x, y) coordinates of the brightest pixel.
  - **Sample Rate:** Analyze every Nth frame to speed up processing on long videos (video only).
- **Asynchronous Processing:** The analysis runs in a separate thread, keeping the GUI responsive.

### Results & Data Export

- **Interactive Results Tab:** A dedicated interface to explore the analysis output.
- **Data Table:** Displays a list of all detected wells with their peak intensity and the corresponding frame number.
- **Visual Frame Preview:** Clicking a well in the table shows the exact frame where its peak brightness occurred, with the well highlighted. In 'Peak Intensity' mode, a circle also marks the brightest pixel.
- **Intensity Plot:** An interactive Matplotlib graph shows the brightness of each well. For videos, it's a line plot over time; for images, it's a bar chart comparing wells.
- **Detailed Summary:** A text-based report provides a summary of the analysis settings and findings.
- **Multiple Export Options:**
  - **Save Frame:** Save the currently previewed peak frame as a PNG image.
  - **Save All Frames:** Batch-save the peak frames for all detected wells (video only).
  - **Save Well Map:** Export an image showing the locations of all detected wells. In 'Peak Intensity' mode, the map also includes markers for the brightest pixel in each well.
  - **Save Data (JSON):** Export all analysis results, including peak data, well locations, and analysis metadata, into a structured JSON file.
  - **Save Data (Excel):** Export the full time-series brightness data for both average and peak intensity metrics into an XLSX file, with a separate sheet for analysis metadata.

## Requirements

The application is built with Python 3. The following libraries are required:

- `opencv-python`
- `numpy`
- `Pillow` (PIL)
- `matplotlib`
- `openpyxl` (for Excel export functionality)
- `picamera2` (Required for native camera support on Raspberry Pi OS Bookworm or newer)

## Installation

1.  **Clone the repository:**
    ```bash
    git clone <your-repository-url>
    cd multi-well-brightness-detector-rpi
    ```
2.  **Create and activate a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```
3.  **Install the required libraries:**
    You can install all requirements from the `requirements.txt` file:
    ```bash
    pip install -r requirements.txt
    ```
    Alternatively, you can install them manually:
    ```bash
    pip install opencv-python numpy Pillow matplotlib openpyxl
    ```
4.  **(Raspberry Pi Only) Install `picamera2`:**
    The `picamera2` library is typically pre-installed on recent versions of Raspberry Pi OS. If it's missing, you may need to install it and its dependencies:
    ```bash
    sudo apt update
    sudo apt install -y python3-picamera2
    ```

## Usage

Run the application from the root directory of the project:

```bash
python src/main.py
```

### Workflow

1.  **Capture Tab:**
    - Select a camera and resolution from the dropdown menus.
    - Click **Start Stream** to begin the live feed.
    - Adjust Brightness and Contrast sliders as needed.
    - Click **Capture Image** to save a single frame to the `output/images` folder.
    - Click **Start Recording** to save a video to the `output/videos` folder. Click **Stop Recording** to finish.
2.  **Analysis Tab:**
    - Click **Load Media** to select a video or image file you want to analyze.
    - A preview of the media will appear. You can play/pause and scrub through the timeline for videos.
    - Adjust the `Threshold`, `Min Well Area`, `Brightness Metric`, and `Sample Rate` to fit your media.
    - Click **Run Analysis**. A progress bar will appear while the media is processed.
3.  **Results Tab:**
    - Once the analysis is complete, the application will automatically switch to the **Results** tab.
    - Click on any well in the table to see its peak frame in the preview window.
    - Use the plot controls to zoom and pan the intensity graph.
    - Use the **Export** buttons at the bottom to save your data in the desired format.

## Building an Executable

You can create a standalone executable file using `pyinstaller`. This bundles the application and its Python dependencies into a single file that can be run on other machines without a Python installation.

Navigate to the project's root folder and run the following command:

```bash
pyinstaller --noconfirm --onefile --windowed --name "WellIntensityAnalyzer" src/main.py
```

The final executable will be located in the `dist` folder.

## Project Structure

```
multi-well-brightness-detector-rpi/
├── README.md                   # This file
├── requirements.txt            # Python package requirements
├── output/                     # Default directory for saved images and videos
│   ├── images/
│   └── videos/
├── src/
│   ├── camera_handler.py       # Manages camera interactions (picamera2 / OpenCV)
│   ├── main.py                 # Main application entry point and GUI window
│   ├── video_recorder.py       # Handles video recording logic
│   ├── well_analyzer.py        # Core logic for video and image analysis
│   └── tabs/
│       ├── capture_tab.py      # UI and logic for the 'Capture' tab
│       ├── analysis_tab.py     # UI and logic for the 'Analysis' tab
│       └── results_tab.py      # UI and logic for the 'Results' tab
└── testing/                    # Test videos and images
```
