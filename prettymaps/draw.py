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

# Standard library imports
import json
import logging
import os
import time
import pathlib
import warnings
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, Union

# Third-party imports
import cv2
import geopandas as gp
import matplotlib
import numpy as np
import osmnx as ox
import pandas as pd
import shapely.affinity
import shapely.ops
import vsketch
from matplotlib import pyplot as plt
from matplotlib.colors import LightSource
from matplotlib.patches import Path, PathPatch
from shapely.geometry import (
    GeometryCollection,
    LineString,
    MultiLineString,
    MultiPolygon,
    Point,
    Polygon,
    box,
)
from shapely.geometry.base import BaseGeometry
from sklearn.preprocessing import MinMaxScaler
from thefuzz import fuzz
import shutil

# Local imports
from .fetch import get_gdfs, obtain_elevation, get_keypoints
from .gpx import read_track, is_track_file, track_center, track_radius
from .utils import log_execution_time

# Default matplotlib style for a GPX/KML track layer (see the `gpx` arg of plot()).
GPX_STYLE = {"ec": "#EB4034", "lw": 3, "zorder": 6}

# Log configuration for elapsed time
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# =============================================================================
# Classes
# =============================================================================


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
    Dataclass implementing a prettymaps Plot object.

    Attributes:
        geodataframes (Dict[str, gp.GeoDataFrame]): A dictionary of GeoDataFrames (one for each plot layer).
        fig (matplotlib.figure.Figure): A matplotlib figure.
        ax (matplotlib.axes.Axes): A matplotlib axis object.
        background (BaseGeometry): Background layer (shapely object).
        keypoints (gp.GeoDataFrame): Keypoints GeoDataFrame.
    """

    geodataframes: Dict[str, gp.GeoDataFrame]
    fig: matplotlib.figure.Figure
    ax: matplotlib.axes.Axes
    background: BaseGeometry
    keypoints: gp.GeoDataFrame


@dataclass
class Preset:
    """
    Dataclass implementing a prettymaps Preset object.

    Attributes:
        params (dict): Dictionary of prettymaps.plot() parameters.
    """

    params: dict


class PolygonPatch(PathPatch):
    """
    A class to create a matplotlib PathPatch from a shapely geometry.

    Attributes:
        shape (BaseGeometry): Shapely geometry.
        kwargs: Parameters for matplotlib's PathPatch constructor.

    Methods:
        __init__(shape: BaseGeometry, **kwargs):
            Initialize the PolygonPatch with the given shapely geometry and additional parameters.


            shape (BaseGeometry): Shapely geometry.
            kwargs: Parameters for matplotlib's PathPatch constructor.
    """

    def __init__(self, shape: BaseGeometry, **kwargs):
        """
        Initialize the PolygonPatch.

        Args:
            shape (BaseGeometry): Shapely geometry
            kwargs: parameters for matplotlib's PathPatch constructor
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
        # Initialize PathPatch with the generated Path
        super().__init__(
            Path(np.concatenate(vertices, 1).T, np.concatenate(codes)), **kwargs
        )


# =============================================================================
# Functions to draw GeoDataFrames / elevation maps
# =============================================================================


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
    gdf["width"] = (
        gdf["highway"].map(highway_to_width) if type(width) == dict else width
    )

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

    # Project gdf if applicable
    if not gdf.empty and gdf.crs is not None:
        gdf = ox.projection.project_gdf(gdf)

    if layer in ["streets", "railway", "waterway"]:
        geometries = graph_to_shapely(gdf, width)
    else:
        geometries = geometries_to_shapely(
            gdf, point_size=point_size, line_width=line_width
        )

    return geometries


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
                            if k in ["lw", "ls", "dashes", "zorder"]
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


def plot_legends(
    keypoints_df, ax, dx=0, dy=0, bbox=dict(fc="#F2F4CB", boxstyle="square"), zorder=100
):
    texts = []
    for i in range(len(keypoints_df)):
        x, y = np.concatenate(
            ox.projection.project_gdf(keypoints_df.iloc[[i]]).geometry.iloc[0].centroid.xy
        )
        name = keypoints_df.name.iloc[i]
        kwargs = keypoints_df.kwargs.iloc[i]
        if not pd.isna(name):
            texts.append(
                ax.text(
                    x + dx,
                    y + dy,
                    name,
                    bbox=bbox,
                    zorder=zorder,
                    **(kwargs if not pd.isna(kwargs) else {}),
                )
            )

    # adjust_text(texts)


