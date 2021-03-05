# OpenStreetMap Networkx library to download data from OpenStretMap
import osmnx as ox

# Matplotlib-related stuff, for drawing
from matplotlib.path import Path
from matplotlib import pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import PathPatch

# CV2 & Scipy & Numpy & Pandas
import numpy as np
from numpy.random import choice

# Shapely
from shapely.geometry import *
from shapely.affinity import *

# Geopandas
from geopandas import GeoDataFrame

# etc
import pandas as pd
from functools import reduce
from tabulate import tabulate
from IPython.display import Markdown
from collections.abc import Iterable

# Fetch
from fetch import *

# Drawing functions

def show_palette(palette, description = ''):
    '''
    Helper to display palette in Markdown
    '''

    colorboxes = [
        f'![](https://placehold.it/30x30/{c[1:]}/{c[1:]}?text=)'
        for c in palette
    ]
    
    display(Markdown((description)))
    display(Markdown(tabulate(pd.DataFrame(colorboxes), showindex = False)))

def get_patch(shape, **kwargs):
    '''
    Convert shapely object to matplotlib patch
    '''
    if type(shape) == Path:
        return patches.PathPatch(shape, **kwargs)
    elif type(shape) == Polygon and shape.area > 0:
        return patches.Polygon(list(zip(*shape.exterior.xy)), **kwargs)
    else:
        return None

def plot_shape(shape, ax, **kwargs):
    '''
    Plot shapely object
    '''
    if isinstance(shape, Iterable):
        for shape_ in shape:
            plot_shape(shape_, ax, **kwargs)
    else:
        ax.add_patch(get_patch(shape, **kwargs))

def plot_shapes(shapes, ax, palette = None, **kwargs):
    '''
    Plot collection of shapely objects (optionally, use a color palette)
    '''
    if not isinstance(shapes, Iterable):
        shapes = [shapes]

    for shape in shapes:
        if palette is None:
            plot_shape(shape, ax, **kwargs)
        else:
            plot_shape(shape, ax, fc = choice(palette), **kwargs)

def plot_streets(streets, ax, color = '#f5da9f', background_color = 'white', **kwargs):
    '''
    Plot shapely Polygon (or MultiPolygon) representing streets using matplotlib PathPatches
    '''
    for s in streets if isinstance(streets, Iterable) else [streets]:
        if s is not None:
            ax.add_patch(get_patch(pathify(s), facecolor = color, edgecolor = 'black', **kwargs))

def plot(
    # Address
    query,
    # Figure parameters
    figsize = (10, 10),
    ax = None,
    title = None,
    # Whether to plot a circle centered around the address; circle params
    circle = False,
    radius = 1000,
    streets_radius = 1000,
    # Street params
    dilate_streets = 5,
    draw_streets = True,
    # Color params
    background_color = 'white',
    background_alpha = 1.,
    palette = None,
    perimeter_lw = 1,
    perimeter_ec = 'black',
    water_ec = 'black',
    land_ec = 'black',
    buildings_ec = 'black',
    # Which layers to plot
    layers = ['perimeter', 'landuse', 'water', 'building', 'streets'],
    # Layer ordering params
    zorder_perimeter = None,
    zorder_landuse = None,
    zorder_water = None,
    zorder_streets = None,
    zorder_building = None,
    # Whether to fetch data using OSM Id
    by_osmid = False
    ):

    #############
    ### Fetch ###
    #############

    # Geocode central point
    if not by_osmid:
        point = ox.geocode(query)

    # Fetch perimeter
    perimeter = get_perimeter(query, by_osmid = by_osmid) if not circle else None

    # Fetch buildings, land, water, streets
    layers_dict = {}
    for layer in layers:
        if layer == 'perimeter':
            pass
        elif layer == 'streets':
            layers_dict[layer], _ = get_streets(
                **({'point': point, 'radius': streets_radius} if circle else {'perimeter': perimeter}),
                dilate = dilate_streets
            )
        else:
            layers_dict[layer], perimeter_ = get_footprints(
                **({'point': point, 'radius': radius} if circle else {'perimeter': perimeter}),
                footprint = layer
            )

    # Project perimeter
    if 'perimeter' in layers:
        layers_dict['perimeter'] = perimeter_ if circle else union(ox.project_gdf(perimeter).geometry)

    ############
    ### Plot ###
    ############

    if ax is None:
        # if ax is none, create figure
        fig, ax = plt.subplots(figsize = figsize)

    # Ajust axis
    ax.axis('off')
    ax.axis('equal')
    ax.autoscale()

    # Setup parameters for drawing layers
    layer_kwargs = {
        'perimeter': {'lw': perimeter_lw, 'ec': perimeter_ec, 'fc': background_color, 'alpha': background_alpha, 'zorder': zorder_perimeter},
        'landuse': {'ec': land_ec, 'fc': '#53bd53', 'zorder': zorder_landuse},
        'water': {'ec': water_ec, 'fc': '#a1e3ff', 'zorder': zorder_water},
        'streets': {'fc': '#f5da9f', 'zorder': zorder_streets},
        'building': {'ec': buildings_ec, 'palette': palette, 'zorder': zorder_building},
    }

    # Draw layers
    for layer in ['perimeter', 'landuse', 'water', 'streets', 'building']:
        if layer in layers_dict:
            plot_shapes(layers_dict[layer], ax, **layer_kwargs[layer])

    # Return perimeter
    return layers_dict['perimeter']