# Dewarp

An interactive perspective transform tool for correcting image distortion. Select 4 corner points on a distorted image and dewarp will automatically straighten and correct the perspective. If real world dimensions (mm, inch or pixels) are known, they can be added on the right page.

![Dewarp Screenshot](assets/Clipboard01.png)

## Features

- **Interactive Point Selection**: Click to select 4 corner points on your document
- **Drag-and-Drop Adjustment**: Click and drag any point to fine-tune its position
- **Zoom & Pan**: Mouse wheel zoom (centered on cursor) and right-click/left-click pan for precise point placement
- **Auto-Calculated Dimensions**: Automatically calculates output dimensions from selected points
- **Flexible Units**: Output size in millimeters, inches, or pixels with configurable DPI
- **Real-time Visual Feedback**: Enhanced point markers with numbers and green connecting lines
- **Two Transform Modes**:
  - **Full Image Mode** (default): Transforms entire image, keeping everything in frame
  - **Crop Mode**: Crops to selected quadrilateral only
- **Side-by-Side View**: View original and transformed images simultaneously
- **Save Results**: Export transformed images maintaining original file format (JPG/PNG/BMP)
- **Preferences Dialog**: Configure DPI, units, and crop mode settings

## Installation

### Option 1: Using requirements.txt (Traditional)

```bash
pip install -r requirements.txt
```

### Option 2: Using pyproject.toml (Modern)

```bash
pip install -e .
```

### Dependencies

- **opencv-python** (cv2): Advanced perspective transforms, color conversion, text rendering
- **cv3**: Pythonic OpenCV wrapper for basic I/O and drawing operations
- **numpy**: Numerical operations and array handling
- **Pillow**: GUI image display

## Usage

### Quick Start

```bash
# Start with file dialog
python dewarp.py

# Or load an image directly
python dewarp.py path/to/image.jpg

# Use test image
python dewarp.py test/test_image_warped.png
```

### Command Line Options

```bash
python dewarp.py [image] [options]

Arguments:
  image                    Path to image file (optional, will prompt if not provided)

Options:
  --dpi <value>           Set DPI for dimension conversion (default: 300)
  --units <mm|inches|pixels>  Set measurement units (default: mm)
  --crop                  Enable crop mode to crop to selected points
                         (default: transform entire image)
```

**Examples:**

```bash
# Use inches with 150 DPI
python dewarp.py --units inches --dpi 150 image.jpg

# Crop mode with pixels
python dewarp.py --crop --units pixels image.jpg

# High resolution scan mode
python dewarp.py --dpi 600 --units mm document.jpg
```

### Interactive Workflow

1. **Load Image**:
   - Click `File → Load Image` or press `Ctrl+O`
   - Or provide image path as command line argument

