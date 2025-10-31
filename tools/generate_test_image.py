"""
Generate test image for dewarp application testing
Creates a 22x30 cm green background with:
- Rounded corners
- 1 cm grey grid
- Two rectangles (2x3 inches and 7x5 cm) rotated in opposite directions
- Pre-warped with perspective transform
"""

import cv2
import numpy as np
import json

# Configuration
DPI = 300
CM_TO_INCH = 1 / 2.54

# Canvas dimensions
WIDTH_CM = 22
HEIGHT_CM = 30
WIDTH_PX = int(WIDTH_CM * CM_TO_INCH * DPI)
HEIGHT_PX = int(HEIGHT_CM * CM_TO_INCH * DPI)

# Grid spacing
GRID_CM = 1
GRID_PX = int(GRID_CM * CM_TO_INCH * DPI)

# Colors (BGR format for OpenCV)
GREEN_BG = (60, 140, 60)  # Darker green
GREY_GRID = (150, 150, 150)
BLUE_RECT = (200, 100, 50)
RED_RECT = (50, 50, 200)
DARK_GREY_BG = (60, 60, 60)  # Dark grey for warped image background

print(f"Generating test image:")
print(f"  Canvas: {WIDTH_CM}x{HEIGHT_CM} cm ({WIDTH_PX}x{HEIGHT_PX} px @ {DPI} DPI)")
print(f"  Grid spacing: {GRID_CM} cm ({GRID_PX} px)")

# Create base image with dark grey background
image = np.full((HEIGHT_PX, WIDTH_PX, 3), DARK_GREY_BG, dtype=np.uint8)

# Draw rounded rectangle for green background
corner_radius = int(2 * CM_TO_INCH * DPI)  # 2 cm radius
# OpenCV doesn't have a direct rounded rectangle fill, so we'll build it manually
# Create a mask for the rounded rectangle
mask = np.zeros((HEIGHT_PX, WIDTH_PX), dtype=np.uint8)

# Draw the main rectangle body
cv2.rectangle(mask, (corner_radius, 0), (WIDTH_PX - corner_radius, HEIGHT_PX), 255, -1)
cv2.rectangle(mask, (0, corner_radius), (WIDTH_PX, HEIGHT_PX - corner_radius), 255, -1)

# Draw the four corner circles
cv2.circle(mask, (corner_radius, corner_radius), corner_radius, 255, -1)  # top-left
cv2.circle(mask, (WIDTH_PX - corner_radius, corner_radius), corner_radius, 255, -1)  # top-right
cv2.circle(mask, (corner_radius, HEIGHT_PX - corner_radius), corner_radius, 255, -1)  # bottom-left
cv2.circle(mask, (WIDTH_PX - corner_radius, HEIGHT_PX - corner_radius), corner_radius, 255, -1)  # bottom-right

# Apply green color where mask is set
green_layer = np.full((HEIGHT_PX, WIDTH_PX, 3), GREEN_BG, dtype=np.uint8)
image = np.where(mask[:, :, np.newaxis] == 255, green_layer, image)

print("  [OK] Created green background with rounded corners facing outwards")

# Draw grid lines starting 1 cm inside the green border
grid_margin = GRID_PX  # 1 cm margin
for y in range(grid_margin, HEIGHT_PX - grid_margin + 1, GRID_PX):
    cv2.line(image, (grid_margin, y), (WIDTH_PX - grid_margin, y), GREY_GRID, 2)

for x in range(grid_margin, WIDTH_PX - grid_margin + 1, GRID_PX):
    cv2.line(image, (x, grid_margin), (x, HEIGHT_PX - grid_margin), GREY_GRID, 2)

print("  [OK] Drew 1 cm grid starting 1 cm inside border")

# Function to draw rotated rectangle
def draw_rotated_rectangle(img, center, width_px, height_px, angle_deg, color, label):
    """Draw a filled rectangle rotated by angle_deg"""
    # Create rotation matrix
    rect = ((center[0], center[1]), (width_px, height_px), angle_deg)
    box = cv2.boxPoints(rect)
    box = box.astype(int)

    # Draw filled rectangle
    cv2.drawContours(img, [box], 0, color, -1)

    # Draw border
    cv2.drawContours(img, [box], 0, (0, 0, 0), 3)

    # Add label with larger text
    cv2.putText(img, label, (int(center[0] - 70), int(center[1])),
                cv2.FONT_HERSHEY_SIMPLEX, 2.2, (255, 255, 255), 4)

    return box

