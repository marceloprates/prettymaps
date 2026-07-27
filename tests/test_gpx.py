"""Tests for GPX / KML track support (issue #64)."""

import geopandas as gpd
import pytest
from shapely.geometry import LineString, MultiLineString, Polygon

import prettymaps
import prettymaps.draw as draw
from prettymaps.gpx import is_track_file, read_track, track_center, track_radius

_GPX_SAMPLE = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" xmlns="http://www.topografix.com/GPX/1/1">
  <trk><name>seg1</name><trkseg>
    <trkpt lat="41.8800" lon="-87.6300"/>
    <trkpt lat="41.8810" lon="-87.6320"/>
    <trkpt lat="41.8820" lon="-87.6340"/>
  </trkseg></trk>
  <trk><trkseg>
    <trkpt lat="41.8790" lon="-87.6280"/>
    <trkpt lat="41.8795" lon="-87.6290"/>
  </trkseg></trk>
</gpx>
"""

_KML_SAMPLE = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2"><Document><Placemark><LineString>
  <coordinates>-87.6300,41.8800,0 -87.6320,41.8810,0 -87.6340,41.8820,0</coordinates>
</LineString></Placemark></Document></kml>
"""


# --- parser -----------------------------------------------------------------

def test_is_track_file():
    assert is_track_file("walk.gpx")
    assert is_track_file("WALK.GPX")
    assert is_track_file("route.kml")
    assert not is_track_file("Porto Alegre")
    assert not is_track_file((41.39, 2.17))


def test_read_track_gpx(tmp_path):
    path = tmp_path / "walk.gpx"
    path.write_text(_GPX_SAMPLE)
    geom = read_track(str(path))
    assert isinstance(geom, MultiLineString)
    assert len(geom.geoms) == 2
    lat, lon = track_center(geom)
    assert 41.87 < lat < 41.89 and -87.64 < lon < -87.62
    assert track_radius(geom) >= 250.0


def test_read_track_kml(tmp_path):
    path = tmp_path / "walk.kml"
    path.write_text(_KML_SAMPLE)
    geom = read_track(str(path))
    assert isinstance(geom, MultiLineString)
    assert len(geom.geoms) == 1


def test_read_track_missing_geometry(tmp_path):
    path = tmp_path / "empty.gpx"
    path.write_text('<?xml version="1.0"?><gpx xmlns="http://www.topografix.com/GPX/1/1"/>')
    assert read_track(str(path)) is None


def test_read_track_multiple_files(tmp_path):
    a = tmp_path / "a.gpx"; a.write_text(_GPX_SAMPLE)
    b = tmp_path / "b.kml"; b.write_text(_KML_SAMPLE)
    geom = read_track([str(a), str(b)])
    assert isinstance(geom, MultiLineString)
    assert len(geom.geoms) == 3


# --- plot() integration (draw functions mocked; no network) -----------------

def _mock_draw(monkeypatch):
    monkeypatch.setattr(draw, "transform_gdfs", lambda gdfs, *a, **k: gdfs)
    monkeypatch.setattr(draw, "create_background", lambda *a, **k: (None, 0, 0, 0, 0, 0, 0))
    monkeypatch.setattr(draw, "draw_layers", lambda *a, **k: None)
    monkeypatch.setattr(draw, "draw_keypoints", lambda *a, **k: None)
    monkeypatch.setattr(draw, "draw_background", lambda *a, **k: None)
    monkeypatch.setattr(draw, "draw_credit", lambda *a, **k: None)
    monkeypatch.setattr(draw, "draw_hillshade", lambda *a, **k: None)


def _square(min_lon, min_lat, max_lon, max_lat):
    return gpd.GeoDataFrame(
        geometry=[Polygon([(min_lon, min_lat), (max_lon, min_lat),
                           (max_lon, max_lat), (min_lon, max_lat)])],
        crs="EPSG:4326",
    )


def test_plot_gpx_query_autoframes_and_draws(monkeypatch, tmp_path):
    """A GPX file as the query frames the map around it and adds a 'gpx' layer."""
    path = tmp_path / "walk.gpx"; path.write_text(_GPX_SAMPLE)
    perim = _square(-87.64, 41.87, -87.62, 41.89)
    captured = {}

    def fake_get_gdfs(query, *a, **k):
        captured["query"] = query
        return {"perimeter": perim.copy()}

    monkeypatch.setattr(draw, "get_gdfs", fake_get_gdfs)
    _mock_draw(monkeypatch)
    result = prettymaps.plot(str(path), show=False)
    # query was replaced by the track centre (a lat/lon tuple)
    assert isinstance(captured["query"], tuple)
    # the track was injected as a drawable line layer
    assert "gpx" in result.geodataframes
    geom = result.geodataframes["gpx"].geometry.iloc[0]
    assert isinstance(geom, (LineString, MultiLineString))


def test_plot_gpx_param_overlays_without_reframing(monkeypatch, tmp_path):
    """`gpx=` draws the track over a normal query without changing that query."""
    path = tmp_path / "walk.gpx"; path.write_text(_GPX_SAMPLE)
    perim = _square(0, 0, 1, 1)
    captured = {}

    def fake_get_gdfs(query, *a, **k):
        captured["query"] = query
        return {"perimeter": perim.copy()}

    monkeypatch.setattr(draw, "get_gdfs", fake_get_gdfs)
    _mock_draw(monkeypatch)
    result = prettymaps.plot("Porto Alegre", gpx=str(path), show=False)
    assert captured["query"] == "Porto Alegre"  # not reframed
    assert "gpx" in result.geodataframes


def test_plot_gpx_custom_style(monkeypatch, tmp_path):
    """gpx_style overrides the default track style passed to draw_layers."""
    path = tmp_path / "walk.gpx"; path.write_text(_GPX_SAMPLE)
    perim = _square(0, 0, 1, 1)
    style_seen = {}

    monkeypatch.setattr(draw, "get_gdfs", lambda *a, **k: {"perimeter": perim.copy()})
    monkeypatch.setattr(draw, "transform_gdfs", lambda gdfs, *a, **k: gdfs)
    monkeypatch.setattr(draw, "create_background", lambda *a, **k: (None, 0, 0, 0, 0, 0, 0))
    monkeypatch.setattr(draw, "draw_layers",
                        lambda layers, gdfs, style, *a, **k: style_seen.update(style))
    monkeypatch.setattr(draw, "draw_keypoints", lambda *a, **k: None)
    monkeypatch.setattr(draw, "draw_background", lambda *a, **k: None)
    monkeypatch.setattr(draw, "draw_credit", lambda *a, **k: None)
    monkeypatch.setattr(draw, "draw_hillshade", lambda *a, **k: None)
    prettymaps.plot("Porto Alegre", gpx=str(path),
                    gpx_style={"ec": "#123456", "lw": 9}, show=False)
    assert style_seen["gpx"]["ec"] == "#123456"
    assert style_seen["gpx"]["lw"] == 9
