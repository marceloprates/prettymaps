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
        )
    elif args.command == "list-presets":
        for name in _presets()["preset"]:
            print(name)


if __name__ == "__main__":
    main()
