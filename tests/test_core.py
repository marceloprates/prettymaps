import pytest
import prettymaps
import osmnx as ox
import geopandas as gpd

# Helper to get a GeoDataFrame for a given query
def get_gdf(query = "Bom Fim, Porto Alegre, Brasil"):
    return ox.geocode_to_gdf(query)

# Test that presets() returns a DataFrame with known presets
def test_presets():
    df = prettymaps.presets()
    assert not df.empty
    assert 'preset' in df.columns
    assert 'params' in df.columns
    assert 'default' in df['preset'].values

# Test that preset() returns a Preset object with params
def test_preset():
    p = prettymaps.preset('default')
    assert hasattr(p, 'params')
    assert isinstance(p.params, dict)
    assert 'layers' in p.params
    assert 'style' in p.params

# Test create_preset and reading it back
def test_create_and_read_preset(tmp_path):
    name = 'pytest-temp-preset'
    layers = {'building': {'tags': {'building': True}}}
    style = {'building': {'fc': '#fff'}}
    prettymaps.create_preset(name, layers=layers, style=style)
    p = prettymaps.preset(name)
    assert p.params['layers'] == layers
    assert p.params['style'] == style

# Test Subplot class
def test_subplot():
    s = prettymaps.Subplot('Porto Alegre', style={'building': {'fc': '#fff'}})
    assert s.query == 'Porto Alegre'
    assert 'style' in s.kwargs

# Test plot() basic call returns expected attributes (mocked heavy work)
def test_plot_smoke(monkeypatch):
    import prettymaps.draw as draw
    monkeypatch.setattr(draw, 'get_gdfs', lambda *a, **k: {'perimeter': get_gdf(), 'building': get_gdf()})
    monkeypatch.setattr(draw, 'create_background', lambda *a, **k: (None, 0,0,0,0,0,0))
    monkeypatch.setattr(draw, 'draw_layers', lambda *a, **k: None)
    monkeypatch.setattr(draw, 'draw_keypoints', lambda *a, **k: None)
    monkeypatch.setattr(draw, 'draw_background', lambda *a, **k: None)
    monkeypatch.setattr(draw, 'draw_credit', lambda *a, **k: None)
    monkeypatch.setattr(draw, 'draw_hillshade', lambda *a, **k: None)
    result = prettymaps.plot('Porto Alegre', show=False)
    assert hasattr(result, 'geodataframes')
    assert hasattr(result, 'fig')
    assert hasattr(result, 'ax')

# Test multiplot() with two subplots (mocked)
def test_multiplot_smoke(monkeypatch):
    import prettymaps.draw as draw
    monkeypatch.setattr(draw, 'plot', lambda *a, **k: type('FakePlot', (), {'geodataframes': {}, 'fig': None, 'ax': None, 'background': None, 'keypoints': None})())
    s1 = prettymaps.Subplot('Cidade Baixa, Porto Alegre')
    s2 = prettymaps.Subplot('Bom Fim, Porto Alegre')
    prettymaps.multiplot(s1, s2, figsize=(4,4)) 

# Test plot() with a (lat, lon) tuple as query (mocked)
def test_plot_latlon_tuple(monkeypatch):
    import prettymaps.draw as draw
    monkeypatch.setattr(draw, 'get_gdfs', lambda *a, **k: {'perimeter': get_gdf(), 'building': get_gdf()})
    monkeypatch.setattr(draw, 'create_background', lambda *a, **k: (None, 0,0,0,0,0,0))
    monkeypatch.setattr(draw, 'draw_layers', lambda *a, **k: None)
    monkeypatch.setattr(draw, 'draw_keypoints', lambda *a, **k: None)
    monkeypatch.setattr(draw, 'draw_background', lambda *a, **k: None)
    monkeypatch.setattr(draw, 'draw_credit', lambda *a, **k: None)
    monkeypatch.setattr(draw, 'draw_hillshade', lambda *a, **k: None)
    result = prettymaps.plot((41.39, 2.17), show=False)
    assert hasattr(result, 'geodataframes')
    assert hasattr(result, 'fig')
    assert hasattr(result, 'ax')