@log_execution_time
def draw_keypoints(keypoints, gdfs, ax, logging=False):
    perimeter = gdfs["perimeter"].geometry[0]
    # Get keypoints
    if "tags" in keypoints:
        keypoints_df = get_keypoints(
            perimeter,
            tags=keypoints["tags"],
        )
    else:
        keypoints_df = gp.GeoDataFrame(geometry=[], crs=gdfs["perimeter"].crs)
    keypoints_df["kwargs"] = [
        keypoints["kwargs"] if "kwargs" in keypoints else {}
    ] * len(keypoints_df)
    # Remove unwanted keypoints
    if "remove" in keypoints:
        for query in keypoints["remove"]:
            match = match_keypoint(keypoints_df, query)
            keypoints_df = keypoints_df.drop(match.index)
    if "specific" in keypoints:
        for query, kwargs in keypoints["specific"].items():
            specific_keypoints_df = get_keypoints(
                perimeter,
                tags=kwargs["tags"],
            )
            match = match_keypoint(specific_keypoints_df, query)
            if not pd.isna(match.name).iloc[0]:
                # Add match to keypoints_df
                keypoints_df = pd.concat([keypoints_df, match])
    # Add kwargs column
    if "style" in keypoints:
        for query, kwargs in keypoints["style"].items():
            match = match_keypoint(keypoints_df, query)
            if not pd.isna(match.name).iloc[0]:
                keypoints_df.loc[match.index, "kwargs"] = kwargs
    # Plot keypoints
    plot_legends(
        keypoints_df,
        ax,
    )
    return keypoints_df


@log_execution_time
def draw_layers(layers, gdfs, style, fig, ax, vsk, mode, logging=False):
    for layer in gdfs:
        if (layer in layers) or (layer in style):
            plot_gdf(
                layer,
                gdfs[layer],
                ax,
                mode=mode,
                vsk=vsk,
                width=(
                    layers[layer]["width"]
                    if (layer in layers) and ("width" in layers[layer])
                    else None
                ),
                **(style[layer] if layer in style else {}),
            )


@log_execution_time
def draw_hillshade(
    layers,
    gdfs,
    ax,
    azdeg=315,
    altdeg=45,
    vert_exag=1,
    dx=1,
    dy=1,
    alpha=0.75,
    logging=False,
    **kwargs,
):
    if "hillshade" in layers:
        elevation_data = obtain_elevation(gdfs["perimeter"])
        elevation_data = np.clip(elevation_data, 0, None)
        elevation_data = elevation_data.astype(np.float32)
        # Upscale the elevation data to match A1 paper width (594mm)
        scale_factor = 594 / elevation_data.shape[1]
        elevation_data = cv2.resize(
            elevation_data,
            (
                int(elevation_data.shape[1] * scale_factor),
                int(elevation_data.shape[0] * scale_factor),
            ),
        )
        # Perform bilateral filtering to remove noise
        # Apply bilateral filter
        d = 5  # Diameter of each pixel neighborhood
        sigma_color = 5  # Filter sigma in the color space
        sigma_space = 5  # Filter sigma in the coordinate space
        elevation_data = cv2.bilateralFilter(
            elevation_data, d, sigma_color, sigma_space
        )
        ls = LightSource(azdeg=azdeg, altdeg=altdeg)
        hillshade = ls.hillshade(elevation_data, vert_exag=vert_exag, dx=dx, dy=dy)
        # Convert hillshade to RGBA

        # hillshade = np.clip(hillshade, 0, np.inf)
        # hillshade = MinMaxScaler((0, 1)).fit_transform(hillshade)
        hillshade_rgba = np.zeros((*hillshade.shape, 4), dtype=np.uint8)
        hillshade_rgba[..., :3] = (hillshade[..., None] * 255).astype(np.uint8)
        hillshade_rgba[..., 3] = ((1 - hillshade) * 255).astype(np.uint8)

        min_x, max_x = ax.get_xlim()
        min_y, max_y = ax.get_ylim()
        min_lon, min_lat, max_lon, max_lat = ox.projection.project_gdf(
            gdfs["perimeter"]
        ).total_bounds
        ax.imshow(
            hillshade_rgba,
            # cmap="gray",
            alpha=alpha,
            extent=(min_lon, max_lon, min_lat, max_lat),
            zorder=20,
        )
        ax.set_xlim(min_x, max_x)
        ax.set_ylim(min_y, max_y)

        # Delete the ./SRTM1 folder after drawing hillshade
        srtm1_dir = os.path.join(os.getcwd(), "SRTM1")
        if os.path.isdir(srtm1_dir):
            try:
                shutil.rmtree(srtm1_dir)
            except Exception as e:
                if logging:
                    print(f"Warning: Failed to delete {srtm1_dir}: {e}")


