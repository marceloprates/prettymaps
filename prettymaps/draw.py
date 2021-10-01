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

import re
from collections.abc import Iterable

import osmnx as ox
import pandas as pd
from geopandas import GeoDataFrame
import numpy as np
from numpy.random import choice
from shapely.geometry import box, Polygon, MultiLineString, GeometryCollection
from shapely.affinity import translate, scale, rotate
from descartes import PolygonPatch
from tabulate import tabulate

from .fetch import get_perimeter, get_layer


# Plot a single shape
def plot_shape(shape, ax, vsketch=None, **kwargs):
    """
    Plot shapely object
    """
    if isinstance(shape, Iterable) and type(shape) != MultiLineString:
        for shape_ in shape:
            plot_shape(shape_, ax, vsketch=vsketch, **kwargs)
    else:
        if not shape.is_empty:

            if vsketch is None:
                ax.add_patch(PolygonPatch(shape, **kwargs))
            else:
                if ("draw" not in kwargs) or kwargs["draw"]:

                    if "stroke" in kwargs:
                        vsketch.stroke(kwargs["stroke"])
                    else:
                        vsketch.stroke(1)

                    if "penWidth" in kwargs:
                        vsketch.penWidth(kwargs["penWidth"])
                    else:
                        vsketch.penWidth(0.3)

                    if "fill" in kwargs:
                        vsketch.fill(kwargs["fill"])
                    else:
                        vsketch.noFill()

                    vsketch.geometry(shape)


# Plot a collection of shapes
def plot_shapes(shapes, ax, vsketch=None, palette=None, **kwargs):
    """
    Plot collection of shapely objects (optionally, use a color palette)
    """
    if not isinstance(shapes, Iterable):
        shapes = [shapes]

    for shape in shapes:
        if palette is None:
            plot_shape(shape, ax, vsketch=vsketch, **kwargs)
        else:
            plot_shape(shape, ax, vsketch=vsketch, fc=choice(palette), **kwargs)


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


# Apply transformation (translation & scale) to layers
def transform(layers, x, y, scale_x, scale_y, rotation):
    # Transform layers (translate & scale)
    k, v = zip(*layers.items())
    v = GeometryCollection(v)
    if (x is not None) and (y is not None):
        v = translate(v, *(np.array([x, y]) - np.concatenate(v.centroid.xy)))
    if scale_x is not None:
        v = scale(v, scale_x, 1)
    if scale_y is not None:
        v = scale(v, 1, scale_y)
    if rotation is not None:
        v = rotate(v, rotation)
    layers = dict(zip(k, v))
    return layers


def draw_text(ax, text, x, y, **kwargs):
    if 'bbox' in kwargs:
        bbox_kwargs = kwargs.pop('bbox')
        text = ax.text(x, y, text, **kwargs)
        text.set_bbox(**bbox_kwargs)
    else:
        text = ax.text(x, y, text, **kwargs)


# Plot
def plot(
    # Address
    query,
    # Whether to use a backup for the layers
    backup=None,
    # Custom postprocessing function on layers
    postprocessing=None,
    # Radius (in case of circular plot)
    radius=None,
    # Which layers to plot
    layers={"perimeter": {}},
    # Drawing params for each layer (matplotlib params such as 'fc', 'ec', 'fill', etc.)
    drawing_kwargs={},
    # OSM Caption parameters
    osm_credit={},
    # Figure parameters
    figsize=(10, 10),
    ax=None,
    title=None,
    # Vsketch parameters
    vsketch=None,
    # Transform (translation & scale) params
    x=None,
    y=None,
    scale_x=None,
    scale_y=None,
    rotation=None,
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
    drawing_kwargs: dict
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

    # Interpret query
    query_mode = parse_query(query)

    # Save maximum dilation for later use
    dilations = [kwargs["dilate"] for kwargs in layers.values() if "dilate" in kwargs]
    max_dilation = max(dilations) if len(dilations) > 0 else 0

    ####################
    ### Fetch Layers ###
    ####################

    # Use backup if provided
    if backup is not None:
        layers = backup
    # Otherwise, fetch layers
    else:
        # Define base kwargs
        if radius:
            base_kwargs = {
                "point": query if query_mode == "coordinates" else ox.geocode(query),
                "radius": radius,
            }
        else:
            base_kwargs = {
                "perimeter": query
                if query_mode == "polygon"
                else get_perimeter(query, by_osmid=query_mode == "osmid")
            }

        # Fetch layers
        layers = {
            layer: get_layer(
                layer, **base_kwargs, **(kwargs if type(kwargs) == dict else {})
            )
            for layer, kwargs in layers.items()
        }

        # Apply transformation to layers (translate & scale)
        layers = transform(layers, x, y, scale_x, scale_y, rotation)

        # Apply postprocessing step to layers
        if postprocessing is not None:
            layers = postprocessing(layers)

    ############
    ### Plot ###
    ############

    # Matplot-specific stuff (only run if vsketch mode isn't activated)
    if vsketch is None:
        # Ajust axis
        ax.axis("off")
        ax.axis("equal")
        ax.autoscale()

    # Plot background
    if "background" in drawing_kwargs:
        geom = scale(box(*layers["perimeter"].bounds), 1.2, 1.2)

        if vsketch is None:
            ax.add_patch(PolygonPatch(geom, **drawing_kwargs["background"]))
        else:
            vsketch.geometry(geom)

    # Adjust bounds
    xmin, ymin, xmax, ymax = layers["perimeter"].buffer(max_dilation).bounds
    dx, dy = xmax - xmin, ymax - ymin
    if vsketch is None:
        ax.set_xlim(xmin, xmax)
        ax.set_ylim(ymin, ymax)

    # Draw layers
    for layer, shapes in layers.items():
        kwargs = drawing_kwargs[layer] if layer in drawing_kwargs else {}
        if "hatch_c" in kwargs:
            # Draw hatched shape
            plot_shapes(
                shapes,
                ax,
                vsketch=vsketch,
                lw=0,
                ec=kwargs["hatch_c"],
                **{k: v for k, v in kwargs.items() if k not in ["lw", "ec", "hatch_c"]},
            )
            # Draw shape contour only
            plot_shapes(
                shapes,
                ax,
                vsketch=vsketch,
                fill=False,
                **{
                    k: v
                    for k, v in kwargs.items()
                    if k not in ["hatch_c", "hatch", "fill"]
                },
            )
        else:
            # Draw shape normally
            plot_shapes(shapes, ax, vsketch=vsketch, **kwargs)

    if ((isinstance(osm_credit, dict)) or (osm_credit is True)) and (vsketch is None):
        x, y = figsize
        d = 0.8 * (x ** 2 + y ** 2) ** 0.5
        draw_text(
            ax,
            (
                osm_credit["text"]
                if "text" in osm_credit
                else "data © OpenStreetMap contributors\ngithub.com/marceloprates/prettymaps"
            ),
            x=xmin + (osm_credit["x"] * dx if "x" in osm_credit else 0),
            y=ymax - 4 * d - (osm_credit["y"] * dy if "y" in osm_credit else 0),
            fontfamily=(
                osm_credit["fontfamily"]
                if "fontfamily" in osm_credit
                else "Ubuntu Mono"
            ),
            fontsize=(osm_credit["fontsize"] * d if "fontsize" in osm_credit else d),
            zorder=(
                osm_credit["zorder"] if "zorder" in osm_credit else len(layers) + 1
            ),
            **{
                k: v
                for k, v in osm_credit.items()
                if k not in ["text", "x", "y", "fontfamily", "fontsize", "zorder"]
            },
        )

    # Return perimeter
    return layers
