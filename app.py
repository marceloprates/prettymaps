import streamlit as st
import logging
from matplotlib import pyplot as plt
import sys
import os
import io


def download_svg():
    """
    Creates additional map in SVG format
    """
    fig_path = "/tmp/generated_map_download.svg"
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

# Initialize custom markers
if "custom_markers" not in st.session_state:
    st.session_state.custom_markers = []

# Initialize marker editing state
if "editing_marker_index" not in st.session_state:
    st.session_state.editing_marker_index = None

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

    # Custom Markers Section
    st.subheader("Custom Markers")
    st.write(f"Current markers: {len(st.session_state.custom_markers)}")
    st.info(
        "ℹ️ Note: Markers outside the map bounds will be automatically skipped when generating the map."
    )

    # Form para añadir marcador
    with st.expander("Add New Marker", expanded=False):
        # Checkbox fuera del formulario para que funcione en tiempo real
        show_advanced = st.checkbox("Show advanced options", value=False)

        with st.form("add_marker_form", enter_to_submit=False):
            marker_cols = st.columns(2)

            with marker_cols[0]:
                marker_name = st.text_input("Name (optional)", value="")

                # Single flexible location input
                marker_location = st.text_input(
                    "Location",
                    value="52.3676, 4.9041",
                    help="Enter coordinates as 'lat, lon' (e.g., '52.3676, 4.9041') or a place name (e.g., 'Amsterdam Central Station')",
                )

            with marker_cols[1]:
                marker_types = {
                    "Circle": "o",
                    "Star": "*",
                    "Triangle Up": "^",
                    "Triangle Down": "v",
                    "Square": "s",
                    "Diamond": "D",
                    "Pentagon": "p",
                    "Hexagon": "h",
                    "Plus": "P",
                    "X": "X",
                }
                marker_type = st.selectbox(
                    "Marker Type", options=list(marker_types.keys()), index=0
                )
                marker_size = st.slider("Size", 10, 500, 100, step=10)
                marker_color = st.color_picker("Color", "#FF5E5B")

            # Opciones avanzadas dentro del formulario
            if show_advanced:
                st.write("**Advanced Options**")
                adv_cols = st.columns(3)
                with adv_cols[0]:
                    marker_edgecolor = st.color_picker("Edge Color", "#2F3737")
                    marker_linewidth = st.slider("Edge Width", 0.0, 5.0, 1.5, 0.5)
                with adv_cols[1]:
                    marker_alpha = st.slider("Opacity", 0.0, 1.0, 1.0, 0.1)
                with adv_cols[2]:
                    marker_zorder = st.number_input("Z-Order", value=1000)
            else:
                marker_edgecolor = "#2F3737"
                marker_linewidth = 1.5
                marker_alpha = 1.0
                marker_zorder = 1000

            submitted = st.form_submit_button("Add Marker")

            if submitted:
                # Build base marker dict
                new_marker = {
                    "name": marker_name,
                    "marker": marker_types[marker_type],
                    "size": marker_size,
                    "color": marker_color,
                    "edgecolor": marker_edgecolor,
                    "linewidth": marker_linewidth,
                    "alpha": marker_alpha,
                    "zorder": marker_zorder,
                }

                # Parse location input - try to detect if it's coordinates or a place name
                location_str = marker_location.strip()

                # Try to parse as "lat, lon" coordinates
                is_coordinates = False
                if ',' in location_str:
                    parts = location_str.split(',')
                    if len(parts) == 2:
                        try:
                            lat = float(parts[0].strip())
                            lon = float(parts[1].strip())
                            # Validate ranges
                            if -90 <= lat <= 90 and -180 <= lon <= 180:
                                new_marker["query"] = (lat, lon)
                                success_msg = f"Added marker at ({lat:.4f}, {lon:.4f})"
                                is_coordinates = True
                        except ValueError:
                            pass  # Not numeric, treat as place name

                # If not coordinates, treat as place name
                if not is_coordinates:
                    new_marker["query"] = location_str
                    success_msg = f"Added marker for '{location_str}'"

                st.session_state.custom_markers.append(new_marker)
                st.success(success_msg)
                st.rerun()

    # Gestionar marcadores existentes
    if len(st.session_state.custom_markers) > 0:
        with st.expander("Manage Existing Markers", expanded=False):
            # Si hay un marcador siendo editado, mostrar formulario de edición
            if st.session_state.editing_marker_index is not None:
                edit_idx = st.session_state.editing_marker_index
                marker_to_edit = st.session_state.custom_markers[edit_idx]

                st.write(f"### Editing Marker #{edit_idx + 1}")

                # Checkbox para opciones avanzadas (fuera del formulario)
                show_advanced_edit = st.checkbox(
                    "Show advanced options", value=False, key="edit_advanced"
                )

                with st.form("edit_marker_form", enter_to_submit=False):
                    edit_cols = st.columns(2)

                    with edit_cols[0]:
                        edit_name = st.text_input(
                            "Name (optional)",
                            value=marker_to_edit.get("name", ""),
                            key="edit_name",
                        )

                        # Get current location as string (handle all formats)
                        current_location = ""
                        if 'query' in marker_to_edit:
                            query_value = marker_to_edit['query']
                            if isinstance(query_value, tuple):
                                current_location = f"{query_value[0]}, {query_value[1]}"
                            else:  # string
                                current_location = query_value
                        else:
                            # Old format with separate lat/lon
                            lat = marker_to_edit.get("lat", 52.3676)
                            lon = marker_to_edit.get("lon", 4.9041)
                            current_location = f"{lat}, {lon}"

                        # Single flexible location input
                        edit_location = st.text_input(
                            "Location",
                            value=current_location,
                            help="Enter coordinates as 'lat, lon' (e.g., '52.3676, 4.9041') or a place name (e.g., 'Amsterdam Central Station')",
                            key="edit_location",
                        )

                    with edit_cols[1]:
                        marker_types = {
                            "Circle": "o",
                            "Star": "*",
                            "Triangle Up": "^",
                            "Triangle Down": "v",
                            "Square": "s",
                            "Diamond": "D",
                            "Pentagon": "p",
                            "Hexagon": "h",
                            "Plus": "P",
                            "X": "X",
                        }
                        # Find current marker type index
                        current_marker = marker_to_edit.get("marker", "o")
                        marker_type_names = list(marker_types.keys())
                        marker_type_values = list(marker_types.values())
                        current_index = (
                            marker_type_values.index(current_marker)
                            if current_marker in marker_type_values
                            else 0
                        )

                        edit_marker_type = st.selectbox(
                            "Marker Type",
                            options=marker_type_names,
                            index=current_index,
                            key="edit_type",
                        )
                        edit_size = st.slider(
                            "Size",
                            10,
                            500,
                            int(marker_to_edit.get("size", 100)),
                            step=10,
                            key="edit_size",
                        )
                        edit_color = st.color_picker(
                            "Color",
                            marker_to_edit.get("color", "#FF5E5B"),
                            key="edit_color",
                        )

                    # Opciones avanzadas
                    if show_advanced_edit:
                        st.write("**Advanced Options**")
                        edit_adv_cols = st.columns(3)
                        with edit_adv_cols[0]:
                            edit_edgecolor = st.color_picker(
                                "Edge Color",
                                marker_to_edit.get("edgecolor", "#2F3737"),
                                key="edit_edgecolor",
                            )
                            edit_linewidth = st.slider(
                                "Edge Width",
                                0.0,
                                5.0,
                                float(marker_to_edit.get("linewidth", 1.5)),
                                0.5,
                                key="edit_linewidth",
                            )
                        with edit_adv_cols[1]:
                            edit_alpha = st.slider(
                                "Opacity",
                                0.0,
                                1.0,
                                float(marker_to_edit.get("alpha", 1.0)),
                                0.1,
                                key="edit_alpha",
                            )
                        with edit_adv_cols[2]:
                            edit_zorder = st.number_input(
                                "Z-Order",
                                value=int(marker_to_edit.get("zorder", 1000)),
                                key="edit_zorder",
                            )
                    else:
                        edit_edgecolor = marker_to_edit.get("edgecolor", "#2F3737")
                        edit_linewidth = marker_to_edit.get("linewidth", 1.5)
                        edit_alpha = marker_to_edit.get("alpha", 1.0)
                        edit_zorder = marker_to_edit.get("zorder", 1000)

                    # Botones de acción
                    form_cols = st.columns(2)
                    with form_cols[0]:
                        save_edit = st.form_submit_button("💾 Save Changes")
                    with form_cols[1]:
                        cancel_edit = st.form_submit_button("❌ Cancel")

                    if save_edit:
                        # Build updated marker dict
                        updated_marker = {
                            "name": edit_name,
                            "marker": marker_types[edit_marker_type],
                            "size": edit_size,
                            "color": edit_color,
                            "edgecolor": edit_edgecolor,
                            "linewidth": edit_linewidth,
                            "alpha": edit_alpha,
                            "zorder": edit_zorder,
                        }

                        # Parse location input - try to detect if it's coordinates or a place name
                        location_str = edit_location.strip()

                        # Try to parse as "lat, lon" coordinates
                        is_coordinates = False
                        if ',' in location_str:
                            parts = location_str.split(',')
                            if len(parts) == 2:
                                try:
                                    lat = float(parts[0].strip())
                                    lon = float(parts[1].strip())
                                    # Validate ranges
                                    if -90 <= lat <= 90 and -180 <= lon <= 180:
                                        updated_marker["query"] = (lat, lon)
                                        is_coordinates = True
                                except ValueError:
                                    pass  # Not numeric, treat as place name

                        # If not coordinates, treat as place name
                        if not is_coordinates:
                            updated_marker["query"] = location_str

                        # Update the marker
                        st.session_state.custom_markers[edit_idx] = updated_marker
                        st.session_state.editing_marker_index = None
                        st.success("Marker updated successfully!")
                        st.rerun()

                    if cancel_edit:
                        st.session_state.editing_marker_index = None
                        st.rerun()

            else:
                # Mostrar lista de marcadores
                for i, marker in enumerate(st.session_state.custom_markers):
                    marker_display_cols = st.columns([3, 1, 1])
                    with marker_display_cols[0]:
                        name_display = marker.get("name", f"Marker {i+1}")

                        # Display location based on format
                        if 'query' in marker:
                            query_value = marker['query']
                            if isinstance(query_value, tuple):
                                location_str = f"({query_value[0]:.4f}, {query_value[1]:.4f})"
                            else:  # string
                                location_str = f"'{query_value}'"
                        else:
                            location_str = f"({marker['lat']:.4f}, {marker['lon']:.4f})"

                        st.write(
                            f"**{name_display}** - {location_str} - "
                            f"Type: {marker['marker']}, Color: {marker['color']}"
                        )
                    with marker_display_cols[1]:
                        if st.button("✏️ Edit", key=f"edit_marker_{i}"):
                            st.session_state.editing_marker_index = i
                            st.rerun()
                    with marker_display_cols[2]:
                        if st.button("🗑️ Delete", key=f"delete_marker_{i}"):
                            st.session_state.custom_markers.pop(i)
                            st.rerun()

                if st.button("🧹 Clear All Markers"):
                    st.session_state.custom_markers = []
                    st.rerun()

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
        width="stretch",
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
                custom_markers=st.session_state.custom_markers,
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
            fig_path = "/tmp/generated_map.png"
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

    # Read files properly to avoid resource warnings
    png_data = b""
    if png_ready:
        with open(st.session_state["last_png_path"], "rb") as f:
            png_data = f.read()

    svg_data = b""
    if svg_ready:
        with open(st.session_state["last_svg_path"], "rb") as f:
            svg_data = f.read()

    btn_cols = st.columns(2)
    with btn_cols[0]:
        st.download_button(
            label="Download PNG",
            data=png_data,
            file_name=f"{query}.png",
            mime="image/png",
            width="stretch",
            disabled=not png_ready,
        )
    with btn_cols[1]:
        st.download_button(
            label="Download SVG",
            data=svg_data,
            file_name=f"{query}.svg",
            mime="image/svg",
            width="stretch",
            disabled=not svg_ready,
        )

    # Always show image (generated or placeholder)
    if st.session_state.get("last_image"):
        st.image(st.session_state.last_image, width="stretch")
    else:
        st.image(
            "https://github.com/marceloprates/prettymaps/blob/main/pictures/app_placeholder.png?raw=true",
            width="stretch",
        )
