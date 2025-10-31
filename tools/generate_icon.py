"""
Generate dewarp.ico - Icon showing perspective grid with corner points
"""

from PIL import Image, ImageDraw
import math

def create_dewarp_icon(size):
    """Create a single icon at the specified size"""
    # Create image with transparent background
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Colors
    bg_color = (45, 85, 135, 255)  # Blue background
    grid_color = (200, 220, 240, 255)  # Light grid
    point_color = (255, 80, 80, 255)  # Red points
    line_color = (80, 255, 80, 255)  # Green lines

    # Padding
    pad = size * 0.1

    # Draw background rounded square
    corner_radius = int(size * 0.15)
    draw.rounded_rectangle([0, 0, size-1, size-1], radius=corner_radius, fill=bg_color)

    # Draw a perspective grid (asymmetric quadrilateral)
    # Define the warped quadrilateral (asymmetric - like a document at an angle)
    margin = pad * 1.5

    # Asymmetric quadrilateral points (simulating realistic perspective)
    tl = (margin + size * 0.15, margin + size * 0.05)  # top-left (slightly down and right)
    tr = (size - margin - size * 0.05, margin)  # top-right (higher, less right offset)
    br = (size - margin, size - margin - size * 0.08)  # bottom-right (higher)
    bl = (margin + size * 0.05, size - margin)  # bottom-left (more right)

    # Draw grid lines inside the quadrilateral
    grid_lines = 4
    for i in range(1, grid_lines):
        t = i / grid_lines
        # Horizontal lines
        left_x = bl[0] + t * (tl[0] - bl[0])
        left_y = bl[1] + t * (tl[1] - bl[1])
        right_x = br[0] + t * (tr[0] - br[0])
        right_y = br[1] + t * (tr[1] - br[1])

        line_width = max(1, size // 80)
        draw.line([left_x, left_y, right_x, right_y], fill=grid_color, width=line_width)

        # Vertical lines
        bottom_x = bl[0] + t * (br[0] - bl[0])
        bottom_y = bl[1] + t * (br[1] - bl[1])
        top_x = tl[0] + t * (tr[0] - tl[0])
        top_y = tl[1] + t * (tr[1] - tl[1])

        draw.line([bottom_x, bottom_y, top_x, top_y], fill=grid_color, width=line_width)

    # Draw the outline of the quadrilateral in green
    outline_width = max(2, size // 40)
    draw.line([tl, tr], fill=line_color, width=outline_width)
    draw.line([tr, br], fill=line_color, width=outline_width)
    draw.line([br, bl], fill=line_color, width=outline_width)
    draw.line([bl, tl], fill=line_color, width=outline_width)

    # Draw corner points (red circles)
    point_radius = max(2, size // 20)
    for pt in [tl, tr, br, bl]:
        # Outer circle
        draw.ellipse([pt[0]-point_radius, pt[1]-point_radius,
                     pt[0]+point_radius, pt[1]+point_radius],
                    fill=point_color, outline=(255, 255, 255, 255),
                    width=max(1, size // 100))

    return img

def generate_icon():
    """Generate multi-resolution .ico file"""
    import os

    # Common icon sizes for Windows .ico
    sizes = [256, 128, 64, 48, 32, 16]

    images = []
    for size in sizes:
        print(f"Generating {size}x{size} icon...")
        img = create_dewarp_icon(size)
        images.append(img)

    # Create assets directory if it doesn't exist
    assets_dir = os.path.join(os.path.dirname(__file__), "..", "assets")
    os.makedirs(assets_dir, exist_ok=True)

    # Save as .ico file with multiple sizes
    output_path = os.path.join(assets_dir, "dewarp.ico")
    images[0].save(output_path, format='ICO', sizes=[(s, s) for s in sizes])
    print(f"\nIcon saved as {output_path}")

    # Also save a PNG preview of the largest size
    preview_path = os.path.join(assets_dir, "dewarp_icon_preview.png")
    images[0].save(preview_path, format='PNG')
    print(f"Preview saved as {preview_path}")

if __name__ == "__main__":
    generate_icon()
