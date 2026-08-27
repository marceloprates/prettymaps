import streamlit as st
import logging
from matplotlib import pyplot as plt
import sys
import os
import tempfile
import io


def download_svg():
    """
    Creates additional map in SVG format
    """
    fig_path = os.path.join(tempfile.gettempdir(), "generated_map.svg")
    plt.savefig(fig_path, format="svg", bbox_inches="tight", dpi=150)
    return fig_path


# Set Streamlit to use the wide layout
st.set_page_config(layout="wide")

# Add repo root to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
import prettymaps

# Initialize session state for last_image
if "last_image" not in st.session_state:
    st.session_state.last_image = None

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

presets = prettymaps.presets().to_dict()

# Set the title of the app
st.title("prettymaps")

cols = st.columns([1, 2])
with cols[0]:
    query = st.text_area(
        "Location", value="Stad van de Zon, Heerhugowaard, Netherlands", height=86
    )
    radius = st.slider("Radius (km)", 0.5, 1.5, 0.75, step=0.25)
    circular = st.checkbox("Circular map", value=False)

    # Preset selector
    preset_options = list(presets["preset"].values())
    selected_preset = st.selectbox(
        "Select a Preset", preset_options, index=preset_options.index("default")
    )

    # Add input for number of colors
    style = prettymaps.preset(selected_preset).params["style"]
    palette = (
        style["building"]["palette"]
        if "building" in style and "palette" in style["building"]
        else ["#433633", "#FF5E5B"]
    )
    num_colors = st.number_input(
        "Number of colors", min_value=1, value=len(palette), step=1
    )

    custom_palette = {}
    color_cols = st.columns(len(palette))
    for i in range(len(palette) // 1):  # Calculate the number of rows needed
        for j, col in enumerate(color_cols):
            idx = i * 4 + j
            if idx < num_colors:
                color = col.color_picker(
                    f"Color {idx + 1:02d}", palette[idx % len(palette)]
                )
                custom_palette[idx] = color

    # Add page size options
    page_size_col, dpi_col = st.columns(2)
    with page_size_col:
        page_size = st.selectbox(
            "Page Size",
            ["A4", "A5", "Square"],
            index=0,
            # , "A3", "A2", "A1", "Custom"], index=0
        )
    with dpi_col:
        dpi = st.number_input("DPI", min_value=50, max_value=300, value=100, step=50)

    if page_size == "Custom":
        width = st.number_input("Custom Width (inches)", min_value=1.0, value=8.27)
        height = st.number_input("Custom Height (inches)", min_value=1.0, value=11.69)
    else:
        page_sizes = {
            "A4": (8.27, 11.69),
            "A5": (5.83, 8.27),
            "Square": (8.27, 8.27),
            "A3": (11.69, 16.54),
            "A2": (16.54, 23.39),
            "A1": (23.39, 33.11),
        }
        width, height = page_sizes[page_size]

    # Layer selection
    st.subheader("Select Layers")

    layers = {
        # "hillshade": st.checkbox("Hillshade", value="hillshade" in style),
        "building": st.checkbox("Buildings", value="building" in style),
        "streets": st.checkbox("Streets", value="streets" in style),
        "waterway": st.checkbox("Waterway", value="waterway" in style),
        "building": st.checkbox("Building", value="building" in style),
        "water": st.checkbox("Water", value="water" in style),
        "sea": st.checkbox("Sea", value="sea" in style),
        "forest": st.checkbox("Forest", value="forest" in style),
        "green": st.checkbox("Green", value="green" in style),
        "rock": st.checkbox("Rock", value="rock" in style),
        "beach": st.checkbox("Beach", value="beach" in style),
        "parking": st.checkbox("Parking", value="parking" in style),
    }

    # Hillshade parameters
    if False:  # layers["hillshade"]:
        st.subheader("Hillshade Parameters")
        azdeg = st.number_input(
            "Azimuth (degrees)", min_value=0, max_value=360, value=315
        )
        altdeg = st.number_input(
            "Altitude (degrees)", min_value=0, max_value=90, value=45
        )
        vert_exag = st.number_input("Vertical Exaggeration", min_value=0.1, value=1.0)
        dx = st.number_input("dx", min_value=0.1, value=1.0)
        dy = st.number_input("dy", min_value=0.1, value=1.0)
        alpha = st.number_input("Alpha", min_value=0.0, max_value=1.0, value=0.75)

# Add a button in a new column to the right
with cols[1]:
    for i in range(0):
        st.write("")
    button = st.button(
        "Generate",
        key="generate_map",
        help="Click to generate the map",
        type="primary",
        icon=":material/map:",
        use_container_width=True,
    )

    if button:
        hillshade_params = (
            {
                "azdeg": azdeg,
                "altdeg": altdeg,
                "vert_exag": vert_exag,
                "dx": dx,
                "dy": dy,
                "alpha": alpha,
            }
            if False  # layers["hillshade"]
            else {}
        )
        with st.spinner("Generating map..."):
            fig, ax = plt.subplots(figsize=(width, height), dpi=300)
            prettymaps.plot(
                query,
                radius=1000 * radius,
                circle=circular,
                layers={k: (False if v == False else {}) for k, v in layers.items()},
                style={"building": {"palette": list(custom_palette.values())}},
                figsize=(width, height),
                preset=selected_preset,
                show=False,
                ax=ax,
            )
            buf = io.BytesIO()
            plt.savefig(buf, format="png", bbox_inches="tight", dpi=150)
            buf.seek(0)
            st.session_state.last_image = buf

            # Save the figure to a file
            fig_path = os.path.join(tempfile.gettempdir(), "generated_map.png")
            with open(fig_path, "wb") as f:
                f.write(st.session_state.last_image.getbuffer())

            # Save SVG for persistent download
            svg_path = download_svg()
            st.session_state.last_png_path = fig_path
            st.session_state.last_svg_path = svg_path

    # Always show download buttons (disabled if no image)
    png_ready = "last_png_path" in st.session_state and os.path.exists(
        st.session_state["last_png_path"]
    )
    svg_ready = "last_svg_path" in st.session_state and os.path.exists(
        st.session_state["last_svg_path"]
    )
    btn_cols = st.columns(2)
    with btn_cols[0]:
        st.download_button(
            label="Download PNG",
            data=open(st.session_state["last_png_path"], "rb") if png_ready else b"",
            file_name=f"{query}.png",
            mime="image/png",
            use_container_width=True,
            disabled=not png_ready,
        )
    with btn_cols[1]:
        st.download_button(
            label="Download SVG",
            data=open(st.session_state["last_svg_path"], "rb") if svg_ready else b"",
            file_name=f"{query}.svg",
            mime="image/svg",
            use_container_width=True,
            disabled=not svg_ready,
        )

    # Always show image (generated or placeholder)
    if st.session_state.get("last_image"):
        st.image(st.session_state.last_image, use_container_width=True)
    else:
        st.image(
            "https://github.com/marceloprates/prettymaps/blob/main/pictures/app_placeholder.png?raw=true",
            use_container_width=True,
        )