# Test plot() with custom layers and style (mocked)
def test_plot_custom_layers_style(monkeypatch):
    import prettymaps.draw as draw
    monkeypatch.setattr(draw, 'get_gdfs', lambda *a, **k: {'perimeter': get_gdf(), 'building': get_gdf()})
    monkeypatch.setattr(draw, 'create_background', lambda *a, **k: (None, 0,0,0,0,0,0))
    monkeypatch.setattr(draw, 'draw_layers', lambda *a, **k: None)
    monkeypatch.setattr(draw, 'draw_keypoints', lambda *a, **k: None)
    monkeypatch.setattr(draw, 'draw_background', lambda *a, **k: None)
    monkeypatch.setattr(draw, 'draw_credit', lambda *a, **k: None)
    monkeypatch.setattr(draw, 'draw_hillshade', lambda *a, **k: None)
    layers = {'building': {'tags': {'building': True}}}
    style = {'building': {'fc': '#fff'}}
    result = prettymaps.plot('Porto Alegre', layers=layers, style=style, show=False)
    assert hasattr(result, 'geodataframes')

# Test plot() with radius set to False (mocked)
def test_plot_radius_false(monkeypatch):
    import prettymaps.draw as draw
    monkeypatch.setattr(draw, 'get_gdfs', lambda *a, **k: {'perimeter': get_gdf(), 'building': get_gdf()})
    monkeypatch.setattr(draw, 'create_background', lambda *a, **k: (None, 0,0,0,0,0,0))
    monkeypatch.setattr(draw, 'draw_layers', lambda *a, **k: None)
    monkeypatch.setattr(draw, 'draw_keypoints', lambda *a, **k: None)
    monkeypatch.setattr(draw, 'draw_background', lambda *a, **k: None)
    monkeypatch.setattr(draw, 'draw_credit', lambda *a, **k: None)
    monkeypatch.setattr(draw, 'draw_hillshade', lambda *a, **k: None)
    result = prettymaps.plot('Porto Alegre', radius=False, show=False)
    assert hasattr(result, 'geodataframes')

# Test plot() with keypoints argument (mocked)
def test_plot_keypoints(monkeypatch):
    import prettymaps.draw as draw
    monkeypatch.setattr(draw, 'get_gdfs', lambda *a, **k: {'perimeter': get_gdf(), 'building': get_gdf()})
    monkeypatch.setattr(draw, 'create_background', lambda *a, **k: (None, 0,0,0,0,0,0))
    monkeypatch.setattr(draw, 'draw_layers', lambda *a, **k: None)
    monkeypatch.setattr(draw, 'draw_keypoints', lambda *a, **k: 'mocked_keypoints')
    monkeypatch.setattr(draw, 'draw_background', lambda *a, **k: None)
    monkeypatch.setattr(draw, 'draw_credit', lambda *a, **k: None)
    monkeypatch.setattr(draw, 'draw_hillshade', lambda *a, **k: None)
    keypoints = {'tags': {'natural': ['beach']}, 'specific': {'pedra branca': {'tags': {'natural': ['peak']}}}}
    result = prettymaps.plot('Garopaba', keypoints=keypoints, show=False)
    assert result.keypoints == 'mocked_keypoints'

# Test plot() with postprocessing function (mocked)
def test_plot_postprocessing(monkeypatch):
    import prettymaps.draw as draw
    monkeypatch.setattr(draw, 'get_gdfs', lambda *a, **k: {'perimeter': get_gdf(), 'building': get_gdf()})
    monkeypatch.setattr(draw, 'create_background', lambda *a, **k: (None, 0,0,0,0,0,0))
    monkeypatch.setattr(draw, 'draw_layers', lambda *a, **k: None)
    monkeypatch.setattr(draw, 'draw_keypoints', lambda *a, **k: None)
    monkeypatch.setattr(draw, 'draw_background', lambda *a, **k: None)
    monkeypatch.setattr(draw, 'draw_credit', lambda *a, **k: None)
    monkeypatch.setattr(draw, 'draw_hillshade', lambda *a, **k: None)
    def postproc(gdfs):
        gdfs['custom'] = 123
        return gdfs
    result = prettymaps.plot('Porto Alegre', postprocessing=postproc, show=False)
    assert result.geodataframes['custom'] == 123

