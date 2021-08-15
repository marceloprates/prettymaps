# OpenStreetMap Networkx library to download data from OpenStretMap
#from sympy import geometry
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
from IPython.display import Markdown, display
from collections.abc import Iterable

# Fetch
from fetch import *

# Helper functions
def get_hash(key):
    return frozenset(key.items()) if type(key) == dict else key

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
    #if type(shape) == Path:
    #    return patches.PathPatch(shape, **kwargs)
    if type(shape) == Polygon and shape.area > 0:
        return PolygonPatch(list(zip(*shape.exterior.xy)), **kwargs)
    else:
        return None

def plot_shape(shape, ax, vsketch = None, **kwargs):
    '''
    Plot shapely object
    '''
    if isinstance(shape, Iterable) and type(shape) != MultiLineString:
        for shape_ in shape:
            plot_shape(shape_, ax, vsketch = vsketch, **kwargs)
    else:
        if not shape.is_empty:
            if vsketch is None:
                ax.add_patch(PolygonPatch(shape, **kwargs))
            else:
                if ('draw' not in kwargs) or kwargs['draw']:
                    
                    if ('pen' in kwargs):
                        vsketch.stroke(kwargs['pen'])
                    else:
                        vsketch.stroke(1)

                    vsketch.geometry(shape)

def plot_shapes(shapes, ax, vsketch = None, palette = None, **kwargs):
    '''
    Plot collection of shapely objects (optionally, use a color palette)
    '''
    if not isinstance(shapes, Iterable):
        shapes = [shapes]

    for shape in shapes:
        if palette is None:
            plot_shape(shape, ax, vsketch = vsketch, **kwargs)
        else:
            plot_shape(shape, ax, vsketch = vsketch, fc = choice(palette), **kwargs)

def plot(
    # Address
    query,
    # Whether to use a backup for the layers
    backup = None,
    # Radius (in case of circular plot)
    radius = None,
    # Which layers to plot
    layers = {'perimeter': {}},
    # Drawing params for each layer (matplotlib params such as 'fc', 'ec', 'fill', etc.)
    drawing_kwargs = {},
    # Figure parameters
    figsize = (10, 10), ax = None, title = None,
    # Vsketch parameters
    vsketch = None,
    # Transform (translation & scale) params
    x = None, y = None, sf = None, rotation = None,
    ):

    # Interpret query
    if type(query) == tuple:
        query_mode = 'coordinates'
    elif False:
        query_mode = 'osmid'
    else:
        query_mode = 'address'

    # Save maximum dilation for later use
    dilations = [kwargs['dilate'] for kwargs in layers.values() if 'dilate' in kwargs]
    max_dilation = max(dilations) if len(dilations) > 0 else 0

    if backup is None:

        #############
        ### Fetch ###
        #############

        # Define base kwargs
        if radius:
            base_kwargs = {'point': query if type(query) == tuple else ox.geocode(query), 'radius': radius}
        else:
            by_osmid = False
            base_kwargs = {'perimeter': get_perimeter(query, by_osmid = by_osmid)}

        # Fetch layers
        layers = {
            layer: get_layer(
                layer,
                **base_kwargs,
                **(kwargs if type(kwargs) == dict else {})
            )
            for layer, kwargs in layers.items()
        }

        # Transform layers (translate & scale)
        k, v = zip(*layers.items())
        v = GeometryCollection(v)
        if (x is not None) and (y is not None):
            v = translate(v, *(np.array([x, y]) - np.concatenate(v.centroid.xy)))
        if sf is not None:
            v = scale(v, sf, sf)
        if rotation is not None:
            v = rotate(v, rotation)
        layers = dict(zip(k, v))

    else:
        layers = backup

    if vsketch is None:
        # Ajust axis
        ax.axis('off')
        ax.axis('equal')
        ax.autoscale()

    # Plot background
    if 'background' in drawing_kwargs:
        xmin, ymin, xmax, ymax = layers['perimeter'].bounds
        geom = scale(Polygon([
            (xmin, ymin),
            (xmin, ymax),
            (xmax, ymax),
            (xmax, ymin)
        ]), 2, 2)

        if vsketch is None:
            ax.add_patch(PolygonPatch(geom, **drawing_kwargs['background']))
        else:
            vsketch.geometry(geom)

    ############
    ### Plot ###
    ############
    
    # Adjust bounds
    xmin, ymin, xmax, ymax = layers['perimeter'].buffer(max_dilation).bounds
    if vsketch is None:
        ax.set_xlim(xmin, xmax)
        ax.set_ylim(ymin, ymax)

    # Draw layers
    for layer, shapes in layers.items():
        kwargs = drawing_kwargs[layer] if layer in drawing_kwargs else {}
        if 'hatch_c' in kwargs:
            plot_shapes(shapes, ax, vsketch = vsketch, lw = 0, ec = kwargs['hatch_c'], **{k:v for k,v in kwargs.items() if k not in ['lw', 'ec', 'hatch_c']})
            plot_shapes(shapes, ax, vsketch = vsketch, fill = False, **{k:v for k,v in kwargs.items() if k not in ['hatch_c', 'hatch', 'fill']})
        else:
            plot_shapes(shapes, ax, vsketch = vsketch, **kwargs)

    # Return perimeter
    return layers
