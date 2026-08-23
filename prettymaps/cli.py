import argparse

from .draw import plot as _plot
from .draw import presets as _presets


def build_parser():
    parser = argparse.ArgumentParser(prog="prettymaps")
    subparsers = parser.add_subparsers(dest="command", required=True)

    plot_parser = subparsers.add_parser("plot", help="Draw a map for a query")
    plot_parser.add_argument("query", help="Place name, coordinates, or address")
    plot_parser.add_argument(
        "--preset", default="default", help="Preset name (see list-presets)"
    )
    plot_parser.add_argument(
        "-o", "--output", required=True, help="Output file path (e.g. map.png)"
    )
    plot_parser.add_argument(
        "--width", type=float, default=11.7, help="Figure width in inches"
    )
    plot_parser.add_argument(
        "--height", type=float, default=11.7, help="Figure height in inches"
    )
    plot_parser.add_argument(
        "--no-credit",
        action="store_true",
        help="Omit the OpenStreetMap/prettymaps credit box from the image",
    )
    plot_parser.add_argument(
        "--radius",
        type=float,
        default=None,
        help="Radius in meters around the query point, instead of the OSM boundary",
    )
    plot_parser.add_argument(
        "--circle",
        action="store_true",
        default=None,
        help="With --radius, use a circular boundary instead of a square one",
    )
    plot_parser.add_argument(
        "--dilate",
        type=float,
        default=None,
        help="Expand (or shrink, if negative) the boundary by this many meters",
    )

    subparsers.add_parser("list-presets", help="List available preset names")

    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)

    if args.command == "plot":
        _plot(
            args.query,
            preset=args.preset,
            save_as=args.output,
            figsize=(args.width, args.height),
            credit=False if args.no_credit else {},
            radius=args.radius,
            circle=args.circle,
            dilate=args.dilate,
        )
    elif args.command == "list-presets":
        for name in _presets()["preset"]:
            print(name)


if __name__ == "__main__":
    main()
