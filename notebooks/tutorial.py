import marimo

__generated_with = "0.23.15"
app = marimo.App()


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # prettymaps

    A minimal Python library to draw customized maps from [OpenStreetMap](https://www.openstreetmap.org/#map=12/11.0733/106.3078) created using the [osmnx](https://github.com/gboeing/osmnx), [matplotlib](https://matplotlib.org/), [shapely](https://shapely.readthedocs.io/en/stable/index.html) and [vsketch](https://github.com/abey79/vsketch) packages.

    ![](https://github.com/marceloprates/prettymaps/raw/main/pictures/heerhugowaard.png)

    # [![Docs](https://img.shields.io/badge/docs-GitHub%20Pages-blue?logo=github)](https://marceloprates.github.io/prettymaps/) [![PyPI](https://img.shields.io/badge/pypi-v1.4.2-blue)](https://pypi.org/project/prettymaps) [![Python](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/) [![License](https://img.shields.io/badge/license-AGPL%20v3.0-green)](LICENSE)

    This work is [licensed](LICENSE) under a GNU Affero General Public License v3.0 (you can make commercial use, distribute and modify this project, but must **disclose** the source code with the license and copyright notice)

    ## Note about crediting and NFTs:
    - Please keep the printed message on the figures crediting my repository and OpenStreetMap ([mandatory by their license](https://www.openstreetmap.org/copyright)).
    - I am personally **against** NFTs for their [environmental impact](https://earth.org/nfts-environmental-impact/), the fact that they're a [giant money-laundering pyramid scheme](https://twitter.com/smdiehl/status/1445795667826208770) and the structural incentives they create for [theft](https://twitter.com/NFTtheft) in the open source and generative art communities.
    - **I do not authorize in any way this project to be used for selling NFTs**, although I cannot legally enforce it. **Respect the creator**.
    - The [AeternaCivitas](https://magiceden.io/marketplace/aeterna_civitas) and [geoartnft](https://www.geo-nft.com/) projects have used this work to sell NFTs and refused to credit it. See how they reacted after being exposed: [AeternaCivitas](https://github.com/marceloprates/prettymaps/raw/main/pictures/NFT_theft_AeternaCivitas.jpg), [geoartnft](https://github.com/marceloprates/prettymaps/raw/main/pictures/NFT_theft_geoart.jpg).
    - **I have closed my other generative art projects on Github and won't be sharing new ones as open source to protect me from the NFT community**.

    <a href='https://ko-fi.com/marceloprates_' target='_blank'><img height='36' style='border:0px;height:36px;' src='https://cdn.ko-fi.com/cdn/kofi1.png?v=3' border='0' alt='Buy Me a Coffee at ko-fi.com' /></a>

    ## As seen on [Hacker News](https://web.archive.org/web/20210825160918/https://news.ycombinator.com/news):
    ![](https://github.com/marceloprates/prettymaps/raw/main/pictures/hackernews-prettymaps.png)
    ## [prettymaps subreddit](https://www.reddit.com/r/prettymaps_/)
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Installation

    ## Install locally:

    Install prettymaps with:

    ```
    pip install prettymaps
    ```

    ## Install on Google Colaboratory:

    Install prettymaps with:

    ```
    !pip install -e "git+https://github.com/marceloprates/prettymaps#egg=prettymaps"
    ```

    Then **restart the runtime** (Runtime -> Restart Runtime) before importing prettymaps.

    # Run front-end

    After prettymaps is installed, you can run the front-end (streamlit) application from the prettymaps repository using:

    ```
    streamlit run app.py
    ```
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Tutorial

    Plotting with prettymaps is very simple. Run:

    ```python
    prettymaps.plot(your_query)
    ```

    **your_query** can be:
    1. An address (Example: "Porto Alegre"),
    2. Latitude / Longitude coordinates (Example: (-30.0324999, -51.2303767))
    3. A custom boundary in GeoDataFrame format
    """)
    return


@app.cell
def _():
    import prettymaps

    plot_default = prettymaps.plot(
        'Stad van de Zon, Heerhugowaard, Netherlands'
    )
    return (prettymaps,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    You can also choose from different "presets" (parameter combinations saved in JSON files).

    See below an example using the "minimal" preset:
    """)
    return


@app.cell
def _(prettymaps):
    plot_minimal = prettymaps.plot(
        'Stad van de Zon, Heerhugowaard, Netherlands',
        preset='minimal',
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Run

    ```python
    prettymaps.presets()
    ```

    to list all available presets.
    """)
    return


@app.cell
def _(prettymaps):
    prettymaps.presets()
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    To examine a specific preset, run:
    """)
    return


@app.cell
def _(prettymaps):
    prettymaps.preset('default')
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Instead of using the default configuration you can customize several parameters. The most important are:

    - **layers**: A dictionary of OpenStreetMap layers to fetch.
      - Keys: layer names (arbitrary)
      - Values: dicts representing OpenStreetMap queries
    - **style**: Matplotlib style parameters
      - Keys: layer names (the same as before)
      - Values: dicts representing Matplotlib style parameters

    ```python
    plot = prettymaps.plot(
        # Your query. Example: "Porto Alegre" or (-30.0324999, -51.2303767) (GPS coords)
        your_query,
        # Dict of OpenStreetMap Layers to plot. Example:
        # {'building': {'tags': {'building': True}}, 'water': {'tags': {'natural': 'water'}}}
        # Check the /presets folder for more examples
        layers,
        # Dict of style parameters for matplotlib. Example:
        # {'building': {'palette': ['#f00','#0f0','#00f'], 'edge_color': '#333'}}
        style,
        # Preset to load. Options include:
        # ['default', 'minimal', 'macao', 'tijuca']
        preset,
        # Save current parameters to a preset file.
        # Example: "my-preset" will save to "presets/my-preset.json"
        save_preset,
        # Whether to update loaded preset with additional provided parameters. Boolean
        update_preset,
        # Plot with circular boundary. Boolean
        circle,
        # Plot area radius. Float
        radius,
        # Dilate the boundary by this amount. Float
        dilate
    )
    ```

    **plot** is a Python dataclass containing:

    ```python
    @dataclass
    class Plot:
        # A dictionary of GeoDataFrames (one for each plot layer)
        geodataframes: Dict[str, gp.GeoDataFrame]
        # A matplotlib figure
        fig: matplotlib.figure.Figure
        # A matplotlib axis object
        ax: matplotlib.axes.Axes
    ```

    Here's an example of running `prettymaps.plot()` with customized parameters:
    """)
    return


@app.cell
def _(prettymaps):
    plot_macau = prettymaps.plot(
        'Praça Ferreira do Amaral, Macau',
        circle=True,
        radius=1100,
        layers={
            "green": {
                "tags": {
                    "landuse": "grass",
                    "natural": ["island", "wood"],
                    "leisure": "park",
                }
            },
            "forest": {"tags": {"landuse": "forest"}},
            "water": {"tags": {"natural": ["water", "bay"]}},
            "parking": {
                "tags": {
                    "amenity": "parking",
                    "highway": "pedestrian",
                    "man_made": "pier",
                }
            },
            "streets": {
                "width": {
                    "motorway": 5,
                    "trunk": 5,
                    "primary": 4.5,
                    "secondary": 4,
                    "tertiary": 3.5,
                    "residential": 3,
                }
            },
            "building": {"tags": {"building": True}},
        },
        style={
            "background": {"fc": "#F2F4CB", "ec": "#dadbc1", "hatch": "ooo..."},
            "perimeter": {"fc": "#F2F4CB", "ec": "#dadbc1", "lw": 0, "hatch": "ooo..."},
            "green": {"fc": "#D0F1BF", "ec": "#2F3737", "lw": 1},
            "forest": {"fc": "#64B96A", "ec": "#2F3737", "lw": 1},
            "water": {
                "fc": "#a1e3ff",
                "ec": "#2F3737",
                "hatch": "ooo...",
                "hatch_c": "#85c9e6",
                "lw": 1,
            },
            "parking": {"fc": "#F2F4CB", "ec": "#2F3737", "lw": 1},
            "streets": {"fc": "#2F3737", "ec": "#475657", "alpha": 1, "lw": 0},
            "building": {
                "palette": ["#FFC857", "#E9724C", "#C5283D"],
                "ec": "#2F3737",
                "lw": 0.5,
            },
        },
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    In order to plot an entire region and not just a rectangular or circular area, set

    ```python
    radius = False
    ```
    """)
    return


@app.cell
def _(prettymaps):
    plot_bomfim = prettymaps.plot(
        'Bom Fim, Porto Alegre, Brasil', radius=False
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    You can access layer's GeoDataFrames directly like this:
    """)
    return


@app.cell
def _(prettymaps):
    plot_centro = prettymaps.plot(
        'Centro Histórico, Porto Alegre', show=False
    )
    plot_centro.geodataframes['building']
    return (plot_centro,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Search a building by name and display it:
    """)
    return


@app.cell
def _(plot_centro):
    plot_centro.geodataframes['building'][
        plot_centro.geodataframes['building'].name
        == 'Catedral Metropolitana Nossa Senhora Mãe de Deus'
    ].geometry[0]
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Plot mosaic of building footprints:
    """)
    return


@app.cell
def _(prettymaps):
    import numpy as np
    import osmnx as ox
    from matplotlib import pyplot as plt

    plot_poa = prettymaps.plot('Porto Alegre', show=False)
    buildings = plot_poa.geodataframes['building']
    buildings = ox.projection.project_gdf(buildings)
    buildings = [b for b in buildings.geometry if b.area > 0]

    n = 6
    fig, axes = plt.subplots(n, n, figsize=(7, 6))
    fig.patch.set_facecolor('#5cc0eb')
    fig.suptitle('Buildings of Porto Alegre', size=25, color='#fff')
    for ax, building in zip(np.concatenate(axes), buildings):
        ax.plot(*building.exterior.xy, c='#ffffff')
        ax.autoscale()
        ax.axis('off')
        ax.axis('equal')
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Access `plot.ax` or `plot.fig` to add new elements to the matplotlib plot:
    """)
    return


@app.cell
def _(prettymaps):
    plot_bcn = prettymaps.plot(
        (41.39491, 2.17557),
        preset='barcelona',
        show=False,
    )

    plot_bcn.fig.patch.set_facecolor('#F2F4CB')
    _ = plot_bcn.ax.set_title('Barcelona', font='serif', size=50)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Use **plotter** mode to export a pen plotter-compatible SVG (thanks to abey79's amazing [vsketch](https://github.com/abey79/vsketch) library):
    """)
    return


@app.cell
def _(prettymaps):
    plot_bcn_plotter = prettymaps.plot(
        (41.39491, 2.17557),
        mode='plotter',
        layers=dict(perimeter={}),
        preset='barcelona-plotter',
        scale_x=0.6,
        scale_y=-0.6,
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Some other examples:
    """)
    return


@app.cell
def _(prettymaps):
    plot_tijuca = prettymaps.plot(
        'Barra da Tijuca',
        dilate=0,
        figsize=(22, 10),
        preset='tijuca',
        adjust_aspect_ratio=False,
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Use `prettymaps.create_preset()` to create a preset:
    """)
    return


@app.cell
def _(prettymaps):
    prettymaps.create_preset(
        "my-preset",
        layers={
            "building": {
                "tags": {
                    "building": True,
                    "leisure": ["track", "pitch"],
                }
            },
            "streets": {
                "width": {
                    "trunk": 6,
                    "primary": 6,
                    "secondary": 5,
                    "tertiary": 4,
                    "residential": 3.5,
                    "pedestrian": 3,
                    "footway": 3,
                    "path": 3,
                }
            },
        },
        style={
            "perimeter": {"fill": False, "lw": 0, "zorder": 0},
            "streets": {"fc": "#F1E6D0", "ec": "#2F3737", "lw": 1.5, "zorder": 3},
            "building": {
                "palette": ["#fff"],
                "ec": "#2F3737",
                "lw": 1,
                "zorder": 4,
            },
        },
    )

    prettymaps.preset('my-preset')
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Use **prettymaps.multiplot** and **prettymaps.Subplot** to draw multiple regions on the same canvas:
    """)
    return


@app.cell
def _(prettymaps):
    multiplot_pa = prettymaps.multiplot(
        prettymaps.Subplot(
            'Cidade Baixa, Porto Alegre',
            style={'building': {'palette': ['#49392C', '#E1F2FE', '#98D2EB']}},
        ),
        prettymaps.Subplot(
            'Bom Fim, Porto Alegre',
            style={'building': {'palette': ['#BA2D0B', '#D5F2E3', '#73BA9B', '#F79D5C']}},
        ),
        prettymaps.Subplot(
            'Farroupilha, Porto Alegre',
            layers={'building': {'tags': {'building': True}}},
            style={'building': {'palette': ['#EEE4E1', '#E7D8C9', '#E6BEAE']}},
        ),
        preset='cb-bf-f',
        figsize=(12, 12),
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Add hillshade
    """)
    return


@app.cell
def _(prettymaps):
    plot_honolulu = prettymaps.plot(
        'Honolulu',
        radius=5500,
        figsize='a4',
        layers={
            'hillshade': {
                'azdeg': 315,
                'altdeg': 45,
                'vert_exag': 1,
                'dx': 1,
                'dy': 1,
                'alpha': 0.75,
            },
        },
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Add keypoints
    """)
    return


@app.cell
def _(prettymaps):
    plot_garopaba = prettymaps.plot(
        'Garopaba',
        radius=5000,
        figsize='a4',
        layers={'building': False},
        keypoints={
            'tags': {'natural': ['beach']},
            'specific': {
                'pedra branca': {'tags': {'natural': ['peak']}},
            },
        },
    )
    return


if __name__ == "__main__":
    app.run()
