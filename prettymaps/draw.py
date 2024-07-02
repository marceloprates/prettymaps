"""
Prettymaps - A minimal Python library to draw pretty maps from OpenStreetMap Data
Copyright (C) 2021 Marcelo Prates

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import re
import os
import json
import pathlib
import warnings
import matplotlib
import numpy as np
import osmnx as ox
import shapely.ops
import pandas as pd
import geopandas as gp
import shapely.affinity
from copy import deepcopy
from .fetch import get_gdfs
from dataclasses import dataclass
from matplotlib import pyplot as plt
from matplotlib.colors import hex2color
from matplotlib.patches import Path, PathPatch
from shapely.geometry.base import BaseGeometry
from typing import Optional, Union, Tuple, List, Dict, Any, Iterable
from shapely.geometry import (
    Point,
    LineString,
    MultiLineString,
    Polygon,
    MultiPolygon,
    GeometryCollection,
    box,
)

try:
    import vsketch
except:
    warnings.warn(
        'Install Vsketch with "pip install git+https://github.com/abey79/vsketch@1.0.0" to enable pen plotter mode.'
    )


class Subplot:
    """
    Class implementing a prettymaps Subplot. Attributes:
    - query: prettymaps.plot() query
    - kwargs: dictionary of prettymaps.plot() parameters
    """

    def __init__(self, query, **kwargs):
        self.query = query
        self.kwargs = kwargs


@dataclass
class Plot:
    """
    Dataclass implementing a prettymaps Plot object. Attributes:
    - geodataframes: A dictionary of GeoDataFrames (one for each plot layer)
    - fig: A matplotlib figure
    - ax: A matplotlib axis object
    - background: Background layer (shapely object)
    """

    geodataframes: Dict[str, gp.GeoDataFrame]
    fig: matplotlib.figure.Figure
    ax: matplotlib.axes.Axes
    background: BaseGeometry


@dataclass
class Preset:
    """
    Dataclass implementing a prettymaps Preset object. Attributes:
    - params: dictionary of prettymaps.plot() parameters
    """

    params: dict

    '''
    def _ipython_display_(self):
        """
        Implements the _ipython_display_() function for the Preset class.
        'params' will be displayed as a Markdown table with annotated hex colors
        """

        def light_color(hexstring):
            rgb = np.array(hex2color(hexstring))
            return rgb.mean() > .5

        def annotate_colors(text):
            matches = re.findall(
                '#(?:\\d|[a-f]|[A-F]){6}|#(?:\\d|[a-f]|[A-F]){4}|#(?:\\d|[a-f]|[A-F]){3}', text)
            for match in matches:
                text = text.replace(
                    match,
                    f'<span style="background-color:{match}; color:{"#000" if light_color(match) else "#fff"}">{match}</span>'
                )
            return text

        params = pd.DataFrame(self.params)
        params = params.applymap(lambda x: annotate_colors(
            yaml.dump(x, default_flow_style=False).replace('\n', '<br>')))
        params.iloc[1:, 2:] = ''

        IPython.display.display(IPython.display.Markdown(params.to_markdown()))
    '''


def transform_gdfs(
    gdfs: Dict[str, gp.GeoDataFrame],
    x: float = 0,
    y: float = 0,
    scale_x: float = 1,
    scale_y: float = 1,
    rotation: float = 0,
) -> Dict[str, gp.GeoDataFrame]:
    """
    Apply geometric transformations to dictionary of GeoDataFrames

    Args:
        gdfs (Dict[str, gp.GeoDataFrame]): Dictionary of GeoDataFrames
        x (float, optional): x-axis translation. Defaults to 0.
        y (float, optional): y-axis translation. Defaults to 0.
        scale_x (float, optional): x-axis scale. Defaults to 1.
        scale_y (float, optional): y-axis scale. Defaults to 1.
        rotation (float, optional): rotation angle (in radians). Defaults to 0.

    Returns:
        Dict[str, gp.GeoDataFrame]: dictionary of transformed GeoDataFrames
    """
    # Project geometries
    gdfs = {
        name: ox.project_gdf(gdf) if len(gdf) > 0 else gdf for name, gdf in gdfs.items()
    }
    # Create geometry collection from gdfs' geometries
    collection = GeometryCollection(
        [GeometryCollection(list(gdf.geometry)) for gdf in gdfs.values()]
    )
    # Translation, scale & rotation
    collection = shapely.affinity.translate(collection, x, y)
    collection = shapely.affinity.scale(collection, scale_x, scale_y)
    collection = shapely.affinity.rotate(collection, rotation)
    # Update geometries
    for i, layer in enumerate(gdfs):
        gdfs[layer].geometry = list(collection.geoms[i].geoms)
        # Reproject
        if len(gdfs[layer]) > 0:
            gdfs[layer] = ox.project_gdf(gdfs[layer], to_crs="EPSG:4326")

    return gdfs


def PolygonPatch(shape: BaseGeometry, **kwargs) -> PathPatch:
    """_summary_

    Args:
        shape (BaseGeometry): Shapely geometry
        kwargs: parameters for matplotlib's PathPatch constructor

    Returns:
        PathPatch: matplotlib PatchPatch created from input shapely geometry
    """
    # Init vertices and codes lists
    vertices, codes = [], []
    for geom in shape.geoms if hasattr(shape, "geoms") else [shape]:
        for poly in geom.geoms if hasattr(geom, "geoms") else [geom]:
            if type(poly) != Polygon:
                continue
            # Get polygon's exterior and interiors
            exterior = np.array(poly.exterior.xy)
            interiors = [np.array(interior.xy) for interior in poly.interiors]
            # Append to vertices and codes lists
            vertices += [exterior] + interiors
            codes += list(
                map(
                    # Ring coding
                    lambda p: [Path.MOVETO]
                    + [Path.LINETO] * (p.shape[1] - 2)
                    + [Path.CLOSEPOLY],
                    [exterior] + interiors,
                )
            )
    # Generate PathPatch
    return PathPatch(
        Path(np.concatenate(vertices, 1).T, np.concatenate(codes)), **kwargs
    )


def plot_gdf(
    layer: str,
    gdf: gp.GeoDataFrame,
    ax: matplotlib.axes.Axes,
    mode: str = "matplotlib",
    # vsk: Optional[vsketch.SketchClass] = None,
    vsk=None,
    palette: Optional[List[str]] = None,
    width: Optional[Union[dict, float]] = None,
    union: bool = False,
    dilate_points: Optional[float] = None,
    dilate_lines: Optional[float] = None,
    **kwargs,
) -> None:
    """
    Plot a layer

    Args:
        layer (str): layer name
        gdf (gp.GeoDataFrame): GeoDataFrame
        ax (matplotlib.axes.Axes): matplotlib axis object
        mode (str): drawing mode. Options: 'matplotlib', 'vsketch'. Defaults to 'matplotlib'
        vsk (Optional[vsketch.SketchClass]): Vsketch object. Mandatory if mode == 'plotter'
        palette (Optional[List[str]], optional): Color palette. Defaults to None.
        width (Optional[Union[dict, float]], optional): Street widths. Either a dictionary or a float. Defaults to None.
        union (bool, optional): Whether to join geometries. Defaults to False.
        dilate_points (Optional[float], optional): Amount of dilation to be applied to point (1D) geometries. Defaults to None.
        dilate_lines (Optional[float], optional): Amount of dilation to be applied to line (2D) geometries. Defaults to None.

    Raises:
        Exception: _description_
    """

    # Get hatch and hatch_c parameter
    hatch_c = kwargs.pop("hatch_c") if "hatch_c" in kwargs else None

    # Convert GDF to shapely geometries
    geometries = gdf_to_shapely(
        layer, gdf, width, point_size=dilate_points, line_width=dilate_lines
    )

    # Unite geometries
    if union:
        geometries = shapely.ops.unary_union(GeometryCollection([geometries]))

    if (palette is None) and ("fc" in kwargs) and (type(kwargs["fc"]) != str):
        palette = kwargs.pop("fc")

    for shape in geometries.geoms if hasattr(geometries, "geoms") else [geometries]:
        if mode == "matplotlib":
            if type(shape) in [Polygon, MultiPolygon]:
                # Plot main shape (without silhouette)
                ax.add_patch(
                    PolygonPatch(
                        shape,
                        lw=0,
                        ec=(
                            hatch_c
                            if hatch_c
                            else kwargs["ec"] if "ec" in kwargs else None
                        ),
                        fc=(
                            kwargs["fc"]
                            if "fc" in kwargs
                            else np.random.choice(palette) if palette else None
                        ),
                        **{
                            k: v
                            for k, v in kwargs.items()
                            if k not in ["lw", "ec", "fc"]
                        },
                    ),
                )
                # Plot just silhouette
                ax.add_patch(
                    PolygonPatch(
                        shape,
                        fill=False,
                        **{
                            k: v
                            for k, v in kwargs.items()
                            if k not in ["hatch", "fill"]
                        },
                    )
                )
            elif type(shape) == LineString:
                ax.plot(
                    *shape.xy,
                    c=kwargs["ec"] if "ec" in kwargs else None,
                    **{
                        k: v
                        for k, v in kwargs.items()
                        if k in ["lw", "ls", "dashes", "zorder"]
                    },
                )
            elif type(shape) == MultiLineString:
                for c in shape.geoms:
                    ax.plot(
                        *c.xy,
                        c=kwargs["ec"] if "ec" in kwargs else None,
                        **{
                            k: v
                            for k, v in kwargs.items()
                            if k in ["lw", "lt", "dashes", "zorder"]
                        },
                    )
        elif mode == "plotter":
            if ("draw" not in kwargs) or kwargs["draw"]:

                # Set stroke
                if "stroke" in kwargs:
                    vsk.stroke(kwargs["stroke"])
                else:
                    vsk.stroke(1)

                # Set pen width
                if "penWidth" in kwargs:
                    vsk.penWidth(kwargs["penWidth"])
                else:
                    vsk.penWidth(0.3)

                if "fill" in kwargs:
                    vsk.fill(kwargs["fill"])
                else:
                    vsk.noFill()

                vsk.geometry(shape)
        else:
            raise Exception(f"Unknown mode {mode}")


##########


def plot_legends(gdf, ax):

    for _, row in gdf.iterrows():
        name = row.name
        x, y = np.concatenate(row.geometry.centroid.xy)
        ax.text(x, y, name)


##########


def graph_to_shapely(gdf: gp.GeoDataFrame, width: float = 1.0) -> BaseGeometry:
    """
    Given a GeoDataFrame containing a graph (street newtork),
    convert them to shapely geometries by applying dilation given by 'width'

    Args:
        gdf (gp.GeoDataFrame): input GeoDataFrame containing graph (street network) geometries
        width (float, optional): Line geometries will be dilated by this amount. Defaults to 1..

    Returns:
        BaseGeometry: Shapely
    """

    def highway_to_width(highway):
        if (type(highway) == str) and (highway in width):
            return width[highway]
        elif isinstance(highway, Iterable):
            for h in highway:
                if h in width:
                    return width[h]
            return np.nan
        else:
            return np.nan

    # Annotate GeoDataFrame with the width for each highway type
    gdf["width"] = gdf.highway.map(highway_to_width) if type(width) == dict else width

    # Remove rows with inexistent width
    gdf.drop(gdf[gdf.width.isna()].index, inplace=True)

    with warnings.catch_warnings():
        # Supress shapely.errors.ShapelyDeprecationWarning
        warnings.simplefilter("ignore", shapely.errors.ShapelyDeprecationWarning)
        if not all(gdf.width.isna()):
            # Dilate geometries based on their width
            gdf.geometry = gdf.apply(
                lambda row: row["geometry"].buffer(row.width), axis=1
            )

    return shapely.ops.unary_union(gdf.geometry)


def geometries_to_shapely(
    gdf: gp.GeoDataFrame,
    point_size: Optional[float] = None,
    line_width: Optional[float] = None,
) -> GeometryCollection:
    """
    Convert geometries in GeoDataFrame to shapely format

    Args:
        gdf (gp.GeoDataFrame): Input GeoDataFrame
        point_size (Optional[float], optional): Point geometries (1D) will be dilated by this amount. Defaults to None.
        line_width (Optional[float], optional): Line geometries (2D) will be dilated by this amount. Defaults to None.

    Returns:
        GeometryCollection: Shapely geometries computed from GeoDataFrame geometries
    """

    geoms = gdf.geometry.tolist()
    collections = [x for x in geoms if type(x) == GeometryCollection]
    points = [x for x in geoms if type(x) == Point] + [
        y for x in collections for y in x.geoms if type(y) == Point
    ]
    lines = [x for x in geoms if type(x) in [LineString, MultiLineString]] + [
        y
        for x in collections
        for y in x.geoms
        if type(y) in [LineString, MultiLineString]
    ]
    polys = [x for x in geoms if type(x) in [Polygon, MultiPolygon]] + [
        y for x in collections for y in x.geoms if type(y) in [Polygon, MultiPolygon]
    ]

    # Convert points into circles with radius "point_size"
    if point_size:
        points = [x.buffer(point_size) for x in points] if point_size > 0 else []
    if line_width:
        lines = [x.buffer(line_width) for x in lines] if line_width > 0 else []

    return GeometryCollection(list(points) + list(lines) + list(polys))


def gdf_to_shapely(
    layer: str,
    gdf: gp.GeoDataFrame,
    width: Optional[Union[dict, float]] = None,
    point_size: Optional[float] = None,
    line_width: Optional[float] = None,
    **kwargs,
) -> GeometryCollection:
    """
    Convert a dict of GeoDataFrames to a dict of shapely geometries

    Args:
        layer (str): Layer name
        gdf (gp.GeoDataFrame): Input GeoDataFrame
        width (Optional[Union[dict, float]], optional): Street network width. Can be either a dictionary or a float. Defaults to None.
        point_size (Optional[float], optional): Point geometries (1D) will be dilated by this amount. Defaults to None.
        line_width (Optional[float], optional): Line geometries (2D) will be dilated by this amount. Defaults to None.

    Returns:
        GeometryCollection: Output GeoDataFrame
    """

    # Project gdf
    try:
        gdf = ox.project_gdf(gdf)
    except:
        pass

    if layer in ["streets", "railway", "waterway"]:
        geometries = graph_to_shapely(gdf, width)
    else:
        geometries = geometries_to_shapely(
            gdf, point_size=point_size, line_width=line_width
        )

    return geometries


def override_args(
    layers: dict, circle: Optional[bool], dilate: Optional[Union[float, bool]]
) -> dict:
    """
    Override arguments in layers' kwargs

    Args:
        layers (dict): prettymaps.plot() Layers parameters dict
        circle (Optional[bool]): prettymaps.plot() 'Circle' parameter
        dilate (Optional[Union[float, bool]]): prettymaps.plot() 'dilate' parameter

    Returns:
        dict: output dict
    """
    override_args = ["circle", "dilate"]
    for layer in layers:
        for arg in override_args:
            if arg not in layers[layer]:
                layers[layer][arg] = locals()[arg]
    return layers


def override_params(default_dict: dict, new_dict: dict) -> dict:
    """
    Override parameters in 'default_dict' with additional parameters from 'new_dict'

    Args:
        default_dict (dict): Default dict to be overriden with 'new_dict' parameters
        new_dict (dict): New dict to override 'default_dict' parameters

    Returns:
        dict: default_dict overriden with new_dict parameters
    """

    final_dict = deepcopy(default_dict)

    for key in new_dict.keys():
        if type(new_dict[key]) == dict:
            if key in final_dict:
                final_dict[key] = override_params(final_dict[key], new_dict[key])
            else:
                final_dict[key] = new_dict[key]
        else:
            final_dict[key] = new_dict[key]

    return final_dict


def create_background(
    gdfs: Dict[str, gp.GeoDataFrame], style: Dict[str, dict]
) -> Tuple[BaseGeometry, float, float, float, float, float, float]:
    """
    Create a background layer given a collection of GeoDataFrames

    Args:
        gdfs (Dict[str, gp.GeoDataFrame]): Dictionary of GeoDataFrames
        style (Dict[str, dict]): Dictionary of matplotlib style parameters

    Returns:
        Tuple[BaseGeometry, float, float, float, float, float, float]: background geometry, bounds, width and height
    """

    # Create background
    background_pad = 1.1
    if "background" in style and "pad" in style["background"]:
        background_pad = style["background"].pop("pad")

    background = shapely.affinity.scale(
        box(
            *shapely.ops.unary_union(ox.project_gdf(gdfs["perimeter"]).geometry).bounds
        ),
        background_pad,
        background_pad,
    )

    if "background" in style and "dilate" in style["background"]:
        background = background.buffer(style["background"].pop("dilate"))

    # Get bounds
    xmin, ymin, xmax, ymax = background.bounds
    dx, dy = xmax - xmin, ymax - ymin

    return background, xmin, ymin, xmax, ymax, dx, dy


def draw_text(params: Dict[str, dict], background: BaseGeometry) -> None:
    """
    Draw text with content and matplotlib style parameters specified by 'params' dictionary.
    params['text'] should contain the message to be drawn

    Args:
        params (Dict[str, dict]): matplotlib style parameters for drawing text. params['text'] should contain the message to be drawn.
        background (BaseGeometry): Background layer
    """
    # Override default osm_credit dict with provided parameters
    params = override_params(
        dict(
            text="\n".join(
                [
                    "data © OpenStreetMap contributors",
                    "github.com/marceloprates/prettymaps",
                ]
            ),
            x=0,
            y=1,
            horizontalalignment="left",
            verticalalignment="top",
            bbox=dict(boxstyle="square", fc="#fff", ec="#000"),
            fontfamily="Ubuntu Mono",
        ),
        params,
    )
    x, y, text = [params.pop(k) for k in ["x", "y", "text"]]

    # Get background bounds
    xmin, ymin, xmax, ymax = background.bounds

    x = np.interp([x], [0, 1], [xmin, xmax])[0]
    y = np.interp([y], [0, 1], [ymin, ymax])[0]

    plt.text(x, y, text, **params)


def presets_directory():
    return os.path.join(pathlib.Path(__file__).resolve().parent, "presets")


def create_preset(
    name: str,
    layers: Optional[Dict[str, dict]] = None,
    style: Optional[Dict[str, dict]] = None,
    circle: Optional[bool] = None,
    radius: Optional[Union[float, bool]] = None,
    dilate: Optional[Union[float, bool]] = None,
) -> None:
    """
    Create a preset file and save it on the presets folder (prettymaps/presets/) under name 'name.json'

    Args:
        name (str): Preset name
        layers (Dict[str, dict], optional): prettymaps.plot() 'layers' parameter dict. Defaults to None.
        style (Dict[str, dict], optional): prettymaps.plot() 'style' parameter dict. Defaults to None.
        circle (Optional[bool], optional): prettymaps.plot() 'circle' parameter. Defaults to None.
        radius (Optional[Union[float, bool]], optional): prettymaps.plot() 'radius' parameter. Defaults to None.
        dilate (Optional[Union[float, bool]], optional): prettymaps.plot() 'dilate' parameter. Defaults to None.
    """

    # if not os.path.isdir('presets'):
    #    os.makedirs('presets')

    path = os.path.join(presets_directory(), f"{name}.json")
    with open(path, "w") as f:
        json.dump(
            {
                "layers": layers,
                "style": style,
                "circle": circle,
                "radius": radius,
                "dilate": dilate,
            },
            f,
            ensure_ascii=False,
        )


def read_preset(name: str) -> Dict[str, dict]:
    """
    Read a preset from the presets folder (prettymaps/presets/)

    Args:
        name (str): Preset name

    Returns:
        (Dict[str,dict]): parameters dictionary
    """
    path = os.path.join(presets_directory(), f"{name}.json")
    with open(path, "r") as f:
        # Load params from JSON file
        params = json.load(f)
    return params


def delete_preset(name: str) -> None:
    """
    Delete a preset from the presets folder (prettymaps/presets/)

    Args:
        name (str): Preset name
    """

    path = os.path.join(presets_directory(), f"{name}.json")
    if os.path.exists(path):
        os.remove(path)


def override_preset(
    name: str,
    layers: Dict[str, dict] = {},
    style: Dict[str, dict] = {},
    circle: Optional[float] = None,
    radius: Optional[Union[float, bool]] = None,
    dilate: Optional[Union[float, bool]] = None,
) -> Tuple[
    dict,
    dict,
    Optional[float],
    Optional[Union[float, bool]],
    Optional[Union[float, bool]],
]:
    """
    Read the preset file given by 'name' and override it with additional parameters

    Args:
        name (str): _description_
        layers (Dict[str, dict], optional): _description_. Defaults to {}.
        style (Dict[str, dict], optional): _description_. Defaults to {}.
        circle (Union[float, None], optional): _description_. Defaults to None.
        radius (Union[float, None], optional): _description_. Defaults to None.
        dilate (Union[float, None], optional): _description_. Defaults to None.

    Returns:
        Tuple[dict, dict, Optional[float], Optional[Union[float, bool]], Optional[Union[float, bool]]]: Preset parameters overriden by additional provided parameters
    """

    params = read_preset(name)

    # Override preset with kwargs
    if "layers" in params:
        layers = override_params(params["layers"], layers)
    if "style" in params:
        style = override_params(params["style"], style)
    if circle is None and "circle" in params:
        circle = params["circle"]
    if radius is None and "radius" in params:
        radius = params["radius"]
    if dilate is None and "dilate" in params:
        dilate = params["dilate"]

    # Delete layers marked as 'False' in the parameter dict
    for layer in [key for key in layers.keys() if layers[key] == False]:
        del layers[layer]

    # Return overriden presets
    return layers, style, circle, radius, dilate


def manage_presets(
    load_preset: Optional[str],
    save_preset: bool,
    update_preset: Optional[str],
    layers: Dict[str, dict],
    style: Dict[str, dict],
    circle: Optional[bool],
    radius: Optional[Union[float, bool]],
    dilate: Optional[Union[float, bool]],
) -> Tuple[
    dict,
    dict,
    Optional[float],
    Optional[Union[float, bool]],
    Optional[Union[float, bool]],
]:
    """_summary_

    Args:
        load_preset (Optional[str]): Load preset named 'load_preset', if provided
        save_preset (Optional[str]): Save preset to file named 'save_preset', if provided
        update_preset (Optional[str]): Load, update and save preset named 'update_preset', if provided
        layers (Dict[str, dict]): prettymaps.plot() 'layers' parameter dict
        style (Dict[str, dict]): prettymaps.plot() 'style' parameter dict
        circle (Optional[bool]): prettymaps.plot() 'circle' parameter
        radius (Optional[Union[float, bool]]): prettymaps.plot() 'radius' parameter
        dilate (Optional[Union[float, bool]]): prettymaps.plot() 'dilate' parameter

    Returns:
        Tuple[dict, dict, Optional[float], Optional[Union[float, bool]], Optional[Union[float, bool]]]: Updated layers, style, circle, radius, dilate parameters
    """

    # Update preset mode: load a preset, update it with additional parameters and update the JSON file
    if update_preset is not None:
        # load_preset = save_preset = True
        load_preset = save_preset = update_preset

    # Load preset (if provided)
    if load_preset is not None:
        layers, style, circle, radius, dilate = override_preset(
            load_preset, layers, style, circle, radius, dilate
        )

    # Save parameters as preset
    if save_preset is not None:
        create_preset(
            save_preset,
            layers=layers,
            style=style,
            circle=circle,
            radius=radius,
            dilate=dilate,
        )

    return layers, style, circle, radius, dilate


def presets():
    presets = [
        file.split(".")[0]
        for file in os.listdir(presets_directory())
        if file.endswith(".json")
    ]
    presets = sorted(presets)
    presets = pd.DataFrame(
        {"preset": presets, "params": list(map(read_preset, presets))}
    )

    # print('Available presets:')
    # for i, preset in enumerate(presets):
    #    print(f'{i+1}. {preset}')

    return pd.DataFrame(presets)


def preset(name):
    with open(os.path.join(presets_directory(), f"{name}.json"), "r") as f:
        # Load params from JSON file
        params = json.load(f)
        return Preset(params)


# Plot
def plot(
    # Your query. Example:
    # - "Porto Alegre"
    # - (-30.0324999, -51.2303767) (lat/long coordinates)
    # - You can also provide a custom GeoDataFrame boundary as input
    query: Union[str, Tuple[float, float], gp.GeoDataFrame],
    backup=None,
    # Which OpenStreetMap layers to plot
    # Example: {'building': {'tags': {'building': True}}, 'streets': {'width': 2}}
    # Run prettymaps.presets() for more examples
    layers={},
    # Matplotlib params for drawing each layer
    style={},
    # Whether to load params from preset
    preset="default",
    # Whether to save preset
    save_preset=None,
    # Whether to load and update preset with additional parameters
    update_preset=None,
    # Custom postprocessing function on layers
    postprocessing=None,
    # Circular boundary? Default: square
    circle=None,
    # Radius for circular or square boundary
    radius=None,
    # Dilate boundary by this much
    dilate=None,
    # Whether to save result
    save_as=None,
    # Figure parameters
    fig=None,
    ax=None,
    title=None,
    figsize=(12, 12),
    constrained_layout=True,
    # Credit message parameters
    credit={},
    # Mode ('matplotlib' or 'plotter')
    mode="matplotlib",
    # Multiplot mode
    multiplot=False,
    # Whether to display matplotlib
    show=True,
    # Transform (translation, scale, rotation) parameters
    x=0,
    y=0,
    scale_x=1,
    scale_y=1,
    rotation=0,
):
    """

    Draw a map from OpenStreetMap data.

    Parameters
    ----------
    query : string
        The address to geocode and use as the central point around which to get the geometries
    backup : dict
        (Optional) feed the output from a previous 'plot()' run to save time
    postprocessing: function
        (Optional) Apply a postprocessing step to the 'layers' dict
    radius
        (Optional) If not None, draw the map centered around the address with this radius (in meters)
    layers: dict
        Specify the name of each layer and the OpenStreetMap tags to fetch
    style: dict
        Drawing params for each layer (matplotlib params such as 'fc', 'ec', 'fill', etc.)
    osm_credit: dict
        OSM Caption parameters
    figsize: Tuple
        (Optional) Width and Height (in inches) for the Matplotlib figure. Defaults to (10, 10)
    ax: axes
        Matplotlib axes
    title: String
        (Optional) Title for the Matplotlib figure
    vsketch: Vsketch
        (Optional) Vsketch object for pen plotting
    x: float
        (Optional) Horizontal displacement
    y: float
        (Optional) Vertical displacement
    scale_x: float
        (Optional) Horizontal scale factor
    scale_y: float
        (Optional) Vertical scale factor
    rotation: float
        (Optional) Rotation in angles (0-360)

    Returns
    -------
    layers: dict
        Dictionary of layers (each layer is a Shapely MultiPolygon)

    Notes
    -----

    """

    # 1. Manage presets
    layers, style, circle, radius, dilate = manage_presets(
        preset, save_preset, update_preset, layers, style, circle, radius, dilate
    )

    # 2. Init matplotlib figure and ax
    if (mode == "matplotlib") and (fig is None):
        fig = plt.figure(figsize=figsize, dpi=300)
    if (mode == "matplotlib") and (ax is None):
        ax = plt.subplot(111, aspect="equal")

    # 3. Override arguments in layers' kwargs dict
    layers = override_args(layers, circle, dilate)

    if backup:
        gdfs = backup.geodataframes
    else:
        # 4. Fetch geodataframes
        gdfs = get_gdfs(query, layers, radius, dilate, -rotation)

        # 5. Apply transformations to GeoDataFrames (translation, scale, rotation)
        gdfs = transform_gdfs(gdfs, x, y, scale_x, scale_y, rotation)

    # 6. Apply a postprocessing function to the GeoDataFrames, if provided
    if postprocessing:
        gdfs = postprocessing(gdfs)

    # 7. Create background GeoDataFrame and get (x,y) bounds
    background, xmin, ymin, xmax, ymax, dx, dy = create_background(gdfs, style)

    # 8. Draw layers
    if mode == "plotter":
        # 8.1. Draw layers in plotter (vsketch) mode
        #'''
        class Sketch(vsketch.SketchClass):
            def draw(self, vsk: vsketch.Vsketch):

                vsk.size("a4", landscape=True)

                for layer in gdfs:
                    if layer in layers:
                        plot_gdf(
                            layer,
                            gdfs[layer],
                            ax,
                            width=(
                                layers[layer]["width"]
                                if "width" in layers[layer]
                                else None
                            ),
                            mode=mode,
                            vsk=vsk,
                            **(style[layer] if layer in style else {}),
                        )

                if save_as:
                    vsk.save(save_as)

            def finalize(self, vsk: vsketch.Vsketch):
                vsk.vpype("linemerge linesimplify reloop linesort")

        sketch = Sketch()
        sketch.display()
        #'''
    elif mode == "matplotlib":
        # 8.2. Draw layers in matplotlib mode
        for layer in gdfs:
            if (layer in layers) or (layer in style):
                plot_gdf(
                    layer,
                    gdfs[layer],
                    ax,
                    width=(
                        layers[layer]["width"]
                        if (layer in layers) and ("width" in layers[layer])
                        else None
                    ),
                    **(style[layer] if layer in style else {}),
                )
    else:
        raise Exception(f"Unknown mode {mode}")

    # 9. Draw background
    if (mode == "matplotlib") and ("background" in style):
        zorder = (
            style["background"].pop("zorder") if "zorder" in style["background"] else -1
        )
        ax.add_patch(
            PolygonPatch(
                background,
                **{k: v for k, v in style["background"].items() if k != "dilate"},
                zorder=zorder,
            )
        )

    # 10. Draw credit message
    if (mode == "matplotlib") and (credit != False) and (not multiplot):
        draw_text(credit, background)

    # 11. Ajust figure and create PIL Image
    if mode == "matplotlib":
        # Adjust axis
        ax.axis("off")
        ax.axis("equal")
        ax.autoscale()
        # Adjust padding
        plt.subplots_adjust(left=0, bottom=0, right=1, top=1, wspace=0, hspace=0)
        # Save result
        if save_as:
            plt.savefig(save_as)
        if not show:
            plt.close()

    # Generate plot
    plot = Plot(gdfs, fig, ax, background)

    return plot


def multiplot(*subplots, figsize=None, credit={}, **kwargs):

    fig = plt.figure(figsize=figsize)
    ax = plt.subplot(111, aspect="equal")

    mode = "plotter" if "plotter" in kwargs and kwargs["plotter"] else "matplotlib"

    subplots_results = [
        plot(
            subplot.query,
            ax=ax,
            multiplot=True,
            **override_params(
                subplot.kwargs,
                {
                    k: v
                    for k, v in kwargs.items()
                    if k != "load_preset" or "load_preset" not in subplot.kwargs
                },
            ),
        )
        for subplot in subplots
    ]

    if mode == "matplotlib":
        ax.axis("off")
        ax.axis("equal")
        ax.autoscale()
        # plt.subplots_adjust(left=0, bottom=0, right=1, top=1, wspace=0, hspace=0)
        # if "show" in kwargs and not kwargs["show"]:
        #    plt.close()


#
# if credit != False:
#    backgrounds = [result.background for result in subplots_results]
#    global_background = box(*shapely.ops.unary_union(backgrounds).bounds)
#    draw_text(credit, global_background)
