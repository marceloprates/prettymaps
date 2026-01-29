# Tkinter Desktop Application UI

The Tkinter desktop application (`app_tkinter.py`) provides a native desktop interface for prettymaps with the following layout:

## Main Window Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│ prettymaps                                                     [_][□][X]│
├───────────────────────┬─────────────────────────────────────────────┤
│ LEFT PANEL (Controls) │ RIGHT PANEL (Output)                        │
│                       │                                             │
│ Location:             │ ┌─────────────────────────────────────────┐│
│ ┌───────────────────┐ │ │      [🗺 Generate]                      ││
│ │Stad van de Zon... │ │ └─────────────────────────────────────────┘│
│ └───────────────────┘ │                                             │
│                       │ ┌──────────────┬──────────────┐            │
│ Radius (km): 0.75     │ │Download PNG  │Download SVG  │            │
│ [──────●────────]     │ └──────────────┴──────────────┘            │
│                       │                                             │
│ ☐ Circular map        │ ┌─────────────────────────────────────────┐│
│                       │ │                                         ││
│ Select a Preset:      │ │                                         ││
│ ┌───────────────────┐ │ │                                         ││
│ │default          ▼ │ │ │        Map Display Area                 ││
│ └───────────────────┘ │ │                                         ││
│                       │ │                                         ││
│ Number of colors: 2   │ │                                         ││
│ ┌───────────────────┐ │ │                                         ││
│ │2                ↕ │ │ └─────────────────────────────────────────┘│
│ └───────────────────┘ │                                             │
│                       │                                             │
│ Colors:               │                                             │
│ Color 01: [■■■]       │                                             │
│ Color 02: [■■■]       │                                             │
│                       │                                             │
│ Page Size: [A4    ▼]  │                                             │
│ DPI: [100       ↕]    │                                             │
│                       │                                             │
│ Select Layers:        │                                             │
│ ☑ Buildings           │                                             │
│ ☑ Streets             │                                             │
│ ☑ Waterway            │                                             │
│ ☑ Water               │                                             │
│ ☑ Sea                 │                                             │
│ ☑ Forest              │                                             │
│ ☑ Green               │                                             │
│ ☐ Rock                │                                             │
│ ☐ Beach               │                                             │
│ ☐ Parking             │                                             │
│                       │                                             │
└───────────────────────┴─────────────────────────────────────────────┘
```

## Key Features

### Left Panel (Input Controls)
1. **Location** - Multi-line text area for entering the location query
2. **Radius** - Slider control (0.5 to 1.5 km) with live value display
3. **Circular map** - Checkbox to enable circular boundary
4. **Preset selector** - Dropdown to choose from predefined style presets
5. **Number of colors** - Spinbox to adjust the number of colors in the palette
6. **Color pickers** - Grid of color buttons that open color picker dialogs
7. **Page Size** - Dropdown to select output dimensions (A4, A5, Square)
8. **DPI** - Spinbox to set output resolution (50-300)
9. **Layer checkboxes** - Individual toggles for map features

### Right Panel (Output)
1. **Generate button** - Primary action button with map icon
2. **Download buttons** - PNG and SVG export buttons (disabled until map is generated)
3. **Image display area** - Large canvas showing the generated map or placeholder

## Comparison with Streamlit Version

| Feature | Streamlit | Tkinter |
|---------|-----------|---------|
| Interface Type | Web-based | Native desktop |
| Layout | Two columns | Two panels |
| Color Picker | Native color picker | System color chooser dialog |
| Responsiveness | Auto-resizing | Resizable window |
| Dependencies | streamlit + web browser | tkinter (built-in) + Pillow |
| Startup Time | ~5-10 seconds | <1 second |
| Platform | Cross-platform (browser) | Cross-platform (native) |
| Distribution | Requires server | Standalone executable possible |

## Technical Implementation

- **Framework**: Python's built-in tkinter library
- **Image Display**: PIL (Pillow) for image handling and display
- **Scrolling**: Left panel is scrollable for smaller screens
- **State Management**: Class-based state management (similar to Streamlit session state)
- **File Handling**: Native file dialogs for saving PNG/SVG files
- **Execution**: Synchronous UI on main thread with status updates during generation

## Running the Application

```bash
# Install dependencies
pip install -r requirements.txt

# Run the desktop application
python app_tkinter.py
```

## Benefits of Desktop Version

1. **Faster startup** - No web server required
2. **Native feel** - Uses system-native widgets and dialogs
3. **Offline usage** - Works without internet (except for OSM data)
4. **Lower resource usage** - No browser overhead
5. **Easy distribution** - Can be packaged as standalone executable with PyInstaller
6. **Better integration** - Native file dialogs and system notifications
