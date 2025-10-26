"""
Dewarp - Interactive Perspective Transform Tool
Allows user to select 4 corner points and apply perspective transform
Features: Zoom, Pan, Drag-and-Drop points, Millimeter dimensions
"""

import argparse
import cv2  # Still needed for constants
import cv3
import numpy as np
import tkinter as tk
from tkinter import filedialog, ttk
from PIL import Image, ImageTk


class DewarpGUI:
    def __init__(self, root, dpi=300, units="mm", crop=False):
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

        # DPI for mm conversion (from command line or default 300 DPI)
        self.dpi = dpi
        self.dpi_var = tk.StringVar(value=str(dpi))
        self.dpi_var.trace_add('write', self.on_dpi_changed)

        # Units preference (from command line or default mm)
        self.units = tk.StringVar(value=units)
        self.units.trace_add('write', self.on_units_changed)

        # Crop mode (from command line or default False = transform entire image)
        self.crop_image = tk.BooleanVar(value=crop)

        # Track if user has manually set dimensions
        self.dimensions_manually_set = False
        self._updating_dimensions = False  # Flag to prevent callback during auto-update

        # Setup UI
        self.setup_ui()

    def setup_ui(self):
        # Calculate canvas dimensions based on screen size
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        # Use 45% of screen width for each canvas, 75% of screen height
        self.canvas_width = int(screen_width * 0.45)
        self.canvas_height = int(screen_height * 0.75)

        # Set minimum sizes
        self.canvas_width = max(400, self.canvas_width)
        self.canvas_height = max(300, self.canvas_height)

        # Menu Bar
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # File Menu
        self.file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=self.file_menu)
        self.file_menu.add_command(label="Load Image...", command=self.load_image, accelerator="Ctrl+O")
        self.file_menu.add_command(label="Save Result...", command=self.save_image, accelerator="Ctrl+S", state=tk.DISABLED)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Preferences...", command=self.show_preferences)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Exit", command=self.root.quit, accelerator="Alt+F4")

        # Bind keyboard shortcuts
        self.root.bind('<Control-o>', lambda e: self.load_image())
        self.root.bind('<Control-s>', lambda e: self.save_image() if self.transformed_image else None)

        # Canvas Frame
        canvas_container = ttk.Frame(self.root)
        canvas_container.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Main Canvas for original image
        left_frame = ttk.Frame(canvas_container)
        left_frame.grid(row=0, column=0, padx=5, pady=5, sticky=(tk.W, tk.E, tk.N, tk.S))

        self.canvas = tk.Canvas(left_frame, bg='gray', cursor="cross",
                               width=self.canvas_width, height=self.canvas_height,
                               highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=False)

        # Action buttons overlay (upper left corner of left canvas)
        action_overlay = ttk.Frame(left_frame, relief=tk.RAISED, borderwidth=1)
        action_overlay.place(relx=0.0, rely=0.0, x=5, y=5, anchor=tk.NW)

        ttk.Button(action_overlay, text="Reset", command=self.reset_points, width=6).pack(side=tk.LEFT, padx=1)
        self.transform_btn = ttk.Button(action_overlay, text="Apply", command=self.apply_transform, state=tk.DISABLED, width=6)
        self.transform_btn.pack(side=tk.LEFT, padx=1)

        # Zoom controls overlay (upper right corner of left canvas)
        zoom_overlay = ttk.Frame(left_frame, relief=tk.RAISED, borderwidth=1)
        zoom_overlay.place(relx=1.0, rely=0.0, x=-5, y=5, anchor=tk.NE)

        ttk.Button(zoom_overlay, text="+", command=self.zoom_in, width=3).pack(side=tk.LEFT, padx=1)
        ttk.Button(zoom_overlay, text="-", command=self.zoom_out, width=3).pack(side=tk.LEFT, padx=1)
        ttk.Button(zoom_overlay, text="Fit", command=self.zoom_fit, width=4).pack(side=tk.LEFT, padx=1)
        self.zoom_label = ttk.Label(zoom_overlay, text="100%", width=5)
        self.zoom_label.pack(side=tk.LEFT, padx=3)

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

        # Dimension controls overlay (upper left corner of right canvas)
        dimensions_overlay = ttk.Frame(right_frame, relief=tk.RAISED, borderwidth=1, padding="5")
        dimensions_overlay.place(relx=0.0, rely=0.0, x=5, y=5, anchor=tk.NW)

        self.width_label = ttk.Label(dimensions_overlay, text="Width (mm):", font=('TkDefaultFont', 8))
        self.width_label.grid(row=0, column=0, sticky=tk.E, padx=(0, 3))
        self.width_var = tk.StringVar(value="")  # Empty until points selected
        self.width_var.trace_add('write', self.on_dimension_changed)
        self.width_spinbox = ttk.Spinbox(dimensions_overlay, textvariable=self.width_var, from_=1, to=9999, increment=1, width=8)
        self.width_spinbox.grid(row=0, column=1, padx=3)

        self.height_label = ttk.Label(dimensions_overlay, text="Height (mm):", font=('TkDefaultFont', 8))
        self.height_label.grid(row=0, column=2, sticky=tk.E, padx=(5, 3))
        self.height_var = tk.StringVar(value="")  # Empty until points selected
        self.height_var.trace_add('write', self.on_dimension_changed)
        self.height_spinbox = ttk.Spinbox(dimensions_overlay, textvariable=self.height_var, from_=1, to=9999, increment=1, width=8)
        self.height_spinbox.grid(row=0, column=3, padx=3)

        # Status Bar at bottom
        status_frame = ttk.Frame(self.root, relief=tk.SUNKEN, padding="2")
        status_frame.grid(row=1, column=0, sticky=(tk.W, tk.E))

        self.status_label = ttk.Label(status_frame, text="Load an image to begin", anchor=tk.W)
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # DPI display on the right side of status bar
        self.dpi_display_label = ttk.Label(status_frame, text="DPI: 300", anchor=tk.E)
        self.dpi_display_label.pack(side=tk.RIGHT, padx=10)

        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        canvas_container.columnconfigure(0, weight=1)
        canvas_container.columnconfigure(1, weight=1)
        canvas_container.rowconfigure(0, weight=1)

    def units_to_pixels(self, value):
        """Convert value in current units to pixels based on DPI"""
        try:
            dpi = int(self.dpi_var.get())
        except ValueError:
            dpi = 300

        units = self.units.get()

        if units == "pixels":
            return int(value)
        elif units == "inches":
            return int(value * dpi)
        else:  # mm
            return int((value / 25.4) * dpi)

    def pixels_to_units(self, pixels):
        """Convert pixels to current units based on DPI"""
        try:
            dpi = int(self.dpi_var.get())
        except ValueError:
            dpi = 300

        units = self.units.get()

        if units == "pixels":
            return pixels
        elif units == "inches":
            return pixels / dpi
        else:  # mm
            return (pixels / dpi) * 25.4

    def on_dimension_changed(self, *args):
        """Called when width or height field is modified"""
        # Only mark as manually set if we're not programmatically updating
        if not self._updating_dimensions:
            self.dimensions_manually_set = True

    def on_dpi_changed(self, *args):
        """Called when DPI is modified"""
        try:
            dpi_value = int(self.dpi_var.get())
            self.dpi_display_label.config(text=f"DPI: {dpi_value}")
        except (ValueError, tk.TclError, AttributeError):
            # Ignore errors during initialization or invalid values
            pass

    def on_units_changed(self, *args):
        """Called when units preference is modified"""
        try:
            units = self.units.get()
            # Update dimension labels
            if units == "pixels":
                self.width_label.config(text="Width (px):")
                self.height_label.config(text="Height (px):")
            elif units == "inches":
                self.width_label.config(text="Width (in):")
                self.height_label.config(text="Height (in):")
            else:  # mm
                self.width_label.config(text="Width (mm):")
                self.height_label.config(text="Height (mm):")
        except (tk.TclError, AttributeError):
            # Ignore errors during initialization
            pass

    def show_preferences(self):
        """Show the preferences dialog"""
        # Create modal dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Preferences")
        dialog.transient(self.root)
        dialog.grab_set()

        # Center the dialog
        dialog_width = 350
        dialog_height = 250
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (dialog_width // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (dialog_height // 2)
        dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
        dialog.resizable(False, False)

        # Content frame
        content_frame = ttk.Frame(dialog, padding="20")
        content_frame.pack(fill=tk.BOTH, expand=True)

        # DPI Setting
        ttk.Label(content_frame, text="DPI (Dots Per Inch):").grid(row=0, column=0, sticky=tk.W, pady=10)
        dpi_entry = ttk.Entry(content_frame, textvariable=self.dpi_var, width=10)
        dpi_entry.grid(row=0, column=1, padx=10, pady=10)
        ttk.Label(content_frame, text="(Default: 300)").grid(row=1, column=0, columnspan=2, sticky=tk.W)

        # Units Setting
        ttk.Label(content_frame, text="Measurement Units:").grid(row=2, column=0, sticky=tk.W, pady=(10, 5))
        units_frame = ttk.Frame(content_frame)
        units_frame.grid(row=2, column=1, sticky=tk.W, pady=(10, 5))
        ttk.Radiobutton(units_frame, text="mm", variable=self.units, value="mm").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(units_frame, text="inches", variable=self.units, value="inches").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(units_frame, text="pixels", variable=self.units, value="pixels").pack(side=tk.LEFT, padx=5)

        # Crop Mode Setting
        crop_check = ttk.Checkbutton(
            content_frame,
            text="Crop Image",
            variable=self.crop_image
        )
        crop_check.grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=(15, 5))

        # Button frame
        button_frame = ttk.Frame(content_frame)
        button_frame.grid(row=4, column=0, columnspan=2, pady=(20, 0))

        def on_ok():
            # Validate DPI value
            try:
                dpi_value = int(self.dpi_var.get())
                if dpi_value < 1 or dpi_value > 9999:
                    raise ValueError("DPI must be between 1 and 9999")
            except ValueError:
                self.dpi_var.set("300")
            dialog.destroy()

        def on_cancel():
            dialog.destroy()

        ttk.Button(button_frame, text="OK", command=on_ok, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=on_cancel, width=10).pack(side=tk.LEFT, padx=5)

        # Wait for the dialog to close
        self.root.wait_window(dialog)

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
        self.original_image = cv3.imread(file_path)
        if self.original_image is None:
            self.status_label.config(text="Error: Could not load image")
            return

        # Store the original file path for save dialog
        self.original_file_path = file_path

        # cv3 loads images in RGB by default (no conversion needed)
        self.image = self.original_image

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
        display_image = cv3.resize(self.image, new_width, new_height)

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
                    cv3.line(canvas_image, pt1_x, pt1_y, pt2_x, pt2_y, color=(0, 255, 0), t=2)

        # Draw points on top
        for i, pt in enumerate(self.points):
            pt_x = int(pt[0] * effective_scale + self.pan_offset[0])
            pt_y = int(pt[1] * effective_scale + self.pan_offset[1])

            # Only draw if within canvas bounds (with some margin for visibility)
            if -20 <= pt_x < self.canvas_width + 20 and -20 <= pt_y < self.canvas_height + 20:
                # Outer circle
                cv3.circle(canvas_image, pt_x, pt_y, 10, color=(0, 0, 255), t=2)
                # Inner filled circle
                cv3.circle(canvas_image, pt_x, pt_y, 6, color=(255, 0, 0), fill=True)
                # Label - use cv2 for text as it's simpler
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
        self.file_menu.entryconfig("Save Result...", state=tk.DISABLED)
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

        # Convert pixels to current units
        width_value = self.pixels_to_units(avg_width_pixels)
        height_value = self.pixels_to_units(avg_height_pixels)

        # Update the dimension fields
        # Set flag to prevent triggering the manual edit callback
        self._updating_dimensions = True
        if self.units.get() == "pixels":
            # Pixels - show as integer
            self.width_var.set(str(int(round(width_value))))
            self.height_var.set(str(int(round(height_value))))
        else:
            # mm or inches - show with 1 decimal place
            self.width_var.set(f"{width_value:.1f}")
            self.height_var.set(f"{height_value:.1f}")
        self._updating_dimensions = False

    def apply_transform(self):
        if len(self.points) != 4:
            self.status_label.config(text="Please select exactly 4 points")
            return

        # Order the points
        rect = self.order_points(self.points)
        (tl, tr, br, bl) = rect

        # Get DPI
        try:
            dpi = int(self.dpi_var.get())
        except ValueError:
            dpi = 300

        # Check crop mode
        crop_enabled = self.crop_image.get()
        print(f"DEBUG: crop_image.get() = {crop_enabled}")
        if not crop_enabled:
            # Transform entire image mode (crop unchecked)
            print("DEBUG: Using FULL IMAGE mode (no cropping)")

            # Get dimensions from spinbox (user's real-world measurements)
            try:
                width_value = float(self.width_var.get())
                height_value = float(self.height_var.get())
            except ValueError:
                self.status_label.config(text="Invalid dimensions")
                return

            # Convert to pixels for the quadrilateral
            quad_width = self.units_to_pixels(width_value)
            quad_height = self.units_to_pixels(height_value)

            print(f"DEBUG: User specified quad dimensions: {quad_width}x{quad_height}px")

            # Get original image dimensions
            img_height, img_width = self.original_image.shape[:2]

            # First, create a temporary transform to see where the image corners will end up
            # Map the selected quad to origin with user's specified dimensions
            temp_dst = np.array([
                [0, 0],
                [quad_width - 1, 0],
                [quad_width - 1, quad_height - 1],
                [0, quad_height - 1]], dtype="float32")

            M_temp = cv2.getPerspectiveTransform(rect, temp_dst)

            # Transform the four corners of the original image to see the bounding box
            img_corners = np.array([
                [0, 0],
                [img_width - 1, 0],
                [img_width - 1, img_height - 1],
                [0, img_height - 1]], dtype="float32")

            # Apply transform to each corner
            transformed_corners = cv2.perspectiveTransform(img_corners.reshape(-1, 1, 2), M_temp).reshape(-1, 2)

            # Find bounding box of transformed image
            min_x = int(np.floor(transformed_corners[:, 0].min()))
            max_x = int(np.ceil(transformed_corners[:, 0].max()))
            min_y = int(np.floor(transformed_corners[:, 1].min()))
            max_y = int(np.ceil(transformed_corners[:, 1].max()))

            print(f"DEBUG: Transformed image bounds: x=[{min_x}, {max_x}], y=[{min_y}, {max_y}]")

            # Calculate output canvas size
            output_width = max_x - min_x
            output_height = max_y - min_y

            print(f"DEBUG: Output canvas size: {output_width}x{output_height}px")

            # Adjust destination points to account for negative offsets
            # This ensures the entire transformed image fits in the output
            offset_x = -min_x
            offset_y = -min_y

            dst = np.array([
                [offset_x, offset_y],
                [offset_x + quad_width - 1, offset_y],
                [offset_x + quad_width - 1, offset_y + quad_height - 1],
                [offset_x, offset_y + quad_height - 1]], dtype="float32")

            # Compute final perspective transform
            M = cv2.getPerspectiveTransform(rect, dst)

            # Convert to BGR for warpPerspective, then back to RGB
            original_bgr = cv2.cvtColor(self.original_image, cv2.COLOR_RGB2BGR)
            transformed_bgr = cv2.warpPerspective(original_bgr, M, (output_width, output_height))
            self.transformed_image = cv2.cvtColor(transformed_bgr, cv2.COLOR_BGR2RGB)

            # Calculate output dimensions in mm
            output_width_mm = (output_width / dpi) * 25.4
            output_height_mm = (output_height / dpi) * 25.4

            # Get units abbreviation for display
            units_abbr = "px" if self.units.get() == "pixels" else ("in" if self.units.get() == "inches" else "mm")
            status_msg = f"Transform applied! Output: {output_width_mm:.0f}×{output_height_mm:.0f}mm @ {dpi}DPI ({output_width}×{output_height}px) [Full image, quad={width_value:.1f}×{height_value:.1f}{units_abbr}]"
        else:
            # Crop to selected region mode (original behavior)
            print("DEBUG: Using CROP mode (crop to selected points)")
            # Get dimensions in current units and convert to pixels
            try:
                width_value = float(self.width_var.get())
                height_value = float(self.height_var.get())
            except ValueError:
                self.status_label.config(text="Invalid dimensions")
                return

            # Convert to pixels
            output_width = self.units_to_pixels(width_value)
            output_height = self.units_to_pixels(height_value)

            # Destination points
            dst = np.array([
                [0, 0],
                [output_width - 1, 0],
                [output_width - 1, output_height - 1],
                [0, output_height - 1]], dtype="float32")

            # Compute perspective transform
            M = cv2.getPerspectiveTransform(rect, dst)

            # Convert to BGR for warpPerspective, then back to RGB
            original_bgr = cv2.cvtColor(self.original_image, cv2.COLOR_RGB2BGR)
            transformed_bgr = cv2.warpPerspective(original_bgr, M, (output_width, output_height))
            self.transformed_image = cv2.cvtColor(transformed_bgr, cv2.COLOR_BGR2RGB)

            # Get units abbreviation for display
            units_abbr = "px" if self.units.get() == "pixels" else ("in" if self.units.get() == "inches" else "mm")
            status_msg = f"Transform applied! Output: {width_value:.1f}×{height_value:.1f}{units_abbr} @ {dpi}DPI ({output_width}×{output_height}px)"

        # Display result
        self.display_result()
        self.status_label.config(text=status_msg)
        self.file_menu.entryconfig("Save Result...", state=tk.NORMAL)

    def display_result(self):
        if self.transformed_image is None:
            return

        # cv3 already uses RGB (no conversion needed)
        result_rgb = self.transformed_image

        # Get actual result canvas dimensions
        self.result_canvas.update_idletasks()
        result_canvas_width = self.result_canvas.winfo_width()
        result_canvas_height = self.result_canvas.winfo_height()

        # Fallback to default if canvas not yet realized
        if result_canvas_width <= 1:
            result_canvas_width = self.canvas_width
        if result_canvas_height <= 1:
            result_canvas_height = self.canvas_height

        # Scale to fit canvas - always scale down if needed, never scale up
        height, width = result_rgb.shape[:2]

        # Add small margin to ensure it fits (98% of available space)
        scale_w = (result_canvas_width * 0.98) / width
        scale_h = (result_canvas_height * 0.98) / height
        scale = min(scale_w, scale_h, 1.0)  # Never scale up, always fit within canvas

        new_width = int(width * scale)
        new_height = int(height * scale)

        # Ensure dimensions are at least 1 pixel
        new_width = max(1, new_width)
        new_height = max(1, new_height)

        result_display = cv3.resize(result_rgb, new_width, new_height)

        # Center in canvas
        canvas_image = np.full((result_canvas_height, result_canvas_width, 3), 64, dtype=np.uint8)
        y_offset = max(0, (result_canvas_height - new_height) // 2)
        x_offset = max(0, (result_canvas_width - new_width) // 2)

        # Place the scaled image (should always fit now, but add safety check)
        y_end = min(y_offset + new_height, result_canvas_height)
        x_end = min(x_offset + new_width, result_canvas_width)
        result_h = y_end - y_offset
        result_w = x_end - x_offset

        if result_h > 0 and result_w > 0:
            canvas_image[y_offset:y_end, x_offset:x_end] = result_display[:result_h, :result_w]

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
            # cv3.imwrite expects RGB, which is what we have
            cv3.imwrite(file_path, self.transformed_image)
            self.status_label.config(text=f"Image saved to {file_path}")


def main():
    parser = argparse.ArgumentParser(description='Dewarp - Interactive Perspective Transform Tool')
    parser.add_argument('image', nargs='?', help='Image file to load on startup')
    parser.add_argument('--dpi', type=int, default=300, help='DPI for dimension conversion (default: 300)')
    parser.add_argument('--units', choices=['mm', 'inches', 'pixels'], default='mm',
                        help='Measurement units for dimensions (default: mm)')
    parser.add_argument('--crop', action='store_true',
                        help='Enable crop mode (crop to selected points instead of transforming entire image)')
    args = parser.parse_args()

    root = tk.Tk()
    app = DewarpGUI(root, dpi=args.dpi, units=args.units, crop=args.crop)

    # Load image if provided via command line
    if args.image:
        # Ensure UI is fully initialized before loading image
        root.update_idletasks()
        app.load_image_from_path(args.image)

    root.mainloop()


if __name__ == "__main__":
    main()
