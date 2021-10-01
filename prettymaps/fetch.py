'''
MIT License

Copyright (c) 2021 Marcelo de Oliveira Rosa Prates

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
'''

from ast import Dict
from functools import reduce
from tokenize import Number, String
from typing import Optional, Union, Tuple
from xmlrpc.client import Boolean

import osmnx as ox
from osmnx import utils_geo
from osmnx._errors import EmptyOverpassResponse
import numpy as np
from shapely.geometry import Point, Polygon, MultiPolygon, LineString, MultiLineString
from shapely.ops import unary_union
from geopandas import GeoDataFrame, read_file


def get_boundary(
    point: Tuple, radius: float, crs: String, circle: Boolean = True, dilate: float = 0
) -> Polygon:
    """
    Compute circular or square boundary given point, radius and crs.

    Args:
        point (Tuple): GPS coordinates
        radius (Number): radius in meters
        crs (String): Coordinate Reference System
        circle (bool, optional): Whether to use a circular (True) or square (False) boundary. Defaults to True.
        dilate (int, optional): Dilate the boundary by this much, in meters. Defaults to 0.

    Returns:
        Polygon: a shapely Polygon representing the boundary
    """

    if circle:
        return (
            ox.project_gdf(GeoDataFrame(geometry=[Point(point[::-1])], crs=crs))
            .geometry[0]
            .buffer(radius)
        )
    else:
        x, y = np.stack(
            ox.project_gdf(GeoDataFrame(geometry=[Point(point[::-1])], crs=crs))
            .geometry[0]
            .xy
        )
        r = radius
        return Polygon(
            [(x - r, y - r), (x + r, y - r), (x + r, y + r), (x - r, y + r)]
        ).buffer(dilate)


def get_perimeter(query, by_osmid: Boolean = False, **kwargs) -> GeoDataFrame:
    """
    Fetch perimeter given query

    Args:
        query (String): Query for the perimeter to be fetched (for example, "France")
        by_osmid (bool, optional): Whether to fetch perimeter by OSM Id. Defaults to False.

    Returns:
        GeoDataFrame: GeoDataFrame representation of the perimeter
    """
    return ox.geocode_to_gdf(
        query,
        by_osmid=by_osmid,
        **kwargs,
        **{x: kwargs[x] for x in ["circle", "dilate"] if x in kwargs.keys()}
    )


def get_coast(
    perimeter=None,
    point=None,
    radius=None,
    perimeter_tolerance=0,
    union=True,
    buffer=0,
    circle=True,
    dilate=0,
    file_location=None,
):

    if perimeter is not None:
        # Boundary defined by polygon (perimeter)
        bbox = perimeter.to_crs(3174)
        bbox = bbox.buffer(perimeter_tolerance + dilate + buffer)
        bbox = bbox.to_crs(4326)
        bbox = bbox.envelope
        # Load the polygons for the coastline from a file
        geometries = read_file(file_location, bbox=bbox)
        perimeter = unary_union(ox.project_gdf(perimeter).geometry)

    elif (point is not None) and (radius is not None):
        # Boundary defined by circle with radius 'radius' around point
        north, south, west, east = utils_geo.bbox_from_point(
            point, dist=radius + dilate + buffer
        )
        bbox = (west, south, east, north)
        # Load the polygons for the coastline from a file
        geometries = read_file(file_location, bbox=bbox)
        perimeter = get_boundary(
            point, radius, geometries.crs, circle=circle, dilate=dilate
        )

    # Project GDF
    if len(geometries) > 0:
        geometries = ox.project_gdf(geometries)

    # Intersect with perimeter
    geometries = geometries.intersection(perimeter)

    if union:
        geometries = unary_union(
            reduce(
                lambda x, y: x + y,
                [
                    [x] if type(x) == Polygon else list(x)
                    for x in geometries
                    if type(x) in [Polygon, MultiPolygon]
                ],
                [],
            )
        )
    else:
        geometries = MultiPolygon(
            reduce(
                lambda x, y: x + y,
                [
                    [x] if type(x) == Polygon else list(x)
                    for x in geometries
                    if type(x) in [Polygon, MultiPolygon]
                ],
                [],
            )
        )

    return geometries