# Test plot() with save_as argument (mocked file save)
def test_plot_save_as(monkeypatch, tmp_path):
    import prettymaps.draw as draw
    monkeypatch.setattr(draw, 'get_gdfs', lambda *a, **k: {'perimeter': get_gdf(), 'building': get_gdf()})
    monkeypatch.setattr(draw, 'create_background', lambda *a, **k: (None, 0,0,0,0,0,0))
    monkeypatch.setattr(draw, 'draw_layers', lambda *a, **k: None)
    monkeypatch.setattr(draw, 'draw_keypoints', lambda *a, **k: None)
    monkeypatch.setattr(draw, 'draw_background', lambda *a, **k: None)
    monkeypatch.setattr(draw, 'draw_credit', lambda *a, **k: None)
    monkeypatch.setattr(draw, 'draw_hillshade', lambda *a, **k: None)
    monkeypatch.setattr('matplotlib.pyplot.savefig', lambda *a, **k: None)
    save_path = tmp_path / 'out.png'
    result = prettymaps.plot('Porto Alegre', save_as=str(save_path), show=False)
    assert hasattr(result, 'geodataframes')

# Test plot() with circle, radius, and dilate arguments (mocked)
def test_plot_circle_radius_dilate(monkeypatch):
    import prettymaps.draw as draw
    monkeypatch.setattr(draw, 'get_gdfs', lambda *a, **k: {'perimeter': get_gdf(), 'building': get_gdf()})
    monkeypatch.setattr(draw, 'create_background', lambda *a, **k: (None, 0,0,0,0,0,0))
    monkeypatch.setattr(draw, 'draw_layers', lambda *a, **k: None)
    monkeypatch.setattr(draw, 'draw_keypoints', lambda *a, **k: None)
    monkeypatch.setattr(draw, 'draw_background', lambda *a, **k: None)
    monkeypatch.setattr(draw, 'draw_credit', lambda *a, **k: None)
    monkeypatch.setattr(draw, 'draw_hillshade', lambda *a, **k: None)
    result = prettymaps.plot('Porto Alegre', circle=True, radius=1000, dilate=50, show=False)
    assert hasattr(result, 'geodataframes')

# Test plot() with mode='plotter' (mocked vsketch)
def test_plot_mode_plotter(monkeypatch):
    import prettymaps.draw as draw
    class DummyVsk:
        def display(self):
            pass
    monkeypatch.setattr(draw, 'get_gdfs', lambda *a, **k: {'perimeter': get_gdf(), 'building': get_gdf()})
    monkeypatch.setattr(draw, 'create_background', lambda *a, **k: (None, 0,0,0,0,0,0))
    monkeypatch.setattr(draw, 'draw_layers', lambda *a, **k: None)
    monkeypatch.setattr(draw, 'draw_keypoints', lambda *a, **k: None)
    monkeypatch.setattr(draw, 'draw_background', lambda *a, **k: None)
    monkeypatch.setattr(draw, 'draw_credit', lambda *a, **k: None)
    monkeypatch.setattr(draw, 'draw_hillshade', lambda *a, **k: None)
    monkeypatch.setattr(draw, 'init_plot', lambda *a, **k: (None, None, DummyVsk()))
    result = prettymaps.plot('Porto Alegre', mode='plotter', show=True)
    assert hasattr(result, 'geodataframes')

# Test multiplot() with custom Subplot styles (mocked)
def test_multiplot_custom_subplots(monkeypatch):
    import prettymaps.draw as draw
    monkeypatch.setattr(draw, 'plot', lambda *a, **k: type('FakePlot', (), {'geodataframes': {}, 'fig': None, 'ax': None, 'background': None, 'keypoints': None})())
    s1 = prettymaps.Subplot('Cidade Baixa, Porto Alegre', style={'building': {'palette': ['#49392C']}})
    s2 = prettymaps.Subplot('Bom Fim, Porto Alegre', style={'building': {'palette': ['#BA2D0B']}})
    prettymaps.multiplot(s1, s2, figsize=(4,4))

