"""
Dewarp - Interactive Perspective Transform Tool
Allows user to select 4 corner points and apply perspective transform
Features: Zoom, Pan, Drag-and-Drop points, Millimeter dimensions
"""

import argparse
import cv2
import numpy as np
import tkinter as tk
from tkinter import filedialog, ttk
from PIL import Image, ImageTk


class DewarpGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Dewarp")

        # State variables
        self.image = None
        self.display_image = None
        self.original_image = None
        self.original_file_path = None
        self.points = []
        self.transformed_image = None

        # Zoom and pan variables
        self.zoom_level = 1.0
        self.pan_offset = [0.0, 0.0]
        self.base_scale_factor = 1.0
        self.canvas_width = 500  # Initial placeholder
        self.canvas_height = 400  # Initial placeholder
        self.needs_initial_center = False

        # Drag state
        self.dragging_point = None
        self.panning = False
        self.drag_start = None

        # DPI for mm conversion (default 300 DPI)
        self.dpi = 300

        # Track if user has manually set dimensions
        self.dimensions_manually_set = False
        self._updating_dimensions = False  # Flag to prevent callback during auto-update

        # Setup UI
        self.setup_ui()

    def setup_ui(self):
        # Calculate canvas dimensions based on screen size
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        # Use 45% of screen width for each canvas, 70% of screen height
        self.canvas_width = int(screen_width * 0.45)
        self.canvas_height = int(screen_height * 0.7)

        # Set minimum sizes
        self.canvas_width = max(400, self.canvas_width)
        self.canvas_height = max(300, self.canvas_height)

        # Control Panel
        control_frame = ttk.Frame(self.root, padding="10")
        control_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Row 0 - Main controls
        ttk.Button(control_frame, text="Load Image", command=self.load_image).grid(row=0, column=0, padx=5)
        ttk.Button(control_frame, text="Reset Points", command=self.reset_points).grid(row=0, column=1, padx=5)

        self.transform_btn = ttk.Button(control_frame, text="Apply Transform", command=self.apply_transform, state=tk.DISABLED)
        self.transform_btn.grid(row=0, column=2, padx=5)

        self.save_btn = ttk.Button(control_frame, text="Save Result", command=self.save_image, state=tk.DISABLED)
        self.save_btn.grid(row=0, column=3, padx=5)

        # Zoom controls
        ttk.Label(control_frame, text="Zoom:").grid(row=0, column=4, padx=(20, 5))
        ttk.Button(control_frame, text="+", command=self.zoom_in, width=3).grid(row=0, column=5, padx=2)
        ttk.Button(control_frame, text="-", command=self.zoom_out, width=3).grid(row=0, column=6, padx=2)
        ttk.Button(control_frame, text="Fit", command=self.zoom_fit, width=4).grid(row=0, column=7, padx=2)

        self.zoom_label = ttk.Label(control_frame, text="100%", width=6)
        self.zoom_label.grid(row=0, column=8, padx=5)

        # Row 1 - Dimension controls
        ttk.Label(control_frame, text="Output Dimensions:").grid(row=1, column=0, padx=5, pady=(10, 5), sticky=tk.W)

        ttk.Label(control_frame, text="Width (mm):").grid(row=1, column=1, padx=5, sticky=tk.E)
        self.width_var = tk.StringVar(value="")  # Empty until points selected
        self.width_var.trace_add('write', self.on_dimension_changed)
        self.width_entry = ttk.Entry(control_frame, textvariable=self.width_var, width=8)
        self.width_entry.grid(row=1, column=2, padx=5)

        ttk.Label(control_frame, text="Height (mm):").grid(row=1, column=3, padx=5, sticky=tk.E)
        self.height_var = tk.StringVar(value="")  # Empty until points selected
        self.height_var.trace_add('write', self.on_dimension_changed)
        self.height_entry = ttk.Entry(control_frame, textvariable=self.height_var, width=8)
        self.height_entry.grid(row=1, column=4, padx=5)

        ttk.Label(control_frame, text="DPI:").grid(row=1, column=5, padx=5, sticky=tk.E)
        self.dpi_var = tk.StringVar(value="300")
        self.dpi_entry = ttk.Entry(control_frame, textvariable=self.dpi_var, width=6)
        self.dpi_entry.grid(row=1, column=6, padx=5)

        # Status Label
        self.status_label = ttk.Label(control_frame, text="Load an image to begin")
        self.status_label.grid(row=2, column=0, columnspan=7, pady=10)

        # Canvas Frame
        canvas_container = ttk.Frame(self.root)
        canvas_container.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Main Canvas for original image
        left_frame = ttk.Frame(canvas_container)
        left_frame.grid(row=0, column=0, padx=5, pady=5, sticky=(tk.W, tk.E, tk.N, tk.S))

        self.canvas = tk.Canvas(left_frame, bg='gray', cursor="cross",
                               width=self.canvas_width, height=self.canvas_height,
                               highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=False)

        # Bind events
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        self.canvas.bind("<Button-3>", self.on_canvas_right_click)
        self.canvas.bind("<B3-Motion>", self.on_canvas_pan)
        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)
        self.canvas.bind("<Configure>", self.on_canvas_resize)

        # Result Canvas
        right_frame = ttk.Frame(canvas_container)
        right_frame.grid(row=0, column=1, padx=5, pady=5, sticky=(tk.W, tk.E, tk.N, tk.S))

        self.result_canvas = tk.Canvas(right_frame, bg='gray',
                                       width=self.canvas_width, height=self.canvas_height,
                                       highlightthickness=0)
        self.result_canvas.pack(fill=tk.BOTH, expand=False)
        self.result_canvas.bind("<Configure>", self.on_result_canvas_resize)

        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)
        canvas_container.columnconfigure(0, weight=1)
        canvas_container.columnconfigure(1, weight=1)
        canvas_container.rowconfigure(0, weight=1)

    def mm_to_pixels(self, mm):
        """Convert millimeters to pixels based on DPI"""
        try:
            dpi = int(self.dpi_var.get())
        except ValueError:
            dpi = 300
        return int((mm / 25.4) * dpi)

    def on_dimension_changed(self, *args):
        """Called when width or height field is modified"""
        # Only mark as manually set if we're not programmatically updating
        if not self._updating_dimensions:
            self.dimensions_manually_set = True

    def zoom_in(self, center_x=None, center_y=None):
        """Zoom in by 20%, centered on given point"""
        if center_x is None:
            center_x = self.canvas_width / 2
        if center_y is None:
            center_y = self.canvas_height / 2

        old_zoom = self.zoom_level
        self.zoom_level = min(self.zoom_level * 1.2, 10.0)

        # Adjust pan to keep the cursor position fixed
        if self.image is not None:
            zoom_ratio = self.zoom_level / old_zoom
            self.pan_offset[0] = center_x - (center_x - self.pan_offset[0]) * zoom_ratio
            self.pan_offset[1] = center_y - (center_y - self.pan_offset[1]) * zoom_ratio

        self.update_zoom_display()
        self.display_on_canvas()

    def zoom_out(self, center_x=None, center_y=None):
        """Zoom out by 20%, centered on given point"""
        if center_x is None:
            center_x = self.canvas_width / 2
        if center_y is None:
            center_y = self.canvas_height / 2

        old_zoom = self.zoom_level
        self.zoom_level = max(self.zoom_level / 1.2, 0.1)

        # Adjust pan to keep the cursor position fixed
        if self.image is not None:
            zoom_ratio = self.zoom_level / old_zoom
            self.pan_offset[0] = center_x - (center_x - self.pan_offset[0]) * zoom_ratio
            self.pan_offset[1] = center_y - (center_y - self.pan_offset[1]) * zoom_ratio

        self.update_zoom_display()
        self.display_on_canvas()

    def zoom_fit(self):
        """Reset zoom to fit image in canvas"""
        self.zoom_level = 1.0
        self.pan_offset = [0.0, 0.0]
        self.needs_initial_center = True
        self.update_zoom_display()
        self.display_on_canvas()

    def update_zoom_display(self):
        """Update zoom percentage label"""
        zoom_pct = int(self.zoom_level * self.base_scale_factor * 100)
        self.zoom_label.config(text=f"{zoom_pct}%")

    def on_mouse_wheel(self, event):
        """Handle mouse wheel zoom centered on cursor"""
        if self.image is None:
            return

        if event.delta > 0:
            self.zoom_in(event.x, event.y)
        else:
            self.zoom_out(event.x, event.y)

    def on_canvas_resize(self, event):
        """Handle canvas resize events"""
        # Update canvas dimensions when window is resized
        new_width = event.width
        new_height = event.height

        # Only update if dimensions actually changed
        if new_width != self.canvas_width or new_height != self.canvas_height:
            self.canvas_width = new_width
            self.canvas_height = new_height

            # Redisplay the image with new dimensions
            if self.image is not None:
                # Recalculate and center the image for the new canvas size
                self.needs_initial_center = True
                self.zoom_level = 1.0
                self.display_on_canvas()

    def on_result_canvas_resize(self, event):
        """Handle result canvas resize events"""
        # Redisplay the result image if it exists
        if self.transformed_image is not None:
            self.display_result()

    def on_canvas_right_click(self, event):
        """Start panning with right mouse button"""
        self.drag_start = (event.x, event.y)

    def on_canvas_pan(self, event):
        """Pan the image with right mouse button"""
        if self.drag_start and self.image is not None:
            dx = event.x - self.drag_start[0]
            dy = event.y - self.drag_start[1]
            self.pan_offset[0] += dx
            self.pan_offset[1] += dy
            self.drag_start = (event.x, event.y)
            self.display_on_canvas()

    def load_image(self):
        file_path = filedialog.askopenfilename(
            title="Select Image",
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp"), ("All files", "*.*")]
        )

        if file_path:
            self.load_image_from_path(file_path)

    def load_image_from_path(self, file_path):
        """Load an image from the given file path"""
        # Load image with OpenCV
        self.original_image = cv2.imread(file_path)
        if self.original_image is None:
            self.status_label.config(text="Error: Could not load image")
            return

        # Store the original file path for save dialog
        self.original_file_path = file_path

        # Convert BGR to RGB for display
        self.image = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2RGB)

        # Reset state
        self.points = []
        self.transformed_image = None
        self.zoom_level = 1.0
        self.pan_offset = [0.0, 0.0]
        self.needs_initial_center = True

        # Clear dimension fields and reset manual flag
        self._updating_dimensions = True
        self.width_var.set("")
        self.height_var.set("")
        self._updating_dimensions = False
        self.dimensions_manually_set = False

        # Display the image
        self.display_on_canvas()
        self.status_label.config(text="Click 4 corners (drag to adjust). Drag to pan, scroll to zoom.")

    def display_on_canvas(self):
        if self.image is None:
            return

        height, width = self.image.shape[:2]

        # Calculate base scale to fit canvas (with small margin)
        scale_w = self.canvas_width / width
        scale_h = self.canvas_height / height
        self.base_scale_factor = min(scale_w, scale_h) * 0.98  # 98% to ensure it fits

        # Apply zoom
        effective_scale = self.base_scale_factor * self.zoom_level

        new_width = int(width * effective_scale)
        new_height = int(height * effective_scale)

        # Resize for display
        display_image = cv2.resize(self.image, (new_width, new_height), interpolation=cv2.INTER_AREA)

        # Create canvas-sized image with background
        canvas_image = np.full((self.canvas_height, self.canvas_width, 3), 64, dtype=np.uint8)

        # Center the image on initial load or fit
        if self.needs_initial_center:
            # Calculate centering offset to position image in middle of canvas
            center_x = (self.canvas_width - new_width) / 2.0
            center_y = (self.canvas_height - new_height) / 2.0
            self.pan_offset = [center_x, center_y]
            self.needs_initial_center = False

        # Calculate positions for placing the image on canvas
        x_offset = int(max(0, self.pan_offset[0]))
        y_offset = int(max(0, self.pan_offset[1]))

        # Calculate which part of the display image to show
        img_x_start = int(max(0, -self.pan_offset[0]))
        img_y_start = int(max(0, -self.pan_offset[1]))

        # Calculate how much of the image can fit on canvas
        img_x_end = int(min(new_width, img_x_start + self.canvas_width - x_offset))
        img_y_end = int(min(new_height, img_y_start + self.canvas_height - y_offset))

        # Place the visible portion of the image on canvas
        if img_y_end > img_y_start and img_x_end > img_x_start:
            visible_portion = display_image[img_y_start:img_y_end, img_x_start:img_x_end]
            h, w = visible_portion.shape[:2]
            canvas_image[y_offset:y_offset+h, x_offset:x_offset+w] = visible_portion

        # Draw points and lines on the canvas (not on the resized image)
        # This ensures they're drawn in canvas coordinates
        for i in range(len(self.points)):
            if i < len(self.points) - 1 or len(self.points) == 4:
                next_i = (i + 1) % len(self.points)
                pt1_x = int(self.points[i][0] * effective_scale + self.pan_offset[0])
                pt1_y = int(self.points[i][1] * effective_scale + self.pan_offset[1])
                pt2_x = int(self.points[next_i][0] * effective_scale + self.pan_offset[0])
                pt2_y = int(self.points[next_i][1] * effective_scale + self.pan_offset[1])

                # Only draw if within canvas bounds
                if (0 <= pt1_x < self.canvas_width and 0 <= pt1_y < self.canvas_height and
                    0 <= pt2_x < self.canvas_width and 0 <= pt2_y < self.canvas_height):
                    cv2.line(canvas_image, (pt1_x, pt1_y), (pt2_x, pt2_y), (0, 255, 0), 2)

        # Draw points on top
        for i, pt in enumerate(self.points):
            pt_x = int(pt[0] * effective_scale + self.pan_offset[0])
            pt_y = int(pt[1] * effective_scale + self.pan_offset[1])

            # Only draw if within canvas bounds (with some margin for visibility)
            if -20 <= pt_x < self.canvas_width + 20 and -20 <= pt_y < self.canvas_height + 20:
                # Outer circle
                cv2.circle(canvas_image, (pt_x, pt_y), 10, (0, 0, 255), 2)
                # Inner filled circle
                cv2.circle(canvas_image, (pt_x, pt_y), 6, (255, 0, 0), -1)
                # Label
                cv2.putText(canvas_image, str(i+1), (pt_x+12, pt_y-12),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

        # Convert to PhotoImage
        img_pil = Image.fromarray(canvas_image)
        self.photo = ImageTk.PhotoImage(image=img_pil)

        # Update canvas
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)

        self.update_zoom_display()

    def get_point_at_position(self, x, y, threshold=15):
        """Find if there's a point near the given position"""
        effective_scale = self.base_scale_factor * self.zoom_level

        for i, pt in enumerate(self.points):
            scaled_x = pt[0] * effective_scale + self.pan_offset[0]
            scaled_y = pt[1] * effective_scale + self.pan_offset[1]

            distance = np.sqrt((x - scaled_x)**2 + (y - scaled_y)**2)
            if distance < threshold:
                return i
        return None

    def on_canvas_click(self, event):
        if self.image is None:
            return

        # Check if clicking on existing point
        point_idx = self.get_point_at_position(event.x, event.y)

        if point_idx is not None:
            # Start dragging this point
            self.dragging_point = point_idx
            self.drag_start = (event.x, event.y)
            self.canvas.config(cursor="hand2")
        elif len(self.points) < 4:
            # Add new point
            effective_scale = self.base_scale_factor * self.zoom_level

            # Convert canvas click coordinates to image coordinates
            # Account for the pan offset
            x = (event.x - self.pan_offset[0]) / effective_scale
            y = (event.y - self.pan_offset[1]) / effective_scale

            # Clamp to image bounds
            x = max(0, min(x, self.image.shape[1] - 1))
            y = max(0, min(y, self.image.shape[0] - 1))

            self.points.append((x, y))
            self.display_on_canvas()

            if len(self.points) == 4:
                self.calculate_output_dimensions()
                self.status_label.config(text="All 4 points selected. Dimensions calculated. Adjust by dragging or click 'Apply Transform'.")
                self.transform_btn.config(state=tk.NORMAL)
            else:
                labels = ["top-left", "top-right", "bottom-right", "bottom-left"]
                self.status_label.config(text=f"Point {len(self.points)}/4 added. Suggest: {labels[len(self.points)]}")
        else:
            # All 4 points already placed, start panning
            self.panning = True
            self.drag_start = (event.x, event.y)
            self.canvas.config(cursor="fleur")

    def on_canvas_drag(self, event):
        if self.image is None:
            return

        if self.dragging_point is not None:
            # Update point position
            effective_scale = self.base_scale_factor * self.zoom_level

            # Convert canvas drag coordinates to image coordinates
            x = (event.x - self.pan_offset[0]) / effective_scale
            y = (event.y - self.pan_offset[1]) / effective_scale

            # Clamp to image bounds
            x = max(0, min(x, self.image.shape[1] - 1))
            y = max(0, min(y, self.image.shape[0] - 1))

            self.points[self.dragging_point] = (x, y)
            self.display_on_canvas()
        elif self.panning and self.drag_start:
            # Pan the image
            dx = event.x - self.drag_start[0]
            dy = event.y - self.drag_start[1]
            self.pan_offset[0] += dx
            self.pan_offset[1] += dy
            self.drag_start = (event.x, event.y)
            self.display_on_canvas()

    def on_canvas_release(self, event):
        if self.dragging_point is not None:
            self.dragging_point = None
            self.drag_start = None
            self.canvas.config(cursor="cross")
            # Recalculate dimensions after dragging a point
            if len(self.points) == 4:
                self.calculate_output_dimensions()
        elif self.panning:
            self.panning = False
            self.drag_start = None
            self.canvas.config(cursor="cross")

    def reset_points(self):
        self.points = []
        self.transformed_image = None
        self.transform_btn.config(state=tk.DISABLED)
        self.save_btn.config(state=tk.DISABLED)
        self.result_canvas.delete("all")

        # Clear dimension fields and reset manual flag
        self._updating_dimensions = True
        self.width_var.set("")
        self.height_var.set("")
        self._updating_dimensions = False
        self.dimensions_manually_set = False

        if self.image is not None:
            self.display_on_canvas()
            self.status_label.config(text="Points reset. Click 4 corner points to begin.")

    def order_points(self, pts):
        """Order points as: top-left, top-right, bottom-right, bottom-left"""
        pts = np.array(pts, dtype="float32")

        # Sort by y-coordinate (top to bottom)
        sorted_by_y = pts[np.argsort(pts[:, 1])]

        # Top two points
        top_pts = sorted_by_y[:2]
        top_pts = top_pts[np.argsort(top_pts[:, 0])]  # Sort by x
        tl, tr = top_pts

        # Bottom two points
        bottom_pts = sorted_by_y[2:]
        bottom_pts = bottom_pts[np.argsort(bottom_pts[:, 0])]  # Sort by x
        bl, br = bottom_pts

        return np.array([tl, tr, br, bl], dtype="float32")

    def calculate_output_dimensions(self):
        """Calculate output dimensions based on the distances between selected points"""
        if len(self.points) != 4:
            return

        # Don't recalculate if user has manually set dimensions
        if self.dimensions_manually_set:
            return

        # Order the points
        rect = self.order_points(self.points)
        (tl, tr, br, bl) = rect

        # Calculate distances between points (in pixels)
        top_width = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
        bottom_width = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
        left_height = np.sqrt(((bl[0] - tl[0]) ** 2) + ((bl[1] - tl[1]) ** 2))
        right_height = np.sqrt(((br[0] - tr[0]) ** 2) + ((br[1] - tr[1]) ** 2))

        # Average the opposing sides
        avg_width_pixels = (top_width + bottom_width) / 2.0
        avg_height_pixels = (left_height + right_height) / 2.0

        # Get current DPI setting
        try:
            dpi = int(self.dpi_var.get())
        except ValueError:
            dpi = 300

        # Convert pixels to millimeters: mm = (pixels / DPI) * 25.4
        width_mm = (avg_width_pixels / dpi) * 25.4
        height_mm = (avg_height_pixels / dpi) * 25.4

        # Update the dimension fields (rounded to nearest mm)
        # Set flag to prevent triggering the manual edit callback
        self._updating_dimensions = True
        self.width_var.set(str(int(round(width_mm))))
        self.height_var.set(str(int(round(height_mm))))
        self._updating_dimensions = False

    def apply_transform(self):
        if len(self.points) != 4:
            self.status_label.config(text="Please select exactly 4 points")
            return

        # Order the points
        rect = self.order_points(self.points)
        (tl, tr, br, bl) = rect

        # Get dimensions in mm and convert to pixels
        try:
            width_mm = float(self.width_var.get())
            height_mm = float(self.height_var.get())
            dpi = int(self.dpi_var.get())
        except ValueError:
            self.status_label.config(text="Invalid dimensions or DPI")
            return

        # Convert mm to pixels
        output_width = self.mm_to_pixels(width_mm)
        output_height = self.mm_to_pixels(height_mm)

        # Destination points
        dst = np.array([
            [0, 0],
            [output_width - 1, 0],
            [output_width - 1, output_height - 1],
            [0, output_height - 1]], dtype="float32")

        # Compute perspective transform
        M = cv2.getPerspectiveTransform(rect, dst)
        self.transformed_image = cv2.warpPerspective(self.original_image, M, (output_width, output_height))

        # Display result
        self.display_result()
        self.status_label.config(text=f"Transform applied! Output: {width_mm}×{height_mm}mm @ {dpi}DPI ({output_width}×{output_height}px)")
        self.save_btn.config(state=tk.NORMAL)

    def display_result(self):
        if self.transformed_image is None:
            return

        # Convert BGR to RGB
        result_rgb = cv2.cvtColor(self.transformed_image, cv2.COLOR_BGR2RGB)

        # Scale to fit canvas - always scale down if needed, never scale up
        height, width = result_rgb.shape[:2]

        scale_w = self.canvas_width / width
        scale_h = self.canvas_height / height
        scale = min(scale_w, scale_h)  # Remove the 1.0 cap to allow proper scaling

        new_width = int(width * scale)
        new_height = int(height * scale)

        result_display = cv2.resize(result_rgb, (new_width, new_height))

        # Center in canvas
        canvas_image = np.full((self.canvas_height, self.canvas_width, 3), 64, dtype=np.uint8)
        y_offset = (self.canvas_height - new_height) // 2
        x_offset = (self.canvas_width - new_width) // 2
        canvas_image[y_offset:y_offset+new_height, x_offset:x_offset+new_width] = result_display

        # Convert to PhotoImage
        img_pil = Image.fromarray(canvas_image)
        self.result_photo = ImageTk.PhotoImage(image=img_pil)

        # Update canvas
        self.result_canvas.delete("all")
        self.result_canvas.create_image(0, 0, anchor=tk.NW, image=self.result_photo)

    def save_image(self):
        if self.transformed_image is None:
            return

        # Determine default extension from original file
        default_ext = ".jpg"
        if self.original_file_path:
            import os
            _, ext = os.path.splitext(self.original_file_path)
            if ext.lower() in ['.jpg', '.jpeg', '.png', '.bmp']:
                default_ext = ext.lower()
                if default_ext == '.jpeg':
                    default_ext = '.jpg'

        file_path = filedialog.asksaveasfilename(
            defaultextension=default_ext,
            filetypes=[("JPEG", "*.jpg"), ("PNG", "*.png"), ("BMP", "*.bmp"), ("All files", "*.*")]
        )

        if file_path:
            cv2.imwrite(file_path, self.transformed_image)
            self.status_label.config(text=f"Image saved to {file_path}")


def main():
    parser = argparse.ArgumentParser(description='Dewarp - Interactive Perspective Transform Tool')
    parser.add_argument('image', nargs='?', help='Image file to load on startup')
    args = parser.parse_args()

    root = tk.Tk()
    app = DewarpGUI(root)

    # Load image if provided via command line
    if args.image:
        # Ensure UI is fully initialized before loading image
        root.update_idletasks()
        app.load_image_from_path(args.image)

    root.mainloop()


if __name__ == "__main__":
    main()
