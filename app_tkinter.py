import tkinter as tk
from tkinter import ttk, colorchooser, filedialog, messagebox
import logging
from matplotlib import pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import sys
import os
import io
from PIL import Image, ImageTk

# Add repo root to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
import prettymaps

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class PrettymapsApp:
    def __init__(self, root):
        self.root = root
        self.root.title("prettymaps")
        self.root.geometry("1400x900")
        
        # State variables
        self.last_image = None
        self.last_png_path = None
        self.last_svg_path = None
        self.color_widgets = []
        self.custom_palette = {}
        
        # Get presets
        self.presets = prettymaps.presets().to_dict()
        
        # Create main container with two columns
        self.main_frame = ttk.Frame(root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights for resizing
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.columnconfigure(1, weight=2)
        self.main_frame.rowconfigure(0, weight=1)
        
        # Create left and right panels
        self.create_left_panel()
        self.create_right_panel()
        
        # Initialize default values
        self.update_color_pickers()
    
    def create_left_panel(self):
        """Create the left panel with controls"""
        left_panel = ttk.Frame(self.main_frame, padding="10")
        left_panel.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Make the left panel scrollable
        canvas = tk.Canvas(left_panel, highlightthickness=0)
        scrollbar = ttk.Scrollbar(left_panel, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        row = 0
        
        # Location input
        ttk.Label(scrollable_frame, text="Location:").grid(row=row, column=0, sticky=tk.W, pady=5)
        row += 1
        self.location_text = tk.Text(scrollable_frame, height=3, width=40)
        self.location_text.insert("1.0", "Stad van de Zon, Heerhugowaard, Netherlands")
        self.location_text.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        row += 1
        
        # Radius slider
        ttk.Label(scrollable_frame, text="Radius (km):").grid(row=row, column=0, sticky=tk.W, pady=5)
        row += 1
        self.radius_var = tk.DoubleVar(value=0.75)
        self.radius_slider = ttk.Scale(scrollable_frame, from_=0.5, to=1.5, 
                                       variable=self.radius_var, orient=tk.HORIZONTAL)
        self.radius_slider.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=5)
        self.radius_label = ttk.Label(scrollable_frame, text="0.75")
        self.radius_label.grid(row=row, column=1, sticky=tk.W, padx=5)
        self.radius_var.trace_add("write", lambda *args: self.radius_label.config(text=f"{self.radius_var.get():.2f}"))
        row += 1
        
        # Circular map checkbox
        self.circular_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(scrollable_frame, text="Circular map", variable=self.circular_var).grid(
            row=row, column=0, sticky=tk.W, pady=5
        )
        row += 1
        
        # Preset selector
        ttk.Label(scrollable_frame, text="Select a Preset:").grid(row=row, column=0, sticky=tk.W, pady=5)
        row += 1
        preset_options = list(self.presets["preset"].values())
        self.preset_var = tk.StringVar(value="default")
        self.preset_combo = ttk.Combobox(scrollable_frame, textvariable=self.preset_var, 
                                         values=preset_options, state="readonly", width=37)
        self.preset_combo.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        self.preset_combo.bind("<<ComboboxSelected>>", lambda e: self.update_color_pickers())
        row += 1
        
        # Number of colors
        ttk.Label(scrollable_frame, text="Number of colors:").grid(row=row, column=0, sticky=tk.W, pady=5)
        row += 1
        self.num_colors_var = tk.IntVar(value=2)
        self.num_colors_spinbox = ttk.Spinbox(scrollable_frame, from_=1, to=20, 
                                              textvariable=self.num_colors_var, width=37)
        self.num_colors_spinbox.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        self.num_colors_var.trace_add("write", lambda *args: self.update_color_pickers())
        row += 1
        
        # Color pickers container
        ttk.Label(scrollable_frame, text="Colors:").grid(row=row, column=0, sticky=tk.W, pady=5)
        row += 1
        self.colors_frame = ttk.Frame(scrollable_frame)
        self.colors_frame.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        row += 1
        
        # Page size
        ttk.Label(scrollable_frame, text="Page Size:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.page_size_var = tk.StringVar(value="A4")
        page_size_combo = ttk.Combobox(scrollable_frame, textvariable=self.page_size_var,
                                       values=["A4", "A5", "Square"], state="readonly", width=15)
        page_size_combo.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)
        row += 1
        
        # DPI
        ttk.Label(scrollable_frame, text="DPI:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.dpi_var = tk.IntVar(value=100)
        dpi_spinbox = ttk.Spinbox(scrollable_frame, from_=50, to=300, increment=50,
                                  textvariable=self.dpi_var, width=15)
        dpi_spinbox.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)
        row += 1
        
        # Layer selection
        ttk.Label(scrollable_frame, text="Select Layers:", font=("TkDefaultFont", 10, "bold")).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=(10, 5)
        )
        row += 1
        
        # Get default style for initial layer values
        style = prettymaps.preset("default").params["style"]
        
        self.layer_vars = {}
        layers_list = [
            ("building", "Buildings", "building" in style),
            ("streets", "Streets", "streets" in style),
            ("waterway", "Waterway", "waterway" in style),
            ("water", "Water", "water" in style),
            ("sea", "Sea", "sea" in style),
            ("forest", "Forest", "forest" in style),
            ("green", "Green", "green" in style),
            ("rock", "Rock", "rock" in style),
            ("beach", "Beach", "beach" in style),
            ("parking", "Parking", "parking" in style),
        ]
        
        for layer_key, layer_label, default_val in layers_list:
            var = tk.BooleanVar(value=default_val)
            self.layer_vars[layer_key] = var
            ttk.Checkbutton(scrollable_frame, text=layer_label, variable=var).grid(
                row=row, column=0, sticky=tk.W, pady=2
            )
            row += 1
    
    def create_right_panel(self):
        """Create the right panel with button and image display"""
        right_panel = ttk.Frame(self.main_frame, padding="10")
        right_panel.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        right_panel.rowconfigure(1, weight=1)
        right_panel.columnconfigure(0, weight=1)
        
        # Generate button
        self.generate_btn = ttk.Button(right_panel, text="🗺 Generate", command=self.generate_map)
        self.generate_btn.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=10)
        
        # Download buttons frame
        download_frame = ttk.Frame(right_panel)
        download_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
        download_frame.columnconfigure(0, weight=1)
        download_frame.columnconfigure(1, weight=1)
        
        self.download_png_btn = ttk.Button(download_frame, text="Download PNG", 
                                           command=self.download_png, state="disabled")
        self.download_png_btn.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=5)
        
        self.download_svg_btn = ttk.Button(download_frame, text="Download SVG", 
                                           command=self.download_svg, state="disabled")
        self.download_svg_btn.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        
        # Image display area
        self.image_frame = ttk.Frame(right_panel, relief=tk.SUNKEN, borderwidth=2)
        self.image_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        
        # Canvas for image display
        self.image_canvas = tk.Canvas(self.image_frame, bg="white")
        self.image_canvas.pack(fill=tk.BOTH, expand=True)
        
        # Show placeholder image
        self.show_placeholder()
    
    def update_color_pickers(self):
        """Update color pickers based on current preset and number of colors"""
        # Clear existing color widgets
        for widget in self.color_widgets:
            widget.destroy()
        self.color_widgets = []
        self.custom_palette = {}
        
        # Get palette from current preset
        preset_name = self.preset_var.get()
        try:
            style = prettymaps.preset(preset_name).params["style"]
            palette = (
                style["building"]["palette"]
                if "building" in style and "palette" in style["building"]
                else ["#433633", "#FF5E5B"]
            )
        except:
            palette = ["#433633", "#FF5E5B"]
        
        # Update number of colors if needed
        num_colors = self.num_colors_var.get()
        
        # Create color picker buttons
        for i in range(num_colors):
            color = palette[i % len(palette)]
            self.custom_palette[i] = color
            
            frame = ttk.Frame(self.colors_frame)
            frame.grid(row=i // 4, column=i % 4, padx=5, pady=5)
            
            label = ttk.Label(frame, text=f"Color {i+1:02d}:")
            label.pack()
            
            btn = tk.Button(frame, bg=color, width=5, height=2,
                          command=lambda idx=i: self.pick_color(idx))
            btn.pack()
            
            self.color_widgets.extend([frame, label, btn])
    
    def pick_color(self, idx):
        """Open color picker dialog"""
        current_color = self.custom_palette.get(idx, "#000000")
        color = colorchooser.askcolor(initialcolor=current_color, title=f"Choose Color {idx+1}")
        if color[1]:
            self.custom_palette[idx] = color[1]
            # Update button background
            for widget in self.color_widgets:
                if isinstance(widget, tk.Button) and widget.winfo_exists():
                    # Find the button for this index
                    pass
            self.update_color_pickers()
    
    def show_placeholder(self):
        """Show placeholder image"""
        try:
            # Try to load placeholder from URL or show a simple message
            self.image_canvas.delete("all")
            self.image_canvas.create_text(
                self.image_canvas.winfo_width() // 2,
                self.image_canvas.winfo_height() // 2,
                text="Click 'Generate' to create a map",
                font=("TkDefaultFont", 14),
                fill="gray"
            )
        except:
            pass
    
    def generate_map(self):
        """Generate the map based on current settings"""
        # Disable generate button during processing
        self.generate_btn.config(state="disabled", text="Generating...")
        self.root.update()
        
        try:
            # Get parameters
            query = self.location_text.get("1.0", tk.END).strip()
            radius = self.radius_var.get()
            circular = self.circular_var.get()
            selected_preset = self.preset_var.get()
            
            # Get page size
            page_size = self.page_size_var.get()
            page_sizes = {
                "A4": (8.27, 11.69),
                "A5": (5.83, 8.27),
                "Square": (8.27, 8.27),
            }
            width, height = page_sizes[page_size]
            
            # Get layers
            layers = {k: (False if not v.get() else {}) for k, v in self.layer_vars.items()}
            
            # Create figure
            fig, ax = plt.subplots(figsize=(width, height), dpi=300)
            prettymaps.plot(
                query,
                radius=1000 * radius,
                circle=circular,
                layers=layers,
                style={"building": {"palette": list(self.custom_palette.values())}},
                figsize=(width, height),
                preset=selected_preset,
                show=False,
                ax=ax,
            )
            
            # Save to buffer
            buf = io.BytesIO()
            plt.savefig(buf, format="png", bbox_inches="tight", dpi=150)
            buf.seek(0)
            self.last_image = buf
            
            # Save to file
            self.last_png_path = "/tmp/generated_map.png"
            with open(self.last_png_path, "wb") as f:
                f.write(self.last_image.getbuffer())
            
            # Save SVG
            self.last_svg_path = "/tmp/generated_map_download.svg"
            plt.savefig(self.last_svg_path, format="svg", bbox_inches="tight", dpi=150)
            
            plt.close(fig)
            
            # Display image
            self.display_image()
            
            # Enable download buttons
            self.download_png_btn.config(state="normal")
            self.download_svg_btn.config(state="normal")
            
            messagebox.showinfo("Success", "Map generated successfully!")
            
        except Exception as e:
            logging.error(f"Error generating map: {e}")
            messagebox.showerror("Error", f"Failed to generate map: {str(e)}")
        
        finally:
            # Re-enable generate button
            self.generate_btn.config(state="normal", text="🗺 Generate")
    
    def display_image(self):
        """Display the generated image"""
        if self.last_image:
            try:
                self.last_image.seek(0)
                pil_image = Image.open(self.last_image)
                
                # Resize to fit canvas
                canvas_width = self.image_canvas.winfo_width()
                canvas_height = self.image_canvas.winfo_height()
                
                if canvas_width > 1 and canvas_height > 1:
                    # Calculate scaling to fit
                    img_width, img_height = pil_image.size
                    scale = min(canvas_width / img_width, canvas_height / img_height)
                    new_width = int(img_width * scale)
                    new_height = int(img_height * scale)
                    
                    pil_image = pil_image.resize((new_width, new_height), Image.LANCZOS)
                
                # Convert to PhotoImage
                photo = ImageTk.PhotoImage(pil_image)
                
                # Display on canvas
                self.image_canvas.delete("all")
                self.image_canvas.create_image(
                    canvas_width // 2, canvas_height // 2,
                    image=photo, anchor=tk.CENTER
                )
                
                # Keep a reference to prevent garbage collection
                self.image_canvas.image = photo
                
            except Exception as e:
                logging.error(f"Error displaying image: {e}")
    
    def download_png(self):
        """Download PNG file"""
        if self.last_png_path and os.path.exists(self.last_png_path):
            query = self.location_text.get("1.0", tk.END).strip().replace(" ", "_")
            filename = filedialog.asksaveasfilename(
                defaultextension=".png",
                initialfile=f"{query}.png",
                filetypes=[("PNG files", "*.png"), ("All files", "*.*")]
            )
            if filename:
                import shutil
                shutil.copy(self.last_png_path, filename)
                messagebox.showinfo("Success", f"PNG saved to {filename}")
    
    def download_svg(self):
        """Download SVG file"""
        if self.last_svg_path and os.path.exists(self.last_svg_path):
            query = self.location_text.get("1.0", tk.END).strip().replace(" ", "_")
            filename = filedialog.asksaveasfilename(
                defaultextension=".svg",
                initialfile=f"{query}.svg",
                filetypes=[("SVG files", "*.svg"), ("All files", "*.*")]
            )
            if filename:
                import shutil
                shutil.copy(self.last_svg_path, filename)
                messagebox.showinfo("Success", f"SVG saved to {filename}")


def main():
    root = tk.Tk()
    app = PrettymapsApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