# Test plot() returns object with all expected attributes (mocked)
def test_plot_types(monkeypatch):
    import prettymaps.draw as draw
    monkeypatch.setattr(draw, 'get_gdfs', lambda *a, **k: {'perimeter': get_gdf(), 'building': get_gdf()})
    monkeypatch.setattr(draw, 'create_background', lambda *a, **k: (None, 0,0,0,0,0,0))
    monkeypatch.setattr(draw, 'draw_layers', lambda *a, **k: None)
    monkeypatch.setattr(draw, 'draw_keypoints', lambda *a, **k: None)
    monkeypatch.setattr(draw, 'draw_background', lambda *a, **k: None)
    monkeypatch.setattr(draw, 'draw_credit', lambda *a, **k: None)
    monkeypatch.setattr(draw, 'draw_hillshade', lambda *a, **k: None)
    result = prettymaps.plot('Porto Alegre', show=False)
    assert hasattr(result, 'geodataframes')
    assert hasattr(result, 'fig')
    assert hasattr(result, 'ax')
    assert hasattr(result, 'background')
    assert hasattr(result, 'keypoints')

# Test plot() with credit argument (mocked)
def test_plot_credit(monkeypatch):
    import prettymaps.draw as draw
    monkeypatch.setattr(draw, 'get_gdfs', lambda *a, **k: {'perimeter': get_gdf(), 'building': get_gdf()})
    monkeypatch.setattr(draw, 'create_background', lambda *a, **k: (None, 0,0,0,0,0,0))
    monkeypatch.setattr(draw, 'draw_layers', lambda *a, **k: None)
    monkeypatch.setattr(draw, 'draw_keypoints', lambda *a, **k: None)
    monkeypatch.setattr(draw, 'draw_background', lambda *a, **k: None)
    monkeypatch.setattr(draw, 'draw_credit', lambda *a, **k: None)
    monkeypatch.setattr(draw, 'draw_hillshade', lambda *a, **k: None)
    credit = {'text': 'Test credit'}
    result = prettymaps.plot('Porto Alegre', credit=credit, show=False)
    assert hasattr(result, 'geodataframes')

# Test plot() with custom figsize argument (mocked)
def test_plot_custom_figsize(monkeypatch):
    import prettymaps.draw as draw
    monkeypatch.setattr(draw, 'get_gdfs', lambda *a, **k: {'perimeter': get_gdf(), 'building': get_gdf()})
    monkeypatch.setattr(draw, 'create_background', lambda *a, **k: (None, 0,0,0,0,0,0))
    monkeypatch.setattr(draw, 'draw_layers', lambda *a, **k: None)
    monkeypatch.setattr(draw, 'draw_keypoints', lambda *a, **k: None)
    monkeypatch.setattr(draw, 'draw_background', lambda *a, **k: None)
    monkeypatch.setattr(draw, 'draw_credit', lambda *a, **k: None)
    monkeypatch.setattr(draw, 'draw_hillshade', lambda *a, **k: None)
    result = prettymaps.plot('Porto Alegre', figsize=(5,5), show=False)
    assert hasattr(result, 'geodataframes')

# Test plot() with x, y, scale_x, scale_y, rotation params (mocked)
def test_plot_transform_params(monkeypatch):
    import prettymaps.draw as draw
    monkeypatch.setattr(draw, 'get_gdfs', lambda *a, **k: {'perimeter': get_gdf(), 'building': get_gdf()})
    monkeypatch.setattr(draw, 'create_background', lambda *a, **k: (None, 0,0,0,0,0,0))
    monkeypatch.setattr(draw, 'draw_layers', lambda *a, **k: None)
    monkeypatch.setattr(draw, 'draw_keypoints', lambda *a, **k: None)
    monkeypatch.setattr(draw, 'draw_background', lambda *a, **k: None)
    monkeypatch.setattr(draw, 'draw_credit', lambda *a, **k: None)
    monkeypatch.setattr(draw, 'draw_hillshade', lambda *a, **k: None)
    result = prettymaps.plot('Porto Alegre', x=1, y=2, scale_x=0.5, scale_y=0.5, rotation=45, show=False)
    assert hasattr(result, 'geodataframes')

