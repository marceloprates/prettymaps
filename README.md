# prettymaps

A minimal Python library to draw customized maps from [OpenStreetMap](https://www.openstreetmap.org/#map=12/11.0733/106.3078) created using the [osmnx](https://github.com/gboeing/osmnx), [matplotlib](https://matplotlib.org/), [shapely](https://shapely.readthedocs.io/en/stable/index.html) and [vsketch](https://github.com/abey79/vsketch) libraries.

[![CC BY NC 4.0][cc-by-nc-shield]][cc-by-nc]

This work is [licensed](LICENSE) under a
[Creative Commons Attribution-NonCommercial 4.0 International][cc-by-nc].

[![CC BY 4.0][cc-by-image]][cc-by-nc]

[cc-by-nc]: http://creativecommons.org/licenses/by-nc/4.0/
[cc-by-image]: https://i.creativecommons.org/l/by-nc/4.0/88x31.png
[cc-by-nc-shield]: https://img.shields.io/badge/license-CC%20BY%20NC%204.0-lightgrey.svg

- **Because of the recent episodes of plagiarism and refusal to credit this project in the NFT Community (Twitter profiles [AeternaCivitas](https://twitter.com/AeternaCivitas) and [geoartnft](twitter.com/geoartnft)) I have decided to change my license to Creative Commons (CC-BY-NC-4.0) which requires you to credit it everytime you use it and forbids you to use if for commercial purposes.**
- **The printed message on the figures crediting OpenStreetMap and my repository, included by default, is mandatory.**
- **I do not authorize people to sell NFTs using prettymaps and ask that you contact me if you know of someone who is doing it.**
- **CREDIT OPEN SOURCE DEVELOPERS!**

<a href='https://ko-fi.com/marceloprates_' target='_blank'><img height='36' style='border:0px;height:36px;' src='https://cdn.ko-fi.com/cdn/kofi1.png?v=3' border='0' alt='Buy Me a Coffee at ko-fi.com' /></a>

## As seen on [Hacker News](https://web.archive.org/web/20210825160918/https://news.ycombinator.com/news):
![](prints/hackernews-prettymaps.png)

## Read the [docs](https://prettymaps.readthedocs.io/en/latest/prettymaps.html#module-prettymaps)

## [prettymaps subreddit](https://www.reddit.com/r/prettymaps_/)
## [Google Colaboratory Demo](https://colab.research.google.com/github/marceloprates/prettymaps/blob/master/notebooks/examples.ipynb)

## Installation

Install with

```
$ pip install prettymaps
```

## Usage example (For more examples, see [this Jupyter Notebook](https://nbviewer.jupyter.org/github/marceloprates/prettymaps/blob/main/notebooks/examples.ipynb)):

```python
# Init matplotlib figure
fig, ax = plt.subplots(figsize = (12, 12), constrained_layout = True)

backup = plot(
    # Address:
    'Praça Ferreira do Amaral, Macau',
    # Plot geometries in a circle of radius:
    radius = 1100,
    # Matplotlib axis
    ax = ax,
    # Which OpenStreetMap layers to plot and their parameters:
    layers = {
            # Perimeter (in this case, a circle)
            'perimeter': {},
            # Streets and their widths
            'streets': {
                'width': {
                    'motorway': 5,
                    'trunk': 5,
                    'primary': 4.5,
                    'secondary': 4,
                    'tertiary': 3.5,
                    'residential': 3,
                    'service': 2,
                    'unclassified': 2,
                    'pedestrian': 2,
                    'footway': 1,
                }
            },
            # Other layers:
            #   Specify a name (for example, 'building') and which OpenStreetMap tags to fetch
            'building': {'tags': {'building': True, 'landuse': 'construction'}, 'union': False},
            'water': {'tags': {'natural': ['water', 'bay']}},
            'green': {'tags': {'landuse': 'grass', 'natural': ['island', 'wood'], 'leisure': 'park'}},
            'forest': {'tags': {'landuse': 'forest'}},
            'parking': {'tags': {'amenity': 'parking', 'highway': 'pedestrian', 'man_made': 'pier'}}
        },
        # drawing_kwargs:
        #   Reference a name previously defined in the 'layers' argument and specify matplotlib parameters to draw it
        drawing_kwargs = {
            'background': {'fc': '#F2F4CB', 'ec': '#dadbc1', 'hatch': 'ooo...', 'zorder': -1},
            'perimeter': {'fc': '#F2F4CB', 'ec': '#dadbc1', 'lw': 0, 'hatch': 'ooo...',  'zorder': 0},
            'green': {'fc': '#D0F1BF', 'ec': '#2F3737', 'lw': 1, 'zorder': 1},
            'forest': {'fc': '#64B96A', 'ec': '#2F3737', 'lw': 1, 'zorder': 1},
            'water': {'fc': '#a1e3ff', 'ec': '#2F3737', 'hatch': 'ooo...', 'hatch_c': '#85c9e6', 'lw': 1, 'zorder': 2},
            'parking': {'fc': '#F2F4CB', 'ec': '#2F3737', 'lw': 1, 'zorder': 3},
            'streets': {'fc': '#2F3737', 'ec': '#475657', 'alpha': 1, 'lw': 0, 'zorder': 3},
            'building': {'palette': ['#FFC857', '#E9724C', '#C5283D'], 'ec': '#2F3737', 'lw': .5, 'zorder': 4},
        }
)
```

![](prints/macao.png)

## Gallery:

### Barcelona:
![](prints/barcelona.png)
### Heerhugowaard:
![](prints/heerhugowaard.png)
### Barra da Tijuca:
![](prints/tijuca.png)
### Porto Alegre:
![](prints/bomfim-farroupilha-cidadebaixa.png)