@log_execution_time
def create_background(
    gdfs: Dict[str, gp.GeoDataFrame],
    style: Dict[str, dict],
    logging=False,
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
            *shapely.ops.unary_union(ox.projection.project_gdf(gdfs["perimeter"]).geometry).bounds
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


@log_execution_time
def draw_background(
    background,
    ax,
    style,
    mode,
    logging=False,
):
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
    ax.autoscale()


# =============================================================================
# Functions to preprocess GeoDataFrames
# =============================================================================


@log_execution_time
def transform_gdfs(
    gdfs: Dict[str, gp.GeoDataFrame],
    x: float = 0,
    y: float = 0,
    scale_x: float = 1,
    scale_y: float = 1,
    rotation: float = 0,
    logging=False,
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
        name: ox.projection.project_gdf(gdf) if len(gdf) > 0 else gdf for name, gdf in gdfs.items()
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
            gdfs[layer] = ox.projection.project_gdf(gdfs[layer], to_crs="EPSG:4326")

    return gdfs


# =============================================================================
# Functions to manage presets
# =============================================================================


def presets_directory():
    """
    Returns the path to the 'presets' directory.
    This function constructs the path to the 'presets' directory, which is
    located in the same directory as the current script file.
    Returns:
        str: The full path to the 'presets' directory.
    """

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


@log_execution_time
def manage_presets(
    load_preset: Optional[str],
    save_preset: bool,
    update_preset: Optional[str],
    layers: Dict[str, dict],
    style: Dict[str, dict],
    circle: Optional[bool],
    radius: Optional[Union[float, bool]],
    dilate: Optional[Union[float, bool]],
    logging=False,
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


# =============================================================================
# Functions to draw text
# =============================================================================


def draw_text(
    ax: matplotlib.axes.Axes, params: Dict[str, Any], background: BaseGeometry
) -> None:
    """
    Draw text with content and matplotlib style parameters specified by 'params' dictionary.
    params['text'] should contain the message to be drawn.

    Args:
        ax (matplotlib.axes.Axes): Matplotlib axis object.
        params (Dict[str, Any]): Matplotlib style parameters for drawing text. params['text'] should contain the message to be drawn.
        background (BaseGeometry): Background layer.
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
            # fontfamily="Ubuntu Mono",
        ),
        params,
    )
    x, y, text = [params.pop(k) for k in ["x", "y", "text"]]

    # Get background bounds
    xmin, ymin, xmax, ymax = background.bounds

    x = np.interp([x], [0, 1], [xmin, xmax])[0]
    y = np.interp([y], [0, 1], [ymin, ymax])[0]

    ax.text(x, y, text, zorder=1000, **params)


@log_execution_time
def draw_credit(
    ax: matplotlib.axes.Axes,
    background: BaseGeometry,
    credit: Dict[str, Any],
    mode: str,
    multiplot: bool,
    logging: bool = False,
) -> None:
    """
    Draws credit text on the plot.

    Args:
        ax (matplotlib.axes.Axes): Matplotlib axis object.
        background (BaseGeometry): Background layer.
        credit (Dict[str, Any]): Dictionary containing credit text and style parameters.
        mode (str): Drawing mode. Options: 'matplotlib', 'plotter'.
        multiplot (bool): Whether the plot is part of a multiplot.
        logging (bool, optional): Whether to enable logging. Defaults to False.
    """
    if (mode == "matplotlib") and (credit != False) and (not multiplot):
        draw_text(ax, credit, background)


# =============================================================================
# Utils
# =============================================================================


@log_execution_time
def init_plot(
    layers,
    fig=None,
    ax=None,
    figsize=(11.7, 11.7),
    mode="matplotlib",
    adjust_aspect_ratio=True,
    logging=False,
):
    if fig is None:
        if figsize == "a4":
            figsize = (1.5 * 8.3, 1.5 * 11.7)
        elif figsize == "a4_r":
            figsize = (1.5 * 11.7, 1.5 * 8.3)

        fig = plt.figure(figsize=figsize, dpi=300)

        if (
            adjust_aspect_ratio
            and ("perimeter" in layers)
            and ("aspect_ratio" not in layers["perimeter"])
        ):
            layers["perimeter"]["aspect_ratio"] = figsize[0] / figsize[1]

    if ax is None:
        ax = plt.subplot(111, aspect="equal")

    ax.axis("off")
    ax.axis("equal")

    if mode == "plotter":
        vsk = vsketch.Vsketch()
        vsk.size("a4", landscape=True)
    else:
        vsk = None

    return fig, ax, vsk


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


@log_execution_time
def override_args(
    layers: dict,
    circle: Optional[bool],
    dilate: Optional[Union[float, bool]],
    logging=False,
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


def match_keypoint(keypoints_df, query, index=0):
    def match_keypoint(keypoints_df, query, index=0):
        """
        Matches a query string to the 'name' column in a DataFrame of keypoints using fuzzy string matching.

        Parameters:
        keypoints_df (pd.DataFrame): DataFrame containing keypoints with a 'name' column.
        query (str): The query string to match against the 'name' column.
        index (int, optional): The index of the match to return if there are multiple matches. Defaults to 0.

        Returns:
        pd.DataFrame: A DataFrame containing the row of the best match based on the fuzzy string matching score.
        """

    # Drop rows where 'name' is NaN
    keypoints_df = keypoints_df.dropna(subset=["name"])
    keypoints_df = keypoints_df[~keypoints_df.geometry.is_empty]

    # Apply fuzzy string matching to the 'name' column
    keypoints_df.loc[:, "match"] = keypoints_df.name.apply(
        lambda x: fuzz.token_sort_ratio(x, query)
    )

    # Find the rows with the highest matching score
    matches = keypoints_df[keypoints_df.match == max(keypoints_df.match)]

    # Return the best match based on the provided index
    return matches.iloc[[min(index, len(matches) - 1)]]


# =============================================================================
# Main plot functions: plot(), ai_plot(), multiplot()
# =============================================================================


def plot(
    query: str | Tuple[float, float] | gp.GeoDataFrame,
    layers: Dict[str, Dict[str, Any]] = {},
    style: Dict[str, Dict[str, Any]] = {},
    keypoints: Dict[str, Any] = {},
    preset: str = "default",
    use_preset: bool = True,
    save_preset: str | None = None,
    update_preset: str | None = None,
    postprocessing: Callable[
        [Dict[str, gp.GeoDataFrame]], Dict[str, gp.GeoDataFrame]
    ] = lambda x: x,
    circle: bool | None = None,
    radius: float | bool | None = None,
    dilate: float | bool | None = None,
    save_as: str | None = None,
    fig: plt.Figure | None = None,
    ax: plt.Axes | None = None,
    figsize: Tuple[float, float] = (11.7, 11.7),
    credit: Dict[str, Any] = {},
    mode: str = "matplotlib",
    multiplot: bool = False,
    show: bool = True,
    x: float = 0,
    y: float = 0,
    scale_x: float = 1,
    scale_y: float = 1,
    rotation: float = 0,
    logging: bool = False,
    semantic: bool = False,
    adjust_aspect_ratio: bool = True,
    gpx: str | List[str] | None = None,
    gpx_style: Dict[str, Any] | None = None,
) -> Plot:
    """
    Plots a map based on a given query and specified parameters.
    Args:
        query: The query for the location to plot. This can be a string (e.g., "Porto Alegre"), a tuple of latitude and longitude coordinates, or a custom GeoDataFrame boundary.
        layers: The OpenStreetMap layers to plot. Defaults to an empty dictionary.
        style: Matplotlib parameters for drawing each layer. Defaults to an empty dictionary.
        keypoints: Keypoints to highlight on the map. Defaults to an empty dictionary.
        preset: Preset configuration to use. Defaults to "default".
        use_preset: Whether to use the preset configuration. Defaults to True.
        save_preset: Path to save the preset configuration. Defaults to None.
        update_preset: Path to update the preset configuration with additional parameters. Defaults to None.
        circle: Whether to use a circular boundary. Defaults to None.
        radius: Radius for the circular or square boundary. Defaults to None.
        dilate: Amount to dilate the boundary. Defaults to None.
        save_as: Path to save the resulting plot. Defaults to None.
        fig: Matplotlib figure object. Defaults to None.
        ax: Matplotlib axes object. Defaults to None.
        title: Title of the plot. Defaults to None.
        figsize: Size of the figure. Defaults to (11.7, 11.7).
        constrained_layout: Whether to use constrained layout for the figure. Defaults to True.
        credit: Parameters for the credit message. Defaults to an empty dictionary.
        mode: Mode for plotting ('matplotlib' or 'plotter'). Defaults to "matplotlib".
        multiplot: Whether to use multiplot mode. Defaults to False.
        show: Whether to display the plot using matplotlib. Defaults to True.
        x: Translation parameter in the x direction. Defaults to 0.
        y: Translation parameter in the y direction. Defaults to 0.
        scale_x: Scaling parameter in the x direction. Defaults to 1.
        scale_y: Scaling parameter in the y direction. Defaults to 1.
        rotation: Rotation parameter in degrees. Defaults to 0.
        logging: Whether to enable logging. Defaults to False.
        gpx: Path (or list of paths) to a GPX/KML file whose track is drawn on the map as a "gpx" layer. If `query` is itself a GPX/KML file, the map is framed around that track and it is drawn automatically. Defaults to None.
        gpx_style: Matplotlib style for the GPX track layer (e.g. {"ec": "#EB4034", "lw": 3}). Overrides `GPX_STYLE`; ignored if `style["gpx"]` is given. Defaults to None.
    Returns:
        Plot: The resulting plot object.
    """

    # 0. Read a GPX/KML track, if given, to frame the map around it and/or draw it
    track_geom = None
    gpx_source = gpx if gpx is not None else (query if is_track_file(query) else None)
    if gpx_source is not None:
        track_geom = read_track(gpx_source)
    if track_geom is not None and is_track_file(query):
        # The query IS the track file: centre the map on the track and, unless the
        # caller fixed a radius, choose one that encloses the whole track.
        if radius is None:
            radius = track_radius(track_geom)
        query = track_center(track_geom)

    # 1. Manage presets
    layers, style, circle, radius, dilate = manage_presets(
        preset if use_preset else None,
        save_preset,
        update_preset,
        layers,
        style,
        circle,
        radius,
        dilate,
    )

    # 2. Init matplotlib figure & axis and vsketch object
    fig, ax, vsk = init_plot(
        layers,
        fig,
        ax,
        figsize,
        mode,
        adjust_aspect_ratio=adjust_aspect_ratio,
        logging=logging,
    )

    # 3. Override arguments in layers' kwargs dict
    layers = override_args(layers, circle, dilate, logging=logging)

    # 4. Fetch geodataframes
    start_time = time.time()
    gdfs = get_gdfs(query, layers, radius, dilate, -rotation, logging=logging)
    fetch_time = time.time() - start_time
    print(f"Fetching geodataframes took {fetch_time:.2f} seconds")

    # 4b. Inject the GPX/KML track as a "gpx" layer (rides through the same
    # projection, transforms and drawing as every other layer).
    if track_geom is not None:
        gdfs["gpx"] = gp.GeoDataFrame(geometry=[track_geom], crs="EPSG:4326")
        layers.setdefault("gpx", {})
        style.setdefault("gpx", {**GPX_STYLE, **(gpx_style or {})})

    # 5. Apply transformations to GeoDataFrames (translation, scale, rotation)
    gdfs = transform_gdfs(gdfs, x, y, scale_x, scale_y, rotation, logging=logging)

    # 6. Apply a postprocessing function to the GeoDataFrames, if provided
    gdfs = postprocessing(gdfs)

    # 7. Create background GeoDataFrame and get (x,y) bounds
    background, xmin, ymin, xmax, ymax, dx, dy = create_background(
        gdfs, style, logging=logging
    )

    # 8. Draw layers
    draw_layers(layers, gdfs, style, fig, ax, vsk, mode, logging=logging)

    # 9. Draw keypoints
    keypoints = draw_keypoints(keypoints, gdfs, ax, logging=logging)

    # 9. Draw background
    draw_background(background, ax, style, mode, logging=logging)

    # 10. Draw credit message
    draw_credit(ax, background, credit, mode, multiplot, logging=logging)

    # 11. Draw hillshade
    draw_hillshade(
        layers,
        gdfs,
        ax,
        logging=logging,
        **(layers["hillshade"] if "hillshade" in layers else {}),
    )

    # 12. Create Plot object
    plot = Plot(gdfs, fig, ax, background, keypoints)

    # 13. Save plot as image
    if save_as is not None:
        plt.savefig(save_as)

    # 14. Show plot
    if show:
        if mode == "plotter":
            vsk.display()
        elif mode == "matplotlib":
            plt.show()
        else:
            raise Exception(f"Unknown mode {mode}")
    else:
        plt.close()

    return plot


def multiplot(*subplots, figsize=None, credit={}, **kwargs):
    """
    Creates a multiplot using the provided subplots and optional parameters.

    Parameters:
    -----------
    *subplots : list
        A list of subplot objects to be plotted.
    figsize : tuple, optional
        A tuple specifying the figure size (width, height) in inches.
    credit : dict, optional
        A dictionary containing credit information for the plot.
    **kwargs : dict, optional
        Additional keyword arguments to customize the plot.

    Returns:
    --------
    None
    """

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
            show=False,
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