def get_geometries(
    perimeter: Optional[GeoDataFrame] = None,
    point: Optional[Tuple] = None,
    radius: Optional[float] = None,
    tags: Dict = {},
    perimeter_tolerance: float = 0,
    union: Boolean = True,
    buffer: float = 0,
    circle: Boolean = True,
    dilate: float = 0,
    point_size: float = 1,
    line_width: float = 1
) -> Union[Polygon, MultiPolygon]:
    """Get geometries

    Args:
        perimeter (Optional[GeoDataFrame], optional): Perimeter from within geometries will be fetched. Defaults to None.
        point (Optional[Tuple], optional): GPS coordinates. Defaults to None.
        radius (Optional[Number], optional): Radius in meters. Defaults to None.
        tags (Dict, optional): OpenStreetMap tags for the geometries to be fetched. Defaults to {}.
        perimeter_tolerance (Number, optional): Tolerance in meters for fetching geometries that fall outside the perimeter. Defaults to 0.
        union (Boolean, optional): Whether to compute the union of all geometries. Defaults to True.
        circle (Boolean, optional): Whether to fetch geometries in a circular (True) or square (False) shape. Defaults to True.
        dilate (Number, optional): Dilate the boundary by this much in meters. Defaults to 0.

    Returns:
        [type]: [description]
    """

    # Boundary defined by polygon (perimeter)
    if perimeter is not None:
        geometries = ox.geometries_from_polygon(
            unary_union(perimeter.to_crs(3174).buffer(buffer+perimeter_tolerance).to_crs(4326).geometry)
            if buffer >0 or perimeter_tolerance > 0
            else unary_union(perimeter.geometry),
            tags={tags: True} if type(tags) == str else tags,
        )
        perimeter = unary_union(ox.project_gdf(perimeter).geometry)
    # Boundary defined by circle with radius 'radius' around point
    elif (point is not None) and (radius is not None):
        geometries = ox.geometries_from_point(
            point,
            dist=radius + dilate + buffer,
            tags={tags: True} if type(tags) == str else tags,
        )
        perimeter = get_boundary(
            point, radius, geometries.crs, circle=circle, dilate=dilate
        )

    # Project GDF
    if len(geometries) > 0:
        geometries = ox.project_gdf(geometries)

    # Intersect with perimeter
    geometries = geometries.intersection(perimeter)

    # Get points, lines, polys & multipolys
    points, lines, polys, multipolys = map(
        lambda t: [x for x in geometries if isinstance(x, t)],
        [Point, LineString, Polygon, MultiPolygon]
    )
    # Convert points, lines & polygons into multipolygons
    points = [x.buffer(point_size) for x in points]
    lines = [x.buffer(line_width) for x in lines]
    # Concatenate multipolys
    multipolys = reduce(lambda x,y: x+y, [list(x) for x in multipolys]) if len(multipolys) > 0 else []
    # Group everything
    geometries = MultiPolygon(points + lines + polys + multipolys)
    # Compute union if specified
    if union: geometries = unary_union(geometries);

    return geometries