# Rectangle 1: 2x3 inches, rotated 15 degrees clockwise
rect1_width_px = int(2 * DPI)
rect1_height_px = int(3 * DPI)
rect1_center = (WIDTH_PX // 3, HEIGHT_PX // 3)
rect1_angle = -15  # Negative = clockwise

box1 = draw_rotated_rectangle(image, rect1_center, rect1_width_px, rect1_height_px,
                               rect1_angle, BLUE_RECT, "2x3\"")

print(f"  [OK] Drew rectangle 1: 2x3 inches ({rect1_width_px}x{rect1_height_px} px) at {rect1_angle} deg")

# Rectangle 2: 7x5 cm, rotated 20 degrees counter-clockwise
rect2_width_px = int(7 * CM_TO_INCH * DPI)
rect2_height_px = int(5 * CM_TO_INCH * DPI)
rect2_center = (2 * WIDTH_PX // 3, 2 * HEIGHT_PX // 3)
rect2_angle = 20  # Positive = counter-clockwise

box2 = draw_rotated_rectangle(image, rect2_center, rect2_width_px, rect2_height_px,
                               rect2_angle, RED_RECT, "7x5cm")

print(f"  [OK] Drew rectangle 2: 7x5 cm ({rect2_width_px}x{rect2_height_px} px) at {rect2_angle} deg")

# Create test directory if it doesn't exist
import os
test_dir = os.path.join(os.path.dirname(__file__), "..", "test")
os.makedirs(test_dir, exist_ok=True)

# Save the original (unwarped) image
original_path = os.path.join(test_dir, "test_image_original.png")
cv2.imwrite(original_path, image)
print(f"\n[OK] Saved original image: {original_path}")

# Apply perspective warp
# Define source points (corners of the image)
src_points = np.array([
    [0, 0],                      # top-left
    [WIDTH_PX - 1, 0],          # top-right
    [WIDTH_PX - 1, HEIGHT_PX - 1],  # bottom-right
    [0, HEIGHT_PX - 1]          # bottom-left
], dtype=np.float32)

# Define destination points (perspective-warped trapezoid)
# Make it look like a document photographed at an angle
offset_tl_x = int(WIDTH_PX * 0.15)
offset_tl_y = int(HEIGHT_PX * 0.05)
offset_tr_x = int(WIDTH_PX * 0.05)
offset_tr_y = 0
offset_br_x = 0
offset_br_y = int(HEIGHT_PX * 0.08)
offset_bl_x = int(WIDTH_PX * 0.05)
offset_bl_y = 0

dst_points = np.array([
    [offset_tl_x, offset_tl_y],                          # top-left (inward)
    [WIDTH_PX - 1 - offset_tr_x, offset_tr_y],          # top-right (inward)
    [WIDTH_PX - 1 - offset_br_x, HEIGHT_PX - 1 - offset_br_y],  # bottom-right (inward)
    [offset_bl_x, HEIGHT_PX - 1 - offset_bl_y]          # bottom-left (inward)
], dtype=np.float32)

# Calculate perspective transform matrix
transform_matrix = cv2.getPerspectiveTransform(src_points, dst_points)

# Apply warp with dark grey background
warped_image = cv2.warpPerspective(image, transform_matrix, (WIDTH_PX, HEIGHT_PX),
                                   borderMode=cv2.BORDER_CONSTANT,
                                   borderValue=DARK_GREY_BG)

# Save warped image
warped_path = os.path.join(test_dir, "test_image_warped.png")
cv2.imwrite(warped_path, warped_image)
print(f"[OK] Saved warped image: {warped_path}")

# Save transform matrix and metadata
metadata = {
    "description": "Test image for dewarp application",
    "dimensions": {
        "width_cm": WIDTH_CM,
        "height_cm": HEIGHT_CM,
        "width_px": WIDTH_PX,
        "height_px": HEIGHT_PX,
        "dpi": DPI
    },
    "grid": {
        "spacing_cm": GRID_CM,
        "spacing_px": GRID_PX
    },
    "rectangles": [
        {
            "id": 1,
            "size": "2x3 inches",
            "size_px": [rect1_width_px, rect1_height_px],
            "center_px": list(rect1_center),
            "rotation_deg": rect1_angle,
            "color": "blue"
        },
        {
            "id": 2,
            "size": "7x5 cm",
            "size_px": [rect2_width_px, rect2_height_px],
            "center_px": list(rect2_center),
            "rotation_deg": rect2_angle,
            "color": "red"
        }
    ],
    "transform": {
        "source_points": src_points.tolist(),
        "destination_points": dst_points.tolist(),
        "matrix": transform_matrix.tolist(),
        "inverse_matrix": np.linalg.inv(transform_matrix).tolist()
    }
}

metadata_path = os.path.join(test_dir, "test_image_metadata.json")
with open(metadata_path, 'w') as f:
    json.dump(metadata, f, indent=2)

print(f"[OK] Saved metadata and transform matrix: {metadata_path}")

# Print transform matrix for reference
print(f"\nPerspective Transform Matrix:")
print(transform_matrix)
print(f"\nInverse Transform Matrix (for unwrapping):")
print(np.linalg.inv(transform_matrix))

print("\n" + "="*60)
print("Test image generation complete!")
print("="*60)
print(f"\nFiles created in test/ directory:")
print(f"  1. test_image_original.png - Original unwarped image")
print(f"  2. test_image_warped.png - Pre-warped test image")
print(f"  3. test_image_metadata.json - Complete metadata and transform matrices")
print(f"\nTo test dewarp application:")
print(f"  python dewarp.py test/test_image_warped.png")
print(f"\nExpected result: Selecting the 4 corners should unwarp the image")
print(f"back to the original rectangular shape.")
