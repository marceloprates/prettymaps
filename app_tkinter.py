import tkinter as tk
from tkinter import ttk, colorchooser, filedialog, messagebox
import logging
from matplotlib import pyplot as plt
import sys
import os
import io
import tempfile
from PIL import Image, ImageTk
import subprocess
import json
import threading
import time
import webbrowser
from math import cos, radians
import http.server
import socketserver
from urllib.parse import urlparse, parse_qs
from urllib.request import unquote

# Add repo root to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
import prettymaps

try:
    from geopy.geocoders import Nominatim
    GEOPY_AVAILABLE = True
except ImportError:
    GEOPY_AVAILABLE = False

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
        self.map_html_path = None
        self.last_coords = None
        self.map_selection = None  # Will hold selection from browser
        self.http_server_port = 8765
        self._initial_geocode_done = False  # Flag to prevent multiple updates at startup
        self._preview_update_pending = False  # Flag to debounce preview updates
        
        # Get presets
        self.presets = prettymaps.presets().to_dict()
        
        # Start local HTTP server for map communication
        self._start_http_server()
        
        # Create main container with two columns
        self.main_frame = ttk.Frame(root, padding="0")
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
    
    def _start_http_server(self):
        """Start local HTTP server to receive map selections from browser"""
        app = self
        
        class MapSelectionHandler(http.server.BaseHTTPRequestHandler):
            def _send_cors_headers(self):
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type')

            def do_OPTIONS(self):
                self.send_response(204)
                self._send_cors_headers()
                self.end_headers()

            def do_GET(self):
                if self.path == '/status':
                    # Health check endpoint
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self._send_cors_headers()
                    self.end_headers()
                    self.wfile.write(b'{"status": "ok", "ready": true}')
                    return

                if self.path == '/map':
                    map_path = app.current_map_path
                    if map_path and os.path.exists(map_path):
                        try:
                            with open(map_path, 'rb') as f:
                                content = f.read()
                            self.send_response(200)
                            self.send_header('Content-Type', 'text/html; charset=utf-8')
                            self._send_cors_headers()
                            self.end_headers()
                            self.wfile.write(content)
                        except Exception as e:
                            print(f"[Server] Error serving map HTML: {e}")
                            self.send_response(500)
                            self._send_cors_headers()
                            self.end_headers()
                    else:
                        self.send_response(404)
                        self._send_cors_headers()
                        self.end_headers()
                    return

                self.send_response(404)
                self._send_cors_headers()
                self.end_headers()

            def do_POST(self):
                if self.path == '/confirm':
                    content_length = int(self.headers.get('Content-Length', 0))
                    try:
                        body = self.rfile.read(content_length).decode('utf-8')
                        data = json.loads(body)
                        print(f"[Server] Received map selection: {data}")
                        
                        # Store selection and apply it
                        app.map_selection = data
                        app._apply_map_selection(data)
                        
                        # Send success response
                        self.send_response(200)
                        self.send_header('Content-Type', 'application/json')
                        self._send_cors_headers()
                        self.end_headers()
                        self.wfile.write(b'{"status": "ok"}')
                    except json.JSONDecodeError as e:
                        print(f"[Server] JSON decode error: {e}")
                        self.send_response(400)
                        self.send_header('Content-Type', 'application/json')
                        self._send_cors_headers()
                        self.end_headers()
                        self.wfile.write(b'{"error": "Invalid JSON"}')
                    except Exception as e:
                        print(f"[Server] Error processing selection: {e}")
                        self.send_response(500)
                        self.send_header('Content-Type', 'application/json')
                        self._send_cors_headers()
                        self.end_headers()
                        self.wfile.write(b'{"error": "Server error"}')
                else:
                    self.send_response(404)
                    self._send_cors_headers()
                    self.end_headers()
            
            def log_message(self, format, *args):
                # Suppress default logging
                pass
        
        def run_server():
            try:
                # Allow address reuse for quick restarts
                socketserver.TCPServer.allow_reuse_address = True
                # Bind to all interfaces (0.0.0.0) instead of loopback only
                with socketserver.TCPServer(("0.0.0.0", self.http_server_port), MapSelectionHandler) as httpd:
                    print(f"[Server] HTTP server started on http://localhost:{self.http_server_port}")
                    print(f"[Server] Ready to receive map selections from browser")
                    httpd.serve_forever()
            except OSError as e:
                print(f"[Server] Error starting server (port may be in use): {e}")
                print(f"[Server] Try restarting the app or closing other apps using port {self.http_server_port}")
            except Exception as e:
                print(f"[Server] Unexpected server error: {e}")
        
        # Start server in background thread
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        time.sleep(1)  # Give server more time to start
    
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
        self.location_text.insert("1.0", "Via Alessandro Spagolla 5a, 38051")
        self.location_text.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        # Don't bind key event yet - will be bound after initial geocoding
        
        # Trigger initial geocoding in background
        def initial_geocode():
            if not GEOPY_AVAILABLE:
                self._initial_geocode_done = True
                self.location_text.bind("<KeyRelease>", lambda e: self.update_map_preview())
                return
            
            try:
                location = self.location_text.get("1.0", tk.END).strip()
                from geopy.geocoders import Nominatim
                geolocator = Nominatim(user_agent="prettymaps_app")
                geo_location = geolocator.geocode(location, timeout=10)
                if geo_location:
                    self.last_coords = (geo_location.latitude, geo_location.longitude)
            except Exception as e:
                logging.debug(f"Initial geocode error: {e}")
            finally:
                self._initial_geocode_done = True
                # Now bind the key event for user edits
                self.location_text.bind("<KeyRelease>", lambda e: self.update_map_preview())
                # And trigger initial map preview
                self.update_map_preview()
        
        self.root.after(200, initial_geocode)
        row += 1
        
        # Radius slider
        ttk.Label(scrollable_frame, text="Radius (km):").grid(row=row, column=0, sticky=tk.W, pady=5)
        row += 1
        self.radius_var = tk.DoubleVar(value=0.75)
        self.radius_slider = ttk.Scale(scrollable_frame, from_=0.2, to=5.0, 
                                       variable=self.radius_var, orient=tk.HORIZONTAL)
        self.radius_slider.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=5)
        self.radius_label = ttk.Label(scrollable_frame, text="0.75")
        self.radius_label.grid(row=row, column=1, sticky=tk.W, padx=5)
        self.radius_var.trace_add("write", lambda *args: self.update_radius_label_and_map())
        row += 1
        
        # Circular map checkbox
        self.circular_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(scrollable_frame, text="Circular map", variable=self.circular_var,
                       command=self.update_map_preview).grid(
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
        """Create the right panel with map preview and generated image"""
        right_panel = ttk.Frame(self.main_frame, padding="0")
        right_panel.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        right_panel.rowconfigure(0, weight=0)  # Map preview (minimal)
        right_panel.rowconfigure(1, weight=0)  # Buttons
        right_panel.rowconfigure(2, weight=1)  # Generated image (maximized)
        right_panel.columnconfigure(0, weight=1)
        
        # ===== TOP: MINIMAL MAP PREVIEW =====
        self.map_preview_frame = ttk.LabelFrame(right_panel, text="🗺 Map Preview", padding="5")
        self.map_preview_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=5, pady=5)
        self.map_preview_frame.columnconfigure(0, weight=1)
        
        # Single button to open map
        self.map_btn = ttk.Button(self.map_preview_frame, text="🌐 Open Map in Browser", 
                                  command=self.open_map_browser)
        self.map_btn.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=5, pady=3)
        
        # Minimal status label
        self.map_status_label = ttk.Label(self.map_preview_frame, 
                                          text="Ready to load map...",
                                          justify=tk.CENTER, foreground="gray", font=("TkDefaultFont", 8))
        self.map_status_label.grid(row=1, column=0, sticky=(tk.W, tk.E), padx=5, pady=2)
        
        # ===== MIDDLE: BUTTONS (TIGHT) =====
        buttons_frame = ttk.Frame(right_panel, padding="5")
        buttons_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), padx=5, pady=0)
        buttons_frame.columnconfigure(0, weight=1)
        buttons_frame.columnconfigure(1, weight=1)
        buttons_frame.columnconfigure(2, weight=1)
        
        self.generate_btn = ttk.Button(buttons_frame, text="🗺 Generate", command=self.generate_map)
        self.generate_btn.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=2)
        
        self.download_png_btn = ttk.Button(buttons_frame, text="📥 PNG", 
                                           command=self.download_png, state="disabled")
        self.download_png_btn.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=2)
        
        self.download_svg_btn = ttk.Button(buttons_frame, text="📥 SVG", 
                                           command=self.download_svg, state="disabled")
        self.download_svg_btn.grid(row=0, column=2, sticky=(tk.W, tk.E), padx=2)
        
        # ===== BOTTOM: LARGE GENERATED IMAGE =====
        self.image_frame = ttk.LabelFrame(right_panel, text="Generated Map", padding="5")
        self.image_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        self.image_frame.rowconfigure(0, weight=1)
        self.image_frame.columnconfigure(0, weight=1)
        
        # Canvas for image display
        self.image_canvas = tk.Canvas(self.image_frame, bg="white")
        self.image_canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Show placeholder image
        self.show_placeholder()
        
        # Store map file path
        self.current_map_path = None
    
    def update_color_pickers(self):
        """Update color pickers based on current preset and number of colors"""
        # Clear existing color widgets
        for widget in self.color_widgets:
            widget.destroy()
        self.color_widgets = []
        
        # Get palette from current preset
        preset_name = self.preset_var.get()
        try:
            style = prettymaps.preset(preset_name).params["style"]
            palette = (
                style["building"]["palette"]
                if "building" in style and "palette" in style["building"]
                else ["#433633", "#FF5E5B"]
            )
        except Exception:
            palette = ["#433633", "#FF5E5B"]
        
        # Update number of colors if needed
        num_colors = self.num_colors_var.get()
        
        # Create color picker buttons, preserving existing custom colors
        for i in range(num_colors):
            # Use existing custom color if available, otherwise use palette default
            if i not in self.custom_palette:
                self.custom_palette[i] = palette[i % len(palette)]
            color = self.custom_palette[i]
            
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
            # Update only the specific button background
            # Find the button widget for this index
            button_index = idx * 3 + 2  # Each color has frame, label, button
            if button_index < len(self.color_widgets):
                widget = self.color_widgets[button_index]
                if isinstance(widget, tk.Button) and widget.winfo_exists():
                    widget.config(bg=color[1])
    
    def update_radius_label_and_map(self):
        """Update radius label and map preview when radius changes"""
        self.radius_label.config(text=f"{self.radius_var.get():.2f}")
        self.update_map_preview()
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
        except Exception as e:
            logging.debug(f"Failed to show placeholder image: {e}")
    
    def open_map_browser(self):
        """Open the current map preview in default browser"""
        if self.current_map_path and os.path.exists(self.current_map_path):
            map_url = f"http://localhost:{self.http_server_port}/map"
            webbrowser.open(map_url)
            # Start monitoring for user confirmation
            self._monitor_map_selection()
        else:
            messagebox.showinfo("Info", "Generate a map preview first by entering a location")
    
    def update_map_preview(self):
        """Update the OpenStreetMap preview based on location input"""
        if not GEOPY_AVAILABLE:
            self.map_status_label.config(text="Install geopy for map preview\npip install geopy folium", 
                                        foreground="red")
            return
        
        # Debounce: if already pending, skip
        if self._preview_update_pending:
            return
        
        self._preview_update_pending = True
        
        try:
            location = self.location_text.get("1.0", tk.END).strip()
            if not location:
                self._preview_update_pending = False
                return
            
            # Update status
            self.map_status_label.config(text="Loading map...", foreground="blue")
            self.root.update_idletasks()
            
            # Run in thread to not block UI
            thread = threading.Thread(target=self._geocode_and_update_map, args=(location,))
            thread.daemon = True
            thread.start()
            
        except Exception as e:
            logging.error(f"Error updating map preview: {e}")
            self.map_status_label.config(text=f"Error: {str(e)[:50]}", foreground="red")
            self._preview_update_pending = False
    
    def _geocode_and_update_map(self, location):
        """Geocode location and update map (runs in background thread)"""
        try:
            import folium
            
            # Geocode the location
            geolocator = Nominatim(user_agent="prettymaps_app")
            self.map_status_label.config(text="Geocoding location...", foreground="blue")
            geo_location = geolocator.geocode(location, timeout=10)
            
            if not geo_location:
                self.root.after(0, lambda: self.map_status_label.config(
                    text=f"Location not found: {location}", foreground="red"))
                self._preview_update_pending = False
                return
            
            # Store coords
            self.last_coords = (geo_location.latitude, geo_location.longitude)
            
            # Create map
            self.map_status_label.config(text="Creating map...", foreground="blue")
            m = folium.Map(
                location=[geo_location.latitude, geo_location.longitude],
                zoom_start=14,
                tiles="OpenStreetMap"
            )
            
            # Get radius and circular setting
            radius_km = self.radius_var.get()
            is_circular = self.circular_var.get()
            
            # Add draggable marker (red, at center)
            folium.Marker(
                location=[geo_location.latitude, geo_location.longitude],
                popup=f"<b>{location}</b><br>Radius: {radius_km:.2f} km<br>Draggable marker",
                icon=folium.Icon(color="red", icon="info-sign"),
                draggable=True
            ).add_to(m)
            
            # Add interactive JavaScript with shape drawing
            self._add_interactive_map_js(m, is_circular, radius_km)
            
            # Save to temp
            temp_dir = tempfile.gettempdir()
            map_path = os.path.join(temp_dir, "preview_map.html")
            m.save(map_path)
            
            # Store path and update status on main thread
            self.current_map_path = map_path
            shape_text = "🔷 Square" if not is_circular else "⭕ Circle"
            self.root.after(0, lambda: self.map_status_label.config(
                text=f"✓ {location} | {shape_text} | {radius_km:.2f}km",
                foreground="darkgreen"))
            
        except Exception as e:
            logging.error(f"Error in geocoding: {e}")
            self.root.after(0, lambda: self.map_status_label.config(
                text=f"Error: {str(e)[:40]}", foreground="red"))
        finally:
            self._preview_update_pending = False
    
    def _add_interactive_map_js(self, m, is_circular, radius_km):
        """Add JavaScript to handle map interactions with shape preview"""
        import folium
        
        shape_type = "circle" if is_circular else "rectangle"
        radius_m = radius_km * 1000
        server_url = f"http://localhost:{self.http_server_port}"
        num_colors = self.num_colors_var.get() if hasattr(self, "num_colors_var") else 2
        palette = [self.custom_palette.get(i, "#433633") for i in range(num_colors)]
        palette_json = json.dumps(palette)
        
        # Get page size, dpi, and layers
        page_size = self.page_size_var.get() if hasattr(self, "page_size_var") else "A4"
        dpi = self.dpi_var.get() if hasattr(self, "dpi_var") else 100
        layers_dict = {}
        if hasattr(self, "layer_vars"):
            for k, v in self.layer_vars.items():
                layers_dict[k] = v.get()
        layers_json = json.dumps(layers_dict)
        
        js_code = f"""
        <script>
        var shapeLayer = null;
        var mapConfig = {{
            radiusKm: {radius_km},
            radiusM: {radius_m},
            isCircular: {str(is_circular).lower()},
            currentLat: null,
            currentLng: null,
            numColors: {num_colors},
            colors: {palette_json},
            pageSize: "{page_size}",
            dpi: {dpi},
            layers: {layers_json}
        }};
        
        setTimeout(function() {{
            var map = null;
            
            // Find leaflet map
            var containers = document.querySelectorAll('.leaflet-container');
            if (containers.length > 0) {{
                map = containers[0].__leaflet_map || containers[0]._leaflet_map;
            }}
            if (!map) {{
                for (var key in window) {{
                    if (window[key] && window[key]._map) {{
                        map = window[key]._map;
                        break;
                    }}
                }}
            }}
            
            if (!map) return;
            
            // Store initial marker position
            map.eachLayer(function(layer) {{
                if (layer._latlng) {{
                    mapConfig.currentLat = layer._latlng.lat;
                    mapConfig.currentLng = layer._latlng.lng;
                }}
            }});
            
            function drawShape() {{
                if (shapeLayer) map.removeLayer(shapeLayer);
                
                if (!mapConfig.currentLat || !mapConfig.currentLng) return;
                
                var lat = mapConfig.currentLat;
                var lng = mapConfig.currentLng;
                var radiusM = mapConfig.radiusM;
                var isCirc = mapConfig.isCircular;
                
                if (isCirc) {{
                    shapeLayer = L.circle([lat, lng], {{
                        radius: radiusM,
                        color: 'blue',
                        fill: true,
                        fillColor: 'blue',
                        fillOpacity: 0.2,
                        weight: 2
                    }}).addTo(map);
                }} else {{
                    var latDelta = (radiusM / 111000);
                    var lngDelta = (radiusM / (111000 * Math.cos(lat * Math.PI / 180)));
                    
                    var bounds = [
                        [lat - latDelta, lng - lngDelta],
                        [lat + latDelta, lng + lngDelta]
                    ];
                    
                    shapeLayer = L.rectangle(bounds, {{
                        color: 'blue',
                        fill: true,
                        fillColor: 'blue',
                        fillOpacity: 0.2,
                        weight: 2
                    }}).addTo(map);
                }}
            }}
            
            // Update shape when marker moves
            map.eachLayer(function(layer) {{
                if (layer.setLatLng) {{
                    layer.on('dragend', function(e) {{
                        var pos = e.target.getLatLng();
                        mapConfig.currentLat = pos.lat;
                        mapConfig.currentLng = pos.lng;
                        drawShape();
                    }});
                }}
            }});
            
            // Handle map clicks
            map.on('click', function(e) {{
                mapConfig.currentLat = e.latlng.lat;
                mapConfig.currentLng = e.latlng.lng;
                
                map.eachLayer(function(layer) {{
                    if (layer.setLatLng) {{
                        layer.setLatLng([e.latlng.lat, e.latlng.lng]);
                    }}
                }});
                
                drawShape();
            }});
            
            drawShape();
            
            // Add control panel (radius, circular, colors, page size, dpi, layers)
            var settingsDiv = L.DomUtil.create('div', 'leaflet-bar leaflet-control');
            settingsDiv.style.backgroundColor = 'white';
            settingsDiv.style.padding = '10px';
            settingsDiv.style.borderRadius = '6px';
            settingsDiv.style.minWidth = '240px';
            settingsDiv.style.maxHeight = '600px';
            settingsDiv.style.overflowY = 'auto';
            settingsDiv.style.boxShadow = '0 1px 4px rgba(0,0,0,0.2)';
            settingsDiv.style.fontSize = '12px';
            
            var layersHtml = '';
            if (mapConfig.layers && Object.keys(mapConfig.layers).length > 0) {{
                layersHtml = '<div style="margin-top:10px; padding-top:10px; border-top:1px solid #ccc;">';
                layersHtml += '<div style="font-weight:bold;margin-bottom:6px;">Layers</div>';
                for (var lkey in mapConfig.layers) {{
                    var checked = mapConfig.layers[lkey] ? 'checked' : '';
                    var lname = lkey.charAt(0).toUpperCase() + lkey.slice(1);
                    layersHtml += '<div style="margin:3px 0;"><label><input type="checkbox" class="layerCheckbox" data-layer="' + lkey + '" ' + checked + ' /> ' + lname + '</label></div>';
                }}
                layersHtml += '</div>';
            }}
            
            settingsDiv.innerHTML = '' +
                '<div style="font-weight:bold;margin-bottom:8px;">Map Settings</div>' +
                '<div style="margin-bottom:6px;">Radius (km): <span id="radiusVal">' + mapConfig.radiusKm.toFixed(2) + '</span></div>' +
                '<input id="radiusInput" type="range" min="0.2" max="5" step="0.1" value="' + mapConfig.radiusKm + '" style="width:100%;" />' +
                '<div style="margin:8px 0 6px 0;">' +
                    '<label><input id="circularInput" type="checkbox" ' + (mapConfig.isCircular ? 'checked' : '') + ' /> Circular</label>' +
                '</div>' +
                '<div style="margin-bottom:6px;">Page Size: <select id="pageSizeInput" style="width:100%;">' +
                    '<option value="A4" ' + (mapConfig.pageSize === 'A4' ? 'selected' : '') + '>A4</option>' +
                    '<option value="A5" ' + (mapConfig.pageSize === 'A5' ? 'selected' : '') + '>A5</option>' +
                    '<option value="Square" ' + (mapConfig.pageSize === 'Square' ? 'selected' : '') + '>Square</option>' +
                '</select></div>' +
                '<div style="margin-bottom:6px;">DPI: <input id="dpiInput" type="number" min="50" max="300" step="10" value="' + mapConfig.dpi + '" style="width:100%;" /></div>' +
                '<div style="margin-bottom:6px;">Colors: <input id="colorCount" type="number" min="1" max="20" value="' + mapConfig.numColors + '" style="width:60px;" /></div>' +
                '<div id="colorList" style="display:flex;flex-wrap:wrap;gap:6px;"></div>' +
                layersHtml;

            var settingsControl = L.control({{position: 'topright'}});
            settingsControl.onAdd = function() {{ return settingsDiv; }};
            settingsControl.addTo(map);

            // Prevent map click/drag when interacting with controls
            L.DomEvent.disableClickPropagation(settingsDiv);
            L.DomEvent.disableScrollPropagation(settingsDiv);

            function renderColorInputs() {{
                var list = settingsDiv.querySelector('#colorList');
                if (!list) return;
                list.innerHTML = '';
                for (var i = 0; i < mapConfig.numColors; i++) {{
                    if (!mapConfig.colors[i]) {{
                        mapConfig.colors[i] = '#433633';
                    }}
                    var wrap = document.createElement('div');
                    var input = document.createElement('input');
                    input.type = 'color';
                    input.value = mapConfig.colors[i];
                    input.setAttribute('data-index', i);
                    input.style.width = '32px';
                    input.style.height = '24px';
                    input.style.border = 'none';
                    input.style.padding = '0';
                    input.oninput = function(e) {{
                        var idx = parseInt(e.target.getAttribute('data-index'));
                        mapConfig.colors[idx] = e.target.value;
                    }};
                    wrap.appendChild(input);
                    list.appendChild(wrap);
                }}
            }}

            renderColorInputs();

            var radiusInput = settingsDiv.querySelector('#radiusInput');
            var radiusVal = settingsDiv.querySelector('#radiusVal');
            if (radiusInput) {{
                radiusInput.oninput = function(e) {{
                    var val = parseFloat(e.target.value || mapConfig.radiusKm);
                    mapConfig.radiusKm = val;
                    mapConfig.radiusM = val * 1000;
                    if (radiusVal) radiusVal.textContent = val.toFixed(2);
                    drawShape();
                }};
            }}

            var circularInput = settingsDiv.querySelector('#circularInput');
            if (circularInput) {{
                circularInput.onchange = function(e) {{
                    mapConfig.isCircular = e.target.checked;
                    drawShape();
                }};
            }}

            var colorCountInput = settingsDiv.querySelector('#colorCount');
            if (colorCountInput) {{
                colorCountInput.onchange = function(e) {{
                    var val = parseInt(e.target.value || mapConfig.numColors);
                    if (isNaN(val) || val < 1) val = 1;
                    if (val > 20) val = 20;
                    mapConfig.numColors = val;
                    renderColorInputs();
                }};
            }}

            var pageSizeInput = settingsDiv.querySelector('#pageSizeInput');
            if (pageSizeInput) {{
                pageSizeInput.onchange = function(e) {{
                    mapConfig.pageSize = e.target.value;
                }};
            }}

            var dpiInput = settingsDiv.querySelector('#dpiInput');
            if (dpiInput) {{
                dpiInput.onchange = function(e) {{
                    var val = parseInt(e.target.value || mapConfig.dpi);
                    if (isNaN(val) || val < 50) val = 50;
                    if (val > 300) val = 300;
                    mapConfig.dpi = val;
                }};
            }}

            var layerCheckboxes = settingsDiv.querySelectorAll('.layerCheckbox');
            for (var i = 0; i < layerCheckboxes.length; i++) {{
                layerCheckboxes[i].onchange = function(e) {{
                    var layer = e.target.getAttribute('data-layer');
                    mapConfig.layers[layer] = e.target.checked;
                }};
            }}

            // Add OK button
            var div = L.DomUtil.create('div', 'leaflet-bar leaflet-control');
            div.style.backgroundColor = 'white';
            div.style.padding = '10px';
            div.style.borderRadius = '5px';
            div.style.cursor = 'pointer';
            div.style.fontWeight = 'bold';
            div.style.color = 'green';
            div.style.fontSize = '14px';
            div.innerHTML = '✓ CONFIRM';
            L.DomEvent.disableClickPropagation(div);
            L.DomEvent.disableScrollPropagation(div);
            
            div.onclick = function() {{
                var data = {{
                    lat: mapConfig.currentLat,
                    lng: mapConfig.currentLng,
                    radius: mapConfig.radiusKm,
                    circular: mapConfig.isCircular,
                    num_colors: mapConfig.numColors,
                    colors: mapConfig.colors,
                    page_size: mapConfig.pageSize,
                    dpi: mapConfig.dpi,
                    layers: mapConfig.layers
                }};
                
                console.log('Sending selection:', data);
                console.log('Server URL: {server_url}/confirm');
                div.innerHTML = '⏳ Sending...';
                div.style.pointerEvents = 'none';
                div.style.opacity = '0.5';
                
                // Send to local server with retry logic
                var sendWithRetry = function(attempt, maxAttempts) {{
                    if (!attempt) attempt = 1;
                    if (!maxAttempts) maxAttempts = 5;
                    
                    console.log('Attempt ' + attempt + ' of ' + maxAttempts);
                    
                    var timeoutId = null;
                    var fetchPromise = fetch('{server_url}/confirm', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify(data)
                    }});
                    
                    // Manual timeout since fetch doesn't support timeout parameter
                    var timeoutPromise = new Promise(function(resolve, reject) {{
                        timeoutId = setTimeout(function() {{
                            reject(new Error('Request timeout'));
                        }}, 5000);
                    }});
                    
                    Promise.race([fetchPromise, timeoutPromise])
                    .then(function(response) {{
                        clearTimeout(timeoutId);
                        if (response.ok) {{
                            console.log('Selection sent successfully');
                            setTimeout(function() {{ window.close(); }}, 500);
                        }} else {{
                            throw new Error('Server returned ' + response.status);
                        }}
                    }})
                    .catch(function(err) {{
                        clearTimeout(timeoutId);
                        console.error('Attempt ' + attempt + ' failed:', err.message);
                        if (attempt < maxAttempts) {{
                            var delayMs = 500 * attempt;
                            console.log('Retrying in ' + delayMs + 'ms...');
                            setTimeout(function() {{
                                sendWithRetry(attempt + 1, maxAttempts);
                            }}, delayMs);
                        }} else {{
                            div.innerHTML = '✓ CONFIRM';
                            div.style.pointerEvents = 'auto';
                            div.style.opacity = '1';
                            console.error('All ' + maxAttempts + ' attempts failed');
                            alert('Failed to send selection after ' + maxAttempts + ' attempts.\\n\\nMake sure the app is still running.\\n\\nError: ' + err.message);
                        }}
                    }});
                }};
                
                sendWithRetry(1, 5);
            }};
            
            var control = L.control({{position: 'topleft'}});
            control.onAdd = function() {{ return div; }};
            control.addTo(map);
            
        }}, 800);
        </script>
        """
        m.get_root().html.add_child(folium.Element(js_code))
    
    def _start_monitoring_map_updates(self):
        """Monitor for changes from the map browser and update GUI"""
        def monitor():
            last_update = 0
            
            while True:
                time.sleep(0.3)
                temp_dir = tempfile.gettempdir()
                
                # Try to read from a shared file
                data_file = os.path.join(temp_dir, "map_updates.json")
                if os.path.exists(data_file):
                    try:
                        mtime = os.path.getmtime(data_file)
                        if mtime > last_update:
                            with open(data_file, 'r') as f:
                                data = json.load(f)
                            last_update = mtime
                            self._apply_map_updates(data)
                            os.remove(data_file)  # Clean up
                    except:
                        pass
        
        thread = threading.Thread(target=monitor, daemon=True)
        thread.start()
    
    def _monitor_map_selection(self):
        """Monitor for user selection from map browser (now handled by HTTP server)"""
        # The HTTP server will directly call _apply_map_selection when data arrives
        # This method is kept for compatibility but the actual work is done by the server
        pass
    
    def _apply_map_selection(self, data):
        """Apply the user's selection from the map"""
        try:
            if 'lat' in data and 'lng' in data:
                # Update location to selected coordinates
                new_location = self._reverse_geocode(data['lat'], data['lng'])
                if new_location:
                    self.root.after(0, lambda: self.location_text.delete("1.0", tk.END))
                    self.root.after(0, lambda: self.location_text.insert("1.0", new_location))
                
                # Update radius if provided
                if 'radius' in data:
                    self.root.after(0, lambda: self.radius_var.set(data['radius']))
                
                # Update circular setting if provided
                if 'circular' in data:
                    self.root.after(0, lambda: self.circular_var.set(data['circular']))

                # Update color palette if provided
                if 'colors' in data or 'num_colors' in data:
                    def apply_palette():
                        colors = data.get('colors') or []
                        num_colors = data.get('num_colors') or len(colors) or self.num_colors_var.get()
                        try:
                            num_colors = int(num_colors)
                        except Exception:
                            num_colors = self.num_colors_var.get()
                        if num_colors < 1:
                            num_colors = 1
                        if num_colors > 20:
                            num_colors = 20
                        self.num_colors_var.set(num_colors)
                        # Preserve palette order
                        new_palette = {}
                        for i in range(num_colors):
                            if i < len(colors) and isinstance(colors[i], str):
                                new_palette[i] = colors[i]
                            else:
                                new_palette[i] = self.custom_palette.get(i, "#433633")
                        self.custom_palette = new_palette
                        self.update_color_pickers()

                    self.root.after(0, apply_palette)

                # Update page size if provided
                if 'page_size' in data:
                    ps = data.get('page_size', 'A4')
                    if ps in ['A4', 'A5', 'Square']:
                        self.root.after(0, lambda: self.page_size_var.set(ps))

                # Update DPI if provided
                if 'dpi' in data:
                    try:
                        dpi_val = int(data.get('dpi', 100))
                        if 50 <= dpi_val <= 300:
                            self.root.after(0, lambda: self.dpi_var.set(dpi_val))
                    except Exception:
                        pass

                # Update layers if provided
                if 'layers' in data:
                    def apply_layers():
                        layers_dict = data.get('layers', {})
                        if isinstance(layers_dict, dict):
                            for layer_key, layer_var in self.layer_vars.items():
                                if layer_key in layers_dict:
                                    layer_var.set(bool(layers_dict[layer_key]))
                    self.root.after(0, apply_layers)
                
                # Auto-generate the map with new coordinates
                self.root.after(0, self.generate_map)
                
        except Exception as e:
            logging.error(f"Error applying map selection: {e}")
    
    def _reverse_geocode(self, lat, lng):
        """Convert coordinates to location name"""
        try:
            geolocator = Nominatim(user_agent="prettymaps_app")
            location = geolocator.reverse(f"{lat}, {lng}", timeout=5)
            return location.address if location else None
        except:
            return None
    
    def generate_map(self):
        """Generate the map based on current settings"""
        # Disable generate button during processing
        self.generate_btn.config(state="disabled", text="Generating...")
        self.root.update()
        
        try:
            # Get parameters
            query = self.location_text.get("1.0", tk.END).strip()
            if not query:
                messagebox.showwarning("Warning", "Please enter a location")
                self.generate_btn.config(state="normal", text="🗺 Generate")
                return
            
            radius = self.radius_var.get()
            circular = self.circular_var.get()
            selected_preset = self.preset_var.get()
            dpi = self.dpi_var.get()
            
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
            
            # Create figure with user-specified DPI
            fig, ax = plt.subplots(figsize=(width, height), dpi=dpi)
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
            
            # Save to buffer with user-specified DPI
            buf = io.BytesIO()
            plt.savefig(buf, format="png", bbox_inches="tight", dpi=dpi)
            buf.seek(0)
            self.last_image = buf
            
            # Save to file using platform-independent temp directory
            temp_dir = tempfile.gettempdir()
            self.last_png_path = os.path.join(temp_dir, "generated_map.png")
            with open(self.last_png_path, "wb") as f:
                f.write(self.last_image.getbuffer())
            
            # Save SVG with user-specified DPI
            self.last_svg_path = os.path.join(temp_dir, "generated_map_download.svg")
            plt.savefig(self.last_svg_path, format="svg", bbox_inches="tight", dpi=dpi)
            
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
    return app


if __name__ == "__main__":
    main()
