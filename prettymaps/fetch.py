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
import warnings
import numpy as np
import osmnx as ox
from copy import deepcopy
from shapely.geometry import (
    box,
    Point,
    Polygon,
    MultiPolygon,
    LineString,
    MultiLineString,
)
import os
from copy import deepcopy
from geopandas import GeoDataFrame
from shapely.affinity import rotate, scale
from shapely.ops import unary_union
from shapely.errors import ShapelyDeprecationWarning

from IPython.display import display
from skimage.measure import find_contours
import elevation
import geopandas as gp
import rioxarray as rxr
from rasterio.crs import CRS
from .utils import log_execution_time

import logging
from concurrent.futures import ThreadPoolExecutor
import subprocess
import sys
import contextlib
from tqdm import tqdm
from concurrent.futures import as_completed
import pandas as pd

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def get_keypoints(
    perimeter,
    tags={
        "place": "quarter",
        "highway": True,
        "building": True,
        "landuse": True,
        "natural": True,
        "waterway": True,
        "amenity": True,
        "leisure": True,
        "shop": True,
        "public_transport": True,
        "tourism": True,
        "historic": True,
        "barrier": True,
        "power": True,
        "railway": True,
        "cycleway": True,
        "footway": True,
        "healthcare": True,
        "office": True,
        "craft": True,
        "man_made": True,
        "boundary": True,
    },
):
    """
    Extract keypoints from a given perimeter based on specified tags.

    Parameters:
    perimeter (shapely.geometry.Polygon): The polygon representing the area of interest.
    tags (dict, optional): A dictionary of tags to filter the keypoints. The keys are tag names and the values are booleans indicating whether to include the tag. Default includes a variety of common tags.

    Returns:
    geopandas.GeoDataFrame: A GeoDataFrame containing the keypoints that match the specified tags within the given perimeter.
    """
    keypoints_df = ox.features.features_from_polygon(perimeter, tags=tags)

    return keypoints_df


