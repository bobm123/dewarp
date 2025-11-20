#!/usr/bin/env python3
"""
Test corner detection on book image to diagnose issues
"""

import cv2
import numpy as np
from PIL import Image

# Load the image (assuming it's been saved as book_test.jpg)
img_path = "book_test.jpg"

try:
    # Load with PIL first
    pil_img = Image.open(img_path)
    img = np.array(pil_img.convert('RGB'))

    print(f"Image shape: {img.shape}")
    print(f"Image dtype: {img.dtype}")

    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

    # Apply Gaussian blur
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # Calculate statistics
    median = np.median(blurred)
    mean = np.mean(blurred)
    std = np.std(blurred)

    print(f"\nGrayscale statistics:")
    print(f"  Median: {median:.1f}")
    print(f"  Mean: {mean:.1f}")
    print(f"  Std Dev: {std:.1f}")
    print(f"  Min: {np.min(blurred)}")
    print(f"  Max: {np.max(blurred)}")

    # Current algorithm (adaptive based on median)
    lower = int(max(0, 0.66 * median))
    upper = int(min(255, 1.33 * median))
    print(f"\nCurrent algorithm Canny thresholds:")
    print(f"  Lower: {lower}")
    print(f"  Upper: {upper}")

    edges1 = cv2.Canny(blurred, lower, upper, apertureSize=3)

    # Try with fixed thresholds (good for light-on-dark)
    edges2 = cv2.Canny(blurred, 50, 150, apertureSize=3)

    # Try with higher thresholds
    edges3 = cv2.Canny(blurred, 100, 200, apertureSize=3)

    # Save edge images for inspection
    cv2.imwrite("edges_adaptive.png", edges1)
    cv2.imwrite("edges_fixed_50_150.png", edges2)
    cv2.imwrite("edges_fixed_100_200.png", edges3)

    print(f"\nEdge detection results saved:")
    print(f"  edges_adaptive.png - using adaptive thresholds")
    print(f"  edges_fixed_50_150.png - using (50, 150)")
    print(f"  edges_fixed_100_200.png - using (100, 200)")

    # Count edge pixels
    print(f"\nEdge pixel counts:")
    print(f"  Adaptive: {np.count_nonzero(edges1)}")
    print(f"  Fixed 50/150: {np.count_nonzero(edges2)}")
    print(f"  Fixed 100/200: {np.count_nonzero(edges3)}")

    # Test contour detection
    for name, edges in [("Adaptive", edges1), ("Fixed 50/150", edges2), ("Fixed 100/200", edges3)]:
        kernel = np.ones((3, 3), np.uint8)
        edges_dilated = cv2.dilate(edges, kernel, iterations=1)
        contours, _ = cv2.findContours(edges_dilated, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)

        print(f"\n{name} - Top 5 contours by area:")
        for i, contour in enumerate(contours[:5]):
            area = cv2.contourArea(contour)
            peri = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
            print(f"  {i+1}. Area: {area:.0f}, Vertices: {len(approx)}")

except FileNotFoundError:
    print(f"Error: Image file '{img_path}' not found")
    print("Please save the book image as 'book_test.jpg' in the current directory")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