# Test plot() with show=True and show=False (mocked plt.show)
def test_plot_show_true_false(monkeypatch):
    import prettymaps.draw as draw
    monkeypatch.setattr(draw, 'get_gdfs', lambda *a, **k: {'perimeter': get_gdf(), 'building': get_gdf()})
    monkeypatch.setattr(draw, 'create_background', lambda *a, **k: (None, 0,0,0,0,0,0))
    monkeypatch.setattr(draw, 'draw_layers', lambda *a, **k: None)
    monkeypatch.setattr(draw, 'draw_keypoints', lambda *a, **k: None)
    monkeypatch.setattr(draw, 'draw_background', lambda *a, **k: None)
    monkeypatch.setattr(draw, 'draw_credit', lambda *a, **k: None)
    monkeypatch.setattr(draw, 'draw_hillshade', lambda *a, **k: None)
    monkeypatch.setattr('matplotlib.pyplot.show', lambda *a, **k: None)
    prettymaps.plot('Porto Alegre', show=True)
    prettymaps.plot('Porto Alegre', show=False)

# Test plot() with update_preset argument (mocked)
def test_plot_update_preset(monkeypatch):
    import prettymaps.draw as draw
    monkeypatch.setattr(draw, 'get_gdfs', lambda *a, **k: {'perimeter': get_gdf(), 'building': get_gdf()})
    monkeypatch.setattr(draw, 'create_background', lambda *a, **k: (None, 0,0,0,0,0,0))
    monkeypatch.setattr(draw, 'draw_layers', lambda *a, **k: None)
    monkeypatch.setattr(draw, 'draw_keypoints', lambda *a, **k: None)
    monkeypatch.setattr(draw, 'draw_background', lambda *a, **k: None)
    monkeypatch.setattr(draw, 'draw_credit', lambda *a, **k: None)
    monkeypatch.setattr(draw, 'draw_hillshade', lambda *a, **k: None)
    monkeypatch.setattr(draw, 'manage_presets', lambda *a, **k: ({'building': {}}, {}, None, None, None))
    result = prettymaps.plot('Porto Alegre', update_preset='default', show=False)
    assert hasattr(result, 'geodataframes')

# Test plot() with semantic=True (mocked)
def test_plot_semantic(monkeypatch):
    import prettymaps.draw as draw
    monkeypatch.setattr(draw, 'get_gdfs', lambda *a, **k: {'perimeter': get_gdf(), 'building': get_gdf()})
    monkeypatch.setattr(draw, 'create_background', lambda *a, **k: (None, 0,0,0,0,0,0))
    monkeypatch.setattr(draw, 'draw_layers', lambda *a, **k: None)
    monkeypatch.setattr(draw, 'draw_keypoints', lambda *a, **k: None)
    monkeypatch.setattr(draw, 'draw_background', lambda *a, **k: None)
    monkeypatch.setattr(draw, 'draw_credit', lambda *a, **k: None)
    monkeypatch.setattr(draw, 'draw_hillshade', lambda *a, **k: None)
    result = prettymaps.plot('Porto Alegre', semantic=True, show=False)
    assert hasattr(result, 'geodataframes')

# Test plot() with adjust_aspect_ratio=False (mocked)
def test_plot_adjust_aspect_ratio(monkeypatch):
    import prettymaps.draw as draw
    monkeypatch.setattr(draw, 'get_gdfs', lambda *a, **k: {'perimeter': get_gdf(), 'building': get_gdf()})
    monkeypatch.setattr(draw, 'create_background', lambda *a, **k: (None, 0,0,0,0,0,0))
    monkeypatch.setattr(draw, 'draw_layers', lambda *a, **k: None)
    monkeypatch.setattr(draw, 'draw_keypoints', lambda *a, **k: None)
    monkeypatch.setattr(draw, 'draw_background', lambda *a, **k: None)
    monkeypatch.setattr(draw, 'draw_credit', lambda *a, **k: None)
    monkeypatch.setattr(draw, 'draw_hillshade', lambda *a, **k: None)
    result = prettymaps.plot('Porto Alegre', adjust_aspect_ratio=False, show=False)
    assert hasattr(result, 'geodataframes') 