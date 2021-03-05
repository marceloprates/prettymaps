# OpenStreetMap Networkx library to download data from OpenStretMap
import osmnx as ox

# CV2 & Scipy & Numpy & Pandas
import numpy as np

# Shapely
from shapely.geometry import *
from shapely.affinity import *

# Geopandas
from geopandas import GeoDataFrame

# Matplotlib
from matplotlib.path import Path

# etc
from collections.abc import Iterable
from functools import reduce

# Helper functions to fetch data from OSM

def ring_coding(ob):
    codes = np.ones(len(ob.coords), dtype = Path.code_type) * Path.LINETO
    codes[0] = Path.MOVETO
    return codes

def pathify(polygon):
    vertices = np.concatenate([np.asarray(polygon.exterior)] + [np.asarray(r) for r in polygon.interiors])
    codes = np.concatenate([ring_coding(polygon.exterior)] + [ring_coding(r) for r in polygon.interiors])
    return Path(vertices, codes)

def union(geometry):
    geometry = np.concatenate([[x] if type(x) == Polygon else x for x in geometry if type(x) in [Polygon, MultiPolygon]])
    geometry = reduce(lambda x, y: x.union(y), geometry[1:], geometry[0])
    return geometry

def get_perimeter(query, by_osmid = False):
    return ox.geocode_to_gdf(query, by_osmid = by_osmid)

def get_footprints(perimeter = None, point = None, radius = None, footprint = 'building'):

    if perimeter is not None:
        # Boundary defined by polygon (perimeter)
        footprints = ox.geometries_from_polygon(union(perimeter.geometry), tags = {footprint: True} if type(footprint) == str else footprint)
        perimeter = union(ox.project_gdf(perimeter).geometry)
        
    elif (point is not None) and (radius is not None):
        # Boundary defined by circle with radius 'radius' around point
        footprints = ox.geometries_from_point(point, dist = radius, tags = {footprint: True} if type(footprint) == str else footprint)
        perimeter = GeoDataFrame(geometry=[Point(point[::-1])], crs = footprints.crs)
        perimeter = ox.project_gdf(perimeter).geometry[0].buffer(radius)

    if len(footprints) > 0:
        footprints = ox.project_gdf(footprints)

    footprints = [
        [x] if type(x) == Polygon else x
        for x in footprints.geometry if type(x) in [Polygon, MultiPolygon]
    ]
    footprints = list(np.concatenate(footprints)) if len(footprints) > 0 else []
    footprints = [pathify(x) for x in footprints if x.within(perimeter)]

    return footprints, perimeter

def get_streets(perimeter = None, point = None, radius = None, dilate = 6, custom_filter = None):

    if perimeter is not None:
        # Boundary defined by polygon (perimeter)
        streets = ox.graph_from_polygon(union(perimeter.geometry), custom_filter = custom_filter)
        streets = ox.project_graph(streets)
        streets = ox.graph_to_gdfs(streets, nodes = False)
        #streets = ox.project_gdf(streets)
        streets = MultiLineString(list(streets.geometry)).buffer(dilate)

    elif (point is not None) and (radius is not None):
        # Boundary defined by polygon (perimeter)

        streets = ox.graph_from_point(point, dist = radius, custom_filter = custom_filter)
        crs = ox.graph_to_gdfs(streets, nodes = False).crs
        streets = ox.project_graph(streets)

        perimeter = GeoDataFrame(geometry=[Point(point[::-1])], crs = crs)
        perimeter = ox.project_gdf(perimeter).geometry[0].buffer(radius)

        streets = ox.graph_to_gdfs(streets, nodes = False)

        streets = MultiLineString(list(
            filter(
                # Filter lines with at least 2 points
                lambda line: len(line) >= 2,
                # Iterate over lines in geometry
                map(
                    # Filter points within perimeter
                    lambda line: list(filter(lambda xy: Point(xy).within(perimeter), zip(*line.xy))),
                    streets.geometry
                )
            )
        )).buffer(dilate) # Dilate lines

    if not isinstance(streets, Iterable):
        streets = [streets]
    
    streets = list(map(pathify, streets))

    return streets, perimeter