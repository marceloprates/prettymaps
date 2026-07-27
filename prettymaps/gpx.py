"""
Read GPS tracks (GPX / KML) into shapely geometries.

Used by :func:`prettymaps.draw.plot` to (a) frame a map around a recorded track
and (b) draw the track as a map layer. See GitHub issue #64.

The parser is intentionally dependency-free (standard-library XML only) and
namespace-agnostic, so it accepts GPX 1.0/1.1 and KML files regardless of the
declared XML namespace.
"""

import math
import xml.etree.ElementTree as ET
from typing import List, Optional, Tuple, Union

from shapely.geometry import LineString, MultiLineString
from shapely.geometry.base import BaseGeometry

# Mean metres-per-degree of latitude (WGS84). Longitude is scaled by cos(lat).
_M_PER_DEG = 111_320.0

__all__ = ["read_track", "is_track_file", "track_center", "track_radius"]


def _localname(tag: str) -> str:
    """Return an element's tag without its XML namespace, lower-cased."""
    return tag.rsplit("}", 1)[-1].lower()


def _lines_from_gpx(root: ET.Element) -> List[LineString]:
    """Extract track segments (trk/trkseg) and routes (rte) as LineStrings."""
    lines = []
    for element in root.iter():
        if _localname(element.tag) in ("trkseg", "rte"):
            points = []
            for point in element:
                if _localname(point.tag) in ("trkpt", "rtept"):
                    try:
                        points.append((float(point.get("lon")), float(point.get("lat"))))
                    except (TypeError, ValueError):
                        continue
            if len(points) >= 2:
                lines.append(LineString(points))
    return lines


def _lines_from_kml(root: ET.Element) -> List[LineString]:
    """Extract <LineString><coordinates> paths ("lon,lat,alt lon,lat,alt ...")."""
    lines = []
    for element in root.iter():
        if _localname(element.tag) != "linestring":
            continue
        for child in element:
            if _localname(child.tag) != "coordinates":
                continue
            points = []
            for token in (child.text or "").split():
                parts = token.split(",")
                if len(parts) >= 2:
                    try:
                        points.append((float(parts[0]), float(parts[1])))
                    except ValueError:
                        continue
            if len(points) >= 2:
                lines.append(LineString(points))
    return lines


def read_track(
    source: Union[str, List[str], Tuple[str, ...]]
) -> Optional[MultiLineString]:
    """
    Read one or more GPX/KML files into a single shapely ``MultiLineString``.

    Coordinates are longitude/latitude (EPSG:4326), matching osmnx/prettymaps.

    Args:
        source: A path to a ``.gpx`` or ``.kml`` file, or a list of such paths.

    Returns:
        A ``MultiLineString`` of every track segment / route / line found, or
        ``None`` if the file(s) contain no usable line geometry.
    """
    if isinstance(source, (list, tuple)):
        geoms: List[LineString] = []
        for item in source:
            track = read_track(item)
            if track is not None:
                geoms.extend(track.geoms)
        return MultiLineString(geoms) if geoms else None

    root = ET.parse(source).getroot()
    root_name = _localname(root.tag)
    if root_name == "kml":
        lines = _lines_from_kml(root)
    elif root_name == "gpx":
        lines = _lines_from_gpx(root)
    else:
        # Unknown root: try both readers.
        lines = _lines_from_gpx(root) or _lines_from_kml(root)

    return MultiLineString(lines) if lines else None


def is_track_file(query: object) -> bool:
    """True if ``query`` is a path to a ``.gpx`` or ``.kml`` file."""
    return isinstance(query, str) and query.lower().rsplit(".", 1)[-1] in ("gpx", "kml")


def track_center(geom: BaseGeometry) -> Tuple[float, float]:
    """Return the ``(latitude, longitude)`` centre of a track's bounding box."""
    min_lon, min_lat, max_lon, max_lat = geom.bounds
    return (min_lat + max_lat) / 2, (min_lon + max_lon) / 2


def track_radius(
    geom: BaseGeometry, margin: float = 1.15, min_radius: float = 250.0
) -> float:
    """
    A square "radius" (half-side, in metres) that encloses the whole track.

    Args:
        geom: Track geometry in lon/lat (EPSG:4326).
        margin: Multiplier applied so the track doesn't touch the map edge.
        min_radius: Floor for very short tracks, so the map isn't absurdly zoomed.
    """
    min_lon, min_lat, max_lon, max_lat = geom.bounds
    center_lat = (min_lat + max_lat) / 2
    width_m = (max_lon - min_lon) * _M_PER_DEG * math.cos(math.radians(center_lat))
    height_m = (max_lat - min_lat) * _M_PER_DEG
    return max(min_radius, (max(width_m, height_m) / 2) * margin)
