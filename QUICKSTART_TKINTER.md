# Quick Start Guide - Tkinter Desktop App

## Installation

1. Clone the repository:
```bash
git clone https://github.com/il-bonvi/prettymaps-custom.git
cd prettymaps-custom
```

2. Install dependencies:
```bash
pip install -e .
```

3. Run the desktop application:
```bash
python app_tkinter.py
```

## First Use

When you launch the application, you'll see:

### Left Panel (Controls)
- **Location field**: Pre-filled with "Stad van de Zon, Heerhugowaard, Netherlands"
- **Radius slider**: Set to 0.75 km
- **Circular map checkbox**: Unchecked
- **Preset dropdown**: Set to "default"
- **Number of colors**: 2 colors
- **Color buttons**: Two color pickers showing the default palette
- **Page Size**: A4
- **DPI**: 100
- **Layer checkboxes**: Several layers pre-selected (Buildings, Streets, etc.)

### Right Panel (Output)
- **Generate button**: Click to create your map
- **Download buttons**: Disabled until you generate a map
- **Display area**: Shows placeholder text "Click 'Generate' to create a map"

## Usage Workflow

1. **Customize your map**:
   - Enter a location in the Location field
   - Adjust the radius with the slider
   - Select a preset or customize colors
   - Choose which layers to include

2. **Generate**:
   - Click the "🗺 Generate" button
   - Wait for the map to be created (status shown in button)
   - View the generated map in the display area

3. **Download**:
   - Click "Download PNG" to save as PNG
   - Click "Download SVG" to save as SVG
   - Choose location in the file dialog

## Tips

- **Color Selection**: Click any color button to open a color picker
- **Scrolling**: The left panel scrolls if your screen is small
- **Window Resizing**: Resize the window to fit your screen
- **Multiple Maps**: Generate as many maps as you want without restarting

## Troubleshooting

### "ModuleNotFoundError: No module named 'tkinter'"
On Linux, install tkinter:
```bash
sudo apt-get install python3-tk
```

On macOS, tkinter is included with Python.

### "Map generation failed"
- Check your internet connection (needed to fetch map data)
- Verify the location name is valid
- Try a different location or smaller radius

### "Cannot save file"
- Ensure you have write permissions to the target directory
- Check that the file isn't already open in another program

## Comparison with Streamlit

If you prefer the web-based interface, you can still use Streamlit:

```bash
pip install -r requirements_streamlit.txt
streamlit run app.py
```

But the Tkinter version offers:
- ⚡ Faster startup
- 🖥️ Native desktop feel
- 📦 Can be packaged as standalone app
- 🔒 No web server required
- 💾 Lower memory usage
