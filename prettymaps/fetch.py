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

from ast import Dict
from functools import reduce
from tokenize import Number, String
from typing import Optional, Union, Tuple

# from unittest.runner import _ResultClassType
from xmlrpc.client import Boolean

import re
import osmnx as ox
from osmnx import utils_geo
from osmnx._errors import EmptyOverpassResponse
import numpy as np
from shapely.geometry import (
    box,
    Point,
    Polygon,
    MultiPolygon,
    LineString,
    MultiLineString,
)
from shapely.affinity import rotate
from shapely.ops import unary_union
from geopandas import GeoDataFrame, read_file
import warnings
from shapely.errors import ShapelyDeprecationWarning
from copy import deepcopy


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
    point = query if parse_query(query) == "coordinates" else ox.geocode(query)
    # Create GeoDataFrame from point
    boundary = ox.project_gdf(
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
                        [(x - r, y - r), (x + r, y - r),
                         (x + r, y + r), (x - r, y + r)]
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
    query, radius=None, by_osmid=False, circle=False, dilate=None, rotation=0, **kwargs
):

    if radius:
        # Perimeter is a circular or square shape
        perimeter = get_boundary(
            query, radius, circle=circle, rotation=rotation)
    else:
        # Perimeter is a OSM or user-provided polygon
        if parse_query(query) == "polygon":
            # Perimeter was already provided
            perimeter = query
        else:
            # Fetch perimeter from OSM
            perimeter = ox.geocode_to_gdf(
                query,
                by_osmid=by_osmid,
                **kwargs,
            )

    # Apply dilation
    perimeter = ox.project_gdf(perimeter)
    if dilate is not None:
        perimeter.geometry = perimeter.geometry.buffer(dilate)
    perimeter = perimeter.to_crs(4326)

    return perimeter


# Get a GeoDataFrame
def get_gdf(
    layer,
    perimeter,
    perimeter_tolerance=0,
    tags=None,
    osmid=None,
    custom_filter=None,
    union=False,
    elevation=None,
    vert_exag=1,
    azdeg=90,
    altdeg=80,
    pad=1,
    min_height=30,
    max_height=None,
    n_curves=100,
    **kwargs
):

    # Supress shapely deprecation warning
    warnings.simplefilter("ignore", ShapelyDeprecationWarning)

    # Apply tolerance to the perimeter
    perimeter_with_tolerance = (
        ox.project_gdf(perimeter).buffer(perimeter_tolerance).to_crs(4326)
    )
    perimeter_with_tolerance = unary_union(
        perimeter_with_tolerance.geometry).buffer(0)

    # Fetch from perimeter's bounding box, to avoid missing some geometries
    bbox = box(*perimeter_with_tolerance.bounds)

    if layer == "hillshade":
        gdf = get_hillshade(
            mask_elevation(get_elevation(elevation), perimeter),
            pad=pad,
            azdeg=azdeg,
            altdeg=altdeg,
            vert_exag=vert_exag,
            min_height=min_height,
            max_height=max_height,
        )
    elif layer == "level_curves":
        gdf = get_level_curves(
            mask_elevation(get_elevation(elevation), perimeter),
            pad=pad,
            n_curves=n_curves,
            min_height=min_height,
            max_height=max_height,
        )
    elif layer in ["streets", "railway", "waterway"]:
        graph = ox.graph_from_polygon(
            bbox,
            custom_filter=custom_filter,
            truncate_by_edge=True,
        )
        gdf = ox.graph_to_gdfs(graph, nodes=False)
    elif layer == "coastline":
        # Fetch geometries from OSM
        gdf = ox.geometries_from_polygon(
            bbox, tags={tags: True} if type(tags) == str else tags
        )
    else:
        if osmid is None:
            # Fetch geometries from OSM
            gdf = ox.geometries_from_polygon(
                bbox, tags={tags: True} if type(tags) == str else tags
            )
        else:
            gdf = ox.geocode_to_gdf(osmid, by_osmid=True)

    # Intersect with perimeter
    gdf.geometry = gdf.geometry.intersection(perimeter_with_tolerance)
    # gdf = gdf[~gdf.geometry.is_empty]
    gdf.drop(gdf[gdf.geometry.is_empty].index, inplace=True)

    return gdf


# Fetch GeoDataFrames given query and a dictionary of layers
def get_gdfs(query, layers_dict, radius, dilate, rotation=0) -> dict:

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
        **perimeter_kwargs
    )

    # Get other layers as GeoDataFrames
    gdfs = {"perimeter": perimeter}
    gdfs.update({
        layer: get_gdf(layer, perimeter, **kwargs)
        for layer, kwargs in layers_dict.items()
        if layer != "perimeter"
    })

    return gdfs