2. **Select Corners**:
   - Click on 4 corner points (any order - they're auto-sorted)
   - Points are numbered 1-4 with visual markers
   - Red filled circles with blue outlines
   - Green lines connect the points

3. **Adjust Points** (Optional):
   - **Zoom In/Out**: Mouse wheel or `+`/`-` buttons
   - **Zoom to Fit**: Click `Fit` button
   - **Pan**: Right-click and drag, or left-click drag after 4 points placed
   - **Drag Points**: Click and drag any point to adjust precisely
   - **Current Zoom**: Displayed as percentage in upper-right

4. **Review Dimensions** (auto-calculated):
   - After selecting 4 points, dimensions are calculated from point distances
   - Width = average of top and bottom edge lengths
   - Height = average of left and right edge lengths
   - Dimensions update as you drag points (until manually edited)
   - Manual edits lock the dimensions

5. **Configure Settings** (Optional):
   - Click `File → Preferences` to adjust:
     - DPI (dots per inch)
     - Units (mm, inches, or pixels)
     - Crop mode (on/off)

6. **Apply Transform**:
   - Click `Apply` button
   - View result in right pane
   - Status bar shows output dimensions

7. **Save Result**:
   - Click `File → Save Result` or press `Ctrl+S`
   - Choose location and format (JPG/PNG/BMP)

### Keyboard Shortcuts

- `Ctrl+O`: Load Image
- `Ctrl+S`: Save Result (when available)
- `Alt+F4`: Exit

### Mouse Controls

| Action | Effect |
|--------|--------|
| **Left-Click** | Add point (if < 4) or select/drag existing point |
| **Left-Click + Drag** | Pan (after 4 points placed) or drag selected point |
| **Right-Click + Drag** | Pan around the image |
| **Mouse Wheel Up** | Zoom in (centered on cursor) |
| **Mouse Wheel Down** | Zoom out (centered on cursor) |

### Transform Modes

#### Full Image Mode (Default)
Transforms the entire image, treating the selected quadrilateral as a reference area with known dimensions. The full image is dewarped based on this reference, keeping all content in the output.

**Use case**: Scanning a card or document on a larger surface where you want to keep everything in frame.

#### Crop Mode (`--crop` flag)
Crops the output to exactly the selected quadrilateral region, discarding everything outside.

**Use case**: Extracting just the document/card itself.

### Dimension Calculation

Dimensions are **automatically calculated** based on your selected points:

1. After selecting 4 corner points, distances between them are measured
2. Averages opposing sides (top/bottom for width, left/right for height)
3. Converts pixel distances to selected units based on DPI
4. Updates automatically as you drag points
5. Manual editing locks dimensions (click `Reset` to re-enable auto-calc)

**Conversion Formula**:
- `pixels = (mm / 25.4) × DPI`
- `pixels = inches × DPI`

**Example**: 210mm @ 300 DPI = 2,480 pixels

## Project Structure

```
dewarp/
├── dewarp.py              # Main application
├── README.md              # This file
├── requirements.txt       # Traditional dependency list
├── pyproject.toml         # Modern Python project config
├── assets/                # Application assets
│   └── dewarp.ico        # Application icon
├── tools/                 # Utility scripts
│   ├── generate_icon.py          # Icon generator
│   └── generate_test_image.py    # Test image generator
└── test/                  # Test images (gitignored)
    ├── test_image_original.png   # Original test image
    ├── test_image_warped.png     # Pre-warped test image
    └── test_image_metadata.json  # Transform metadata
```

## Testing

### Test Images

The project includes test image generation:

```bash
# Generate test images
python tools/generate_test_image.py

# Test the application
python dewarp.py test/test_image_warped.png
```

**Test image specs**:
- 22×30 cm green background with rounded corners
- 1 cm grey grid (starting 1 cm from border)
- Two rotated rectangles (2×3 inches and 7×5 cm)
- Pre-warped with known transform matrix
- Dark grey background for realistic appearance

Select the 4 rounded corners and apply the transform to verify the output matches the original.

## Tips for Best Results

- **Lighting**: Ensure good, even lighting and high contrast
- **Point Placement**: Place points precisely on corners using zoom
- **Grid Lines**: Use the grid (if visible) to verify straightness
- **Full Resolution**: Display is scaled but transform uses full resolution
- **Point Order**: Select in any order - automatic sorting handles it
- **Manual Dimensions**: Lock dimensions by typing values before applying transform

## How It Works

Dewarp uses OpenCV's perspective transformation functions to correct distorted images:

1. **Point Selection**: User selects 4 corner points defining a quadrilateral
2. **Point Ordering**: Points are automatically sorted (top-left, top-right, bottom-right, bottom-left)
3. **Dimension Calculation**: Measures distances and calculates real-world dimensions
4. **Transform Matrix**: Computes perspective transform using `cv2.getPerspectiveTransform()`
5. **Image Warping**: Applies transform with `cv2.warpPerspective()`
6. **Output Scaling**: Converts dimensions from selected units to pixels using DPI

The application uses two complementary libraries:
- **cv3**: Pythonic wrapper for image I/O and drawing
- **cv2**: Advanced functions for perspective transforms and color conversion

## Development

### Regenerate Icon

```bash
python tools/generate_icon.py
```

Generates multi-resolution icon (16×16 to 256×256) in `assets/dewarp.ico`.

### Regenerate Test Images

```bash
python tools/generate_test_image.py
```

Creates test images with known transform in `test/` directory.

## License

MIT

## Author

Built with OpenCV, cv3, and tkinter.