def obtain_elevation(gdf):
    """
    Download all SRTM elevation tiles for the given polygon in a GeoDataFrame.

    Parameters:
    gdf (GeoDataFrame): GeoDataFrame containing the polygon.
    output_dir (str): Directory to save the downloaded tiles.
    """

    # Ensure the GeoDataFrame has a single polygon
    if len(gdf) != 1:
        raise ValueError("GeoDataFrame must contain a single polygon")

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        subprocess.run(
            ["eio", "clean"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

    # Get the bounding box of the polygon
    bounds = gdf.total_bounds
    min_lon, min_lat, max_lon, max_lat = bounds

    # Configure the bounding box for the elevation library

    output_file = os.path.join(os.getcwd(), "elevation.tif")
    elevation.clip(
        bounds=(min_lon, min_lat, max_lon, max_lat),
        output=output_file,
        margin="10%",
        cache_dir=".",
    )

    # subprocess.run(
    #    [
    #        "gdalwarp",
    #        "-tr",
    #        "30",
    #        "30",
    #        "-r",
    #        "cubic",
    #        "elevation.tif",
    #        "resampled_elevation.tif",
    #    ],
    #    # stdout=subprocess.DEVNULL,
    #    # stderr=subprocess.DEVNULL,
    # )

    raster = rxr.open_rasterio(output_file).squeeze()

    raster = raster.rio.reproject(CRS.from_string(ox.projection.project_gdf(gdf).crs.to_string()))

    # convert to numpy array
    elevation_data = raster.data

    return elevation_data


def get_sea_mask(gdf):
    elevation = obtain_elevation(gdf)
    sea_mask = elevation < 0
    sea_mask = sea_mask.T
    contours = find_contours(sea_mask, 0.5)
    # convert to GeoDataFrame
    sea_gdf = gp.GeoDataFrame(
        geometry=[
            Polygon(
                [
                    (
                        x * gdf.total_bounds[2] / sea_mask.shape[1]
                        + gdf.total_bounds[0],
                        y * gdf.total_bounds[3] / sea_mask.shape[0]
                        + gdf.total_bounds[1],
                    )
                    for x, y in contour
                ]
            )
            for contour in contours
        ],
        crs=gdf.crs,
    )
    return sea_gdf


# Parse query (by coordinates, OSMId or name)
def parse_query(query):
    if isinstance(query, GeoDataFrame):
        return "polygon"
    elif isinstance(query, tuple):
        return "coordinates"
    elif re.match("""[A-Z][0-9]+""", query):
        return "osmid"
    else:
        return "address"


# Get circular or square boundary around point
def get_boundary(query, radius, circle=False, rotation=0):

    # Get point from query
    point = query if parse_query(query) == "coordinates" else ox.geocoder.geocode(query)
    # Create GeoDataFrame from point
    boundary = ox.projection.project_gdf(
        GeoDataFrame(geometry=[Point(point[::-1])], crs="EPSG:4326")
    )

    if circle:  # Circular shape
        # use .buffer() to expand point into circle
        boundary.geometry = boundary.geometry.buffer(radius)
    else:  # Square shape
        x, y = np.concatenate(boundary.geometry[0].xy)
        r = radius
        boundary = GeoDataFrame(
            geometry=[
                rotate(
                    Polygon(
                        [(x - r, y - r), (x + r, y - r), (x + r, y + r), (x - r, y + r)]
                    ),
                    rotation,
                )
            ],
            crs=boundary.crs,
        )

    # Unproject
    boundary = boundary.to_crs(4326)

    return boundary


# Get perimeter from query
def get_perimeter(
    query,
    radius=None,
    by_osmid=False,
    circle=False,
    dilate=None,
    rotation=0,
    aspect_ratio=1,
    **kwargs,
):

    if radius:
        # Perimeter is a circular or square shape
        perimeter = get_boundary(query, radius, circle=circle, rotation=rotation)
    else:
        # Perimeter is a OSM or user-provided polygon
        if parse_query(query) == "polygon":
            # Perimeter was already provided
            perimeter = query
        else:
            # Fetch perimeter from OSM
            perimeter = ox.geocoder.geocode_to_gdf(
                query,
                by_osmid=by_osmid,
                **kwargs,
            )

    # Scale according to aspect ratio
    perimeter = ox.projection.project_gdf(perimeter)
    perimeter.loc[0, "geometry"] = scale(perimeter.loc[0, "geometry"], aspect_ratio, 1)
    perimeter = perimeter.to_crs(4326)

    # Apply dilation
    perimeter = ox.projection.project_gdf(perimeter)
    if dilate is not None:
        perimeter.geometry = perimeter.geometry.buffer(dilate)
    perimeter = perimeter.to_crs(4326)

    return perimeter


"""
def cache_geometry(func, cache_dir="cache"):
    def wrapper(*args, **kwargs):
        if "cache" in kwargs and kwargs["cache"]:
            os.makedirs(cache_dir, exist_ok=True)

            perimeter = args[1]
            # Create hash from perimeter
            perimeter_hash = hash(perimeter.to_json())
            # Create hash from kwargs
            kwargs_hash = hash(str(kwargs))
            # Join hashes
            hash_str = f"{perimeter_hash}_{kwargs_hash}"

            # Check if the gdf is cached
            if os.path.exists(os.path.join(cache_dir, f"{hash_str}.geojson")):
                # Read cached gdf
                gdf = gp.read_file(os.path.join(cache_dir, f"{hash_str}.geojson"))
                return gdf
            else:
                # Obtain gdf from OSM
                gdf = func(*args, **kwargs)
                # Write gdf to cache
                # Suppress logging
                logging.getLogger().setLevel(logging.CRITICAL)
                if not gdf.empty:
                    gdf.to_file(
                        os.path.join(cache_dir, f"{hash_str}.geojson"), driver="GeoJSON"
                    )
                logging.getLogger().setLevel(logging.INFO)
        else:
            gdf = func(*args, **kwargs)

        return gdf

    return wrapper
"""


def write_to_cache(
    perimeter: GeoDataFrame,
    gdf: GeoDataFrame,
    layer_kwargs: dict,
    cache_dir: str = "prettymaps_cache",
):
    """
    Write a GeoDataFrame to the cache based on the perimeter and layer arguments.

    Parameters:
    perimeter (GeoDataFrame): The perimeter GeoDataFrame.
    gdf (GeoDataFrame): The GeoDataFrame to cache.
    layer_kwargs (dict): Dictionary of layer arguments.
    cache_dir (str): Directory to save the cached GeoDataFrame.
    """
    np.random.seed(0)
    os.makedirs(cache_dir, exist_ok=True)

    # Create hash from perimeter
    perimeter_hash = hash(perimeter["geometry"].to_json())
    # Create hash from kwargs
    kwargs_hash = hash(str(layer_kwargs))
    # Join hashes
    hash_str = f"{perimeter_hash}_{kwargs_hash}"

    cache_path = os.path.join(cache_dir, f"{hash_str}.geojson")

    # Write gdf to cache
    logging.getLogger().setLevel(logging.CRITICAL)
    if not gdf.empty:
        gdf.to_file(cache_path, driver="GeoJSON")
    logging.getLogger().setLevel(logging.INFO)


def read_from_cache(
    perimeter: GeoDataFrame,
    layer_kwargs: dict,
    cache_dir: str = "prettymaps_cache",
) -> GeoDataFrame:
    """
    Read a GeoDataFrame from the cache based on the perimeter and layer arguments.

    Parameters:
    perimeter (GeoDataFrame): The perimeter GeoDataFrame.
    layer_kwargs (dict): Dictionary of layer arguments.
    cache_dir (str): Directory to read the cached GeoDataFrame from.

    Returns:
    GeoDataFrame: The cached GeoDataFrame, or None if it does not exist.
    """
    np.random.seed(0)
    # Create hash from perimeter
    perimeter_hash = hash(perimeter["geometry"].to_json())
    # Create hash from kwargs
    kwargs_hash = hash(str(layer_kwargs))
    # Join hashes
    hash_str = f"{perimeter_hash}_{kwargs_hash}"

    cache_path = os.path.join(cache_dir, f"{hash_str}.geojson")

    # Check if the gdf is cached
    if os.path.exists(cache_path):
        # Read cached gdf
        return gp.read_file(cache_path)
    else:
        return None


"""
# Get a GeoDataFrame
# @log_execution_time
@cache_geometry
def get_gdf(
    layer,
    perimeter,
    perimeter_tolerance=0,
    tags=None,
    osmid=None,
    custom_filter=None,
    union=False,
    vert_exag=1,
    azdeg=90,
    altdeg=80,
    pad=1,
    min_height=30,
    max_height=None,
    n_curves=100,
    cache=True,
    **kwargs,
):

    # Apply tolerance to the perimeter
    perimeter_with_tolerance = (
        ox.projection.project_gdf(perimeter).buffer(perimeter_tolerance).to_crs(4326)
    )
    perimeter_with_tolerance = unary_union(perimeter_with_tolerance.geometry).buffer(0)

    # Fetch from perimeter's bounding box, to avoid missing some geometries
    bbox = box(*perimeter_with_tolerance.bounds)

    try:
        if layer in ["streets", "railway", "waterway"]:
            graph = ox.graph_from_polygon(
                bbox,
                retain_all=True,
                custom_filter=custom_filter,
                truncate_by_edge=True,
            )
            gdf = ox.graph_to_gdfs(graph, nodes=False)
        elif layer == "sea":
            # Fetch geometries from OSM
            coastline = unary_union(
                ox.features.features_from_polygon(
                    bbox, tags={"natural": "coastline"}
                ).geometry.tolist()
            )
            sea_candidates = bbox.difference(coastline.buffer(1e-9)).geoms
            # sea_mask = get_sea_mask(gdf)
            drive = ox.graph_from_polygon(bbox, network_type="drive")
            drive = ox.graph_to_gdfs(drive, nodes=False)

            # Filter out sea candidates that intersect with the drive network (but use a margin of tolerance)
            def filter_candidate(sea_candidate):
                intersections = drive.geometry.intersects(sea_candidate)
                if "bridge" in drive.columns:
                    return not any(
                        intersections
                        & (
                            drive.loc[
                                drive.geometry.intersects(sea_candidate), "bridge"
                            ]
                            != "yes"
                        )
                    )
                else:
                    return not any(intersections)

            sea = unary_union(
                MultiPolygon(
                    [
                        candidate
                        for candidate in sea_candidates
                        if filter_candidate(candidate)
                    ]
                ).geoms
            ).buffer(1e-8)
            gdf = GeoDataFrame(geometry=[sea], crs=perimeter.crs)
        else:
            if osmid is None:
                # Fetch geometries from OSM
                gdf = ox.features.features_from_polygon(
                    bbox, tags={tags: True} if type(tags) == str else tags
                )
            else:
                gdf = ox.geocoder.geocode_to_gdf(osmid, by_osmid=True)
    except Exception as e:
        # print(f"Error fetching {layer}: {e}")
        gdf = GeoDataFrame(geometry=[])

    # Intersect with perimeter
    gdf.geometry = gdf.geometry.intersection(perimeter_with_tolerance)
    gdf.drop(gdf[gdf.geometry.is_empty].index, inplace=True)

    return gdf


# Fetch GeoDataFrames given query and a dictionary of layers
@log_execution_time
def get_gdfs(query, layers_dict, radius, dilate, rotation=0, logging=False) -> dict:

    perimeter_kwargs = {}
    if "perimeter" in layers_dict:
        perimeter_kwargs = deepcopy(layers_dict["perimeter"])
        perimeter_kwargs.pop("dilate")

    # Get perimeter
    perimeter = get_perimeter(
        query,
        radius=radius,
        rotation=rotation,
        dilate=dilate,
        **perimeter_kwargs,
    )

    # Get other layers as GeoDataFrames
    gdfs = {"perimeter": perimeter}

    def fetch_layer(layer, kwargs):
        return layer, get_gdf(layer, perimeter, logging=logging, **kwargs)

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [
            executor.submit(fetch_layer, layer, kwargs)
            for layer, kwargs in layers_dict.items()
        ]
        results = [
            future.result()
            for future in tqdm(
                as_completed(futures), total=len(futures), desc="Fetching layers"
            )
        ]

    gdfs.update({layer: gdf for layer, gdf in results if layer != "perimeter"})

    return gdfs
"""


def merge_tags(layers_dict: dict) -> dict:
    """
    Merge tags from a dictionary of layers into a single dictionary.

    Parameters:
    layers_dict (dict): Dictionary of layers with their respective tags.

    Returns:
    dict: Merged dictionary of tags.
    """

    layers_dict = deepcopy(layers_dict)
    merged_tags = {}

    def _merge(d: dict):
        for key, value in d.items():
            if isinstance(value, dict):
                if "tags" in value:
                    for tag_key, tag_value in value["tags"].items():
                        if tag_key in merged_tags:
                            if isinstance(merged_tags[tag_key], list):
                                if isinstance(tag_value, list):
                                    merged_tags[tag_key].extend(tag_value)
                                else:
                                    merged_tags[tag_key].append(tag_value)
                            else:
                                merged_tags[tag_key] = (
                                    [merged_tags[tag_key], tag_value]
                                    if not isinstance(tag_value, list)
                                    else [merged_tags[tag_key]] + tag_value
                                )
                        else:
                            merged_tags[tag_key] = (
                                tag_value
                                if isinstance(tag_value, list)
                                else [tag_value]
                            )
                _merge(value)

    _merge(layers_dict)

    # Simplify lists with a single element
    merged_tags = {
        k: (v[0] if isinstance(v, list) and len(v) == 1 else v)
        for k, v in merged_tags.items()
    }

    return merged_tags


def unified_osm_request(
    perimeter: GeoDataFrame, layers_dict: dict, logging: bool = False
) -> dict:
    """
    Unify all OSM requests into one to improve efficiency.

    Parameters:
    perimeter (GeoDataFrame): The perimeter GeoDataFrame.
    layers_dict (dict): Dictionary of layers to fetch.
    logging (bool): Enable or disable logging.

    Returns:
    dict: Dictionary of GeoDataFrames for each layer.
    """
    # Apply tolerance to the perimeter
    perimeter_with_tolerance = ox.projection.project_gdf(perimeter).buffer(0).to_crs(4326)
    perimeter_with_tolerance = unary_union(perimeter_with_tolerance.geometry).buffer(0)

    # Fetch from perimeter's bounding box, to avoid missing some geometries
    bbox = box(*perimeter_with_tolerance.bounds)

    # Initialize the result dictionary
    gdfs = {}
    # Read layers from cache (skips network fetch entirely on a hit)
    for layer, kwargs in layers_dict.items():
        if layer == "perimeter":
            continue
        cached = read_from_cache(perimeter, kwargs)
        if cached is not None:
            gdfs[layer] = cached

    # Combine all tags into a single dictionary for a unified request
    combined_tags = merge_tags(
        {layer: kwargs for layer, kwargs in layers_dict.items() if layer not in gdfs}
    )

    # Fetch all features in one request (skip if every tag-based layer was cached)
    all_features = GeoDataFrame(geometry=[])
    if combined_tags:
        try:
            all_features = ox.features.features_from_polygon(bbox, tags=combined_tags)
        except Exception as e:
            all_features = GeoDataFrame(geometry=[])

    # Split the features into separate GeoDataFrames based on the layers_dict
    for layer, kwargs in layers_dict.items():
        if layer in gdfs:
            continue
        try:
            if layer in ["streets", "railway", "waterway"]:
                graph = ox.graph_from_polygon(
                    bbox,
                    custom_filter=kwargs.get("custom_filter"),
                    truncate_by_edge=True,
                )
                gdf = ox.graph_to_gdfs(graph, nodes=False)
            elif layer == "sea":
                try:
                    coastline = unary_union(
                        ox.features.features_from_polygon(
                            bbox, tags={"natural": "coastline"}
                        ).geometry.tolist()
                    )
                    sea_candidates = bbox.difference(coastline.buffer(1e-9)).geoms
                    drive = ox.graph_from_polygon(bbox, network_type="drive")
                    drive = ox.graph_to_gdfs(drive, nodes=False)

                    def filter_candidate(sea_candidate):
                        intersections = drive.geometry.intersects(sea_candidate)
                        if "bridge" in drive.columns:
                            return not any(
                                intersections
                                & (
                                    drive.loc[
                                        drive.geometry.intersects(sea_candidate),
                                        "bridge",
                                    ]
                                    != "yes"
                                )
                            )
                        else:
                            return not any(intersections)

                    sea = unary_union(
                        MultiPolygon(
                            [
                                candidate
                                for candidate in sea_candidates
                                if filter_candidate(candidate)
                            ]
                        ).geoms
                    ).buffer(1e-8)
                    gdf = GeoDataFrame(geometry=[sea], crs=perimeter.crs)
                except:
                    gdf = GeoDataFrame(geometry=[], crs=perimeter.crs)
            else:
                if kwargs.get("osmid") is None:
                    if layer == "perimeter":
                        gdf = perimeter
                    else:
                        layer_tags = kwargs.get("tags")
                        gdf = gp.GeoDataFrame(geometry=[], crs=perimeter.crs)
                        for key, value in layer_tags.items():
                            if key not in all_features.columns:
                                continue
                            if isinstance(value, bool) and value:
                                filtered_features = all_features[
                                    ~pd.isna(all_features[key])
                                ]
                            elif isinstance(value, list):
                                filtered_features = all_features[
                                    all_features[key].isin(value)
                                ]
                            else:
                                filtered_features = all_features[
                                    all_features[key] == value
                                ]
                            gdf = pd.concat([gdf, filtered_features], axis=0)
                else:
                    gdf = ox.geocoder.geocode_to_gdf(kwargs.get("osmid"), by_osmid=True)

            gdf = gdf.copy()
            gdf.geometry = gdf.geometry.intersection(perimeter_with_tolerance)
            gdf.drop(gdf[gdf.geometry.is_empty].index, inplace=True)
            gdfs[layer] = gdf
            if layer != "perimeter":
                write_to_cache(perimeter, gdf, kwargs)
        except Exception as e:
            # print(f"Error fetching {layer}: {e}")
            gdfs[layer] = GeoDataFrame(geometry=[])

    return gdfs


# Fetch GeoDataFrames given query and a dictionary of layers
@log_execution_time
def get_gdfs(query, layers_dict, radius, dilate, rotation=0, logging=False) -> dict:

    perimeter_kwargs = {}
    if "perimeter" in layers_dict:
        perimeter_kwargs = deepcopy(layers_dict["perimeter"])
        perimeter_kwargs.pop("dilate")

    # Get perimeter
    perimeter = get_perimeter(
        query,
        radius=radius,
        rotation=rotation,
        dilate=dilate,
        **perimeter_kwargs,
    )

    # Get all layers as GeoDataFrames in one unified request
    gdfs = unified_osm_request(perimeter, layers_dict, logging=logging)
    gdfs["perimeter"] = perimeter

    return gdfs
