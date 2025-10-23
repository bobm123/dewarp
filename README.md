# Dewarp

An interactive perspective transform tool for correcting image distortion using OpenCV.

## Features

- **Interactive Point Selection**: Click to select 4 corner points on your document
- **Drag-and-Drop Adjustment**: Click and drag any point to fine-tune its position
- **Zoom & Pan**: Mouse wheel zoom and right-click pan for precise point placement
- **Auto-Calculated Dimensions**: Automatically calculates output dimensions from selected points
- **Millimeter-Based Dimensions**: Output size in mm with configurable DPI
- **Real-time Visual Feedback**: Enhanced point markers with numbers and connecting lines
- **Perspective Transform**: Automatically straightens and corrects perspective
- **Side-by-Side View**: View original and transformed images simultaneously
- **Save Results**: Export transformed images in JPG or PNG format

## Requirements

```bash
pip install opencv-python numpy pillow
```

## Usage

### Running the Application

```bash
# Start with file dialog
python dewarp.py

# Or load an image directly
python dewarp.py path/to/image.jpg
```

### Steps

1. **Load Image**: Click "Load Image" and select your document image
2. **Select Corners**: Click on 4 corner points (any order - they're auto-sorted)
   - Points are numbered 1-4 with visual markers
   - Red filled circles with blue outlines
   - Green lines connect the points
3. **Adjust Points** (Optional):
   - **Zoom**: Use mouse wheel or +/- buttons to zoom in/out
   - **Pan**: Right-click and drag to move around the zoomed image
   - **Drag Points**: Click and drag any point to adjust its position precisely
   - **Fit**: Click "Fit" button to reset zoom and pan
4. **Review Dimensions** (auto-calculated):
   - After selecting 4 points, dimensions are automatically calculated based on point distances
   - Width = average of top and bottom edge lengths
   - Height = average of left and right edge lengths
   - Adjusting points will update dimensions UNTIL you manually edit them
   - Once you manually change width/height, they remain fixed when adjusting points
   - Set DPI (default 300 for high quality)
5. **Apply Transform**: Click "Apply Transform" to process the image
6. **Save Result**: Click "Save Result" to export the transformed image

### Navigation Controls

- **Mouse Wheel**: Zoom in/out at cursor position
- **Right-Click + Drag**: Pan around the zoomed image
- **Left-Click**: Add point or start dragging existing point
- **Zoom Buttons**: +/- buttons for controlled zoom, Fit to reset
- **Zoom Display**: Shows current zoom percentage

### Dimension Settings

Dimensions are **automatically calculated** based on your selected points and specified in **millimeters**:

- **Width (mm)**: Auto-calculated from average of top and bottom edge lengths
- **Height (mm)**: Auto-calculated from average of left and right edge lengths
- **DPI**: Dots per inch for conversion (300 recommended for print quality)

**How it works:**
1. After selecting 4 corner points, the app measures the distances between them
2. It averages opposing sides (top/bottom for width, left/right for height)
3. Converts pixel distances to millimeters based on DPI setting
4. As you drag points to fine-tune, dimensions automatically update
5. Once you manually type in width or height, auto-calculation stops
6. Click "Reset Points" to re-enable auto-calculation

**Pixel Calculation**: `pixels = (mm / 25.4) × DPI`

Example: 210mm @ 300 DPI = 2480 pixels

### Other Controls

- **Reset Points**: Clear all selected corners and start over
- Points are automatically ordered as top-left, top-right, bottom-right, bottom-left

## Tips

- For best results, ensure good lighting and contrast
- The image will be automatically scaled to fit the display window
- The transform works on the original full-resolution image
- Points can be selected in any reasonable order - they will be automatically sorted

## How It Works

The application uses OpenCV's perspective transform (`cv2.getPerspectiveTransform` and `cv2.warpPerspective`) to convert a quadrilateral region into a rectangle. This corrects for camera angles and perspective distortion, making it ideal for scanning documents, receipts, whiteboards, and more.