def get_streets(
    perimeter: Optional[GeoDataFrame] = None,
    point: Optional[Tuple] = None,
    radius: Optional[float] = None,
    layer: String = "streets",
    width: float = 6,
    custom_filter: Optional[str] = None,
    buffer: float = 0,
    retain_all: Boolean = False,
    circle: Boolean = True,
    dilate: float = 0,
    truncate_by_edge: Boolean = True 
) -> MultiPolygon:
    """
    Get streets

    Args:
        perimeter (Optional[GeoDataFrame], optional): [description]. Defaults to None.
        point (Optional[Tuple], optional): [description]. Defaults to None.
        radius (Optional[Number], optional): [description]. Defaults to None.
        layer (String, optional): [description]. Defaults to "streets".
        width (Number, optional): [description]. Defaults to 6.
        custom_filter (Optional[String], optional): [description]. Defaults to None.
        buffer (Number, optional): [description]. Defaults to 0.
        retain_all (Boolean, optional): [description]. Defaults to False.
        circle (Boolean, optional): [description]. Defaults to True.
        dilate (Number, optional): [description]. Defaults to 0.
        truncate_by_edge (Boolean, optional): [description]. Defaults to True.

    Returns:
        MultiPolygon: [description]
    """

    if layer == "streets":
        layer = "highway"

    # Boundary defined by polygon (perimeter)
    if perimeter is not None:
        # Fetch streets data, project & convert to GDF
        try:
            streets = ox.graph_from_polygon(
                unary_union(perimeter.geometry).buffer(buffer)
                if buffer > 0
                else unary_union(perimeter.geometry),
                custom_filter=custom_filter,
            )
            streets = ox.project_graph(streets)
            streets = ox.graph_to_gdfs(streets, nodes=False)
        except EmptyOverpassResponse:
            return MultiLineString()
    # Boundary defined by polygon (perimeter)
    elif (point is not None) and (radius is not None):
        # Fetch streets data, save CRS & project
        try:
            streets = ox.graph_from_point(
                point,
                dist=radius + dilate + buffer,
                retain_all=retain_all,
                custom_filter=custom_filter,
                truncate_by_edge = truncate_by_edge,
            )
            crs = ox.graph_to_gdfs(streets, nodes=False).crs
            streets = ox.project_graph(streets)
            # Compute perimeter from point & CRS
            perimeter = get_boundary(point, radius, crs, circle=circle, dilate=dilate)
            # Convert to GDF
            streets = ox.graph_to_gdfs(streets, nodes=False)
            # Intersect with perimeter & filter empty elements
            streets.geometry = streets.geometry.intersection(perimeter)
            streets = streets[~streets.geometry.is_empty]
        except EmptyOverpassResponse:
            return MultiLineString()

    if type(width) == dict:
        streets = unary_union(
            [
                # Dilate streets of each highway type == 'highway' using width 'w'
                MultiLineString(
                    streets[
                        [highway in value for value in streets[layer]]
                        & (streets.geometry.type == "LineString")
                    ].geometry.tolist()
                    + list(
                        reduce(
                            lambda x, y: x + y,
                            [
                                list(lines)
                                for lines in streets[
                                    [highway in value for value in streets[layer]]
                                    & (streets.geometry.type == "MultiLineString")
                                ].geometry
                            ],
                            [],
                        )
                    )
                ).buffer(w)
                for highway, w in width.items()
            ]
        )
    else:
        # Dilate all streets by same amount 'width'
        streets=  MultiLineString(
            streets[streets.geometry.type == "LineString"].geometry.tolist()
            + list(
                reduce(
                    lambda x, y: x + y,
                    [
                        list(lines)
                        for lines in streets[streets.geometry.type == "MultiLineString"].geometry
                    ],
                    [],
                )
            )
        ).buffer(width)

    return streets


def get_layer(layer: String, **kwargs) -> Union[Polygon, MultiPolygon]:
    """[summary]

    Args:
        layer (String): [description]

    Raises:
        Exception: [description]

    Returns:
        Union[Polygon, MultiPolygon]: [description]
    """
    # Fetch perimeter
    if layer == "perimeter":
        # If perimeter is already provided:
        if "perimeter" in kwargs:
            return unary_union(ox.project_gdf(kwargs["perimeter"]).geometry)
        # If point and radius are provided:
        elif "point" in kwargs and "radius" in kwargs:
            crs = "EPSG:4326"
            perimeter = get_boundary(
                kwargs["point"],
                kwargs["radius"],
                crs,
                **{x: kwargs[x] for x in ["circle", "dilate"] if x in kwargs.keys()}
            )
            return perimeter
        else:
            raise Exception("Either 'perimeter' or 'point' & 'radius' must be provided")
    # Fetch streets or railway
    if layer in ["streets", "railway", "waterway"]:
        return get_streets(**kwargs, layer=layer)
    # Fetch Coastline
    elif layer == "coastline":
        return get_coast(**kwargs)
    # Fetch geometries
    else:
        return get_geometries(**kwargs)
