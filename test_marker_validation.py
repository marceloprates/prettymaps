"""
Test para verificar la validación de marcadores fuera de los límites del mapa.
"""

from shapely.geometry import Point, Polygon

def test_bounds_validation():
    """Test que simula la validación de límites de marcadores"""

    # Crear un perímetro de ejemplo (cuadrado simple)
    perimeter = Polygon([
        (4.90, 52.36),  # SW corner
        (4.91, 52.36),  # SE corner
        (4.91, 52.37),  # NE corner
        (4.90, 52.37),  # NW corner
        (4.90, 52.36)   # Close polygon
    ])

    # Marcadores de prueba
    markers = [
        {'name': 'Inside 1', 'lat': 52.365, 'lon': 4.905},  # Dentro
        {'name': 'Inside 2', 'lat': 52.368, 'lon': 4.908},  # Dentro
        {'name': 'Outside 1', 'lat': 52.380, 'lon': 4.905}, # Fuera (lat muy alto)
        {'name': 'Outside 2', 'lat': 52.365, 'lon': 4.920}, # Fuera (lon muy alto)
        {'name': 'Outside 3', 'lat': 52.350, 'lon': 4.905}, # Fuera (lat muy bajo)
    ]

    valid_markers = []
    invalid_markers = []

    for marker in markers:
        lat = marker['lat']
        lon = marker['lon']
        point = Point(lon, lat)

        # Simular la validación que hace draw_custom_markers
        if perimeter.contains(point) or perimeter.intersects(point):
            valid_markers.append(marker)
        else:
            invalid_markers.append(marker)

    print(f"Total markers: {len(markers)}")
    print(f"Valid markers (inside bounds): {len(valid_markers)}")
    print(f"Invalid markers (outside bounds): {len(invalid_markers)}")

    # Verificaciones
    assert len(valid_markers) == 2, f"Expected 2 valid markers, got {len(valid_markers)}"
    assert len(invalid_markers) == 3, f"Expected 3 invalid markers, got {len(invalid_markers)}"

    # Verificar que los correctos están en cada lista
    assert all(m['name'].startswith('Inside') for m in valid_markers), \
        "All valid markers should have 'Inside' in name"
    assert all(m['name'].startswith('Outside') for m in invalid_markers), \
        "All invalid markers should have 'Outside' in name"

    print("\n✅ Bounds validation test passed!")
    print("\nValid markers:")
    for m in valid_markers:
        print(f"  - {m['name']}: ({m['lat']}, {m['lon']})")

    print("\nInvalid markers (will be skipped):")
    for m in invalid_markers:
        print(f"  - {m['name']}: ({m['lat']}, {m['lon']})")

def test_coordinate_ranges():
    """Test validación de rangos de coordenadas"""

    test_coords = [
        {'lat': 52.3676, 'lon': 4.9041, 'valid': True},   # Normal
        {'lat': 0, 'lon': 0, 'valid': True},              # Ecuador/Prime Meridian
        {'lat': 90, 'lon': 180, 'valid': True},           # Límites máximos
        {'lat': -90, 'lon': -180, 'valid': True},         # Límites mínimos
        {'lat': 91, 'lon': 4.9041, 'valid': False},       # Lat fuera de rango
        {'lat': 52.3676, 'lon': 181, 'valid': False},     # Lon fuera de rango
        {'lat': -91, 'lon': 4.9041, 'valid': False},      # Lat fuera de rango
        {'lat': 52.3676, 'lon': -181, 'valid': False},    # Lon fuera de rango
    ]

    for coord in test_coords:
        lat = coord['lat']
        lon = coord['lon']
        expected_valid = coord['valid']

        # Validación de rangos
        is_valid = (-90 <= lat <= 90) and (-180 <= lon <= 180)

        assert is_valid == expected_valid, \
            f"Coordinate ({lat}, {lon}) validation failed. Expected {expected_valid}, got {is_valid}"

    print("✅ Coordinate range validation test passed!")

if __name__ == "__main__":
    print("=" * 60)
    print("Testing marker validation system")
    print("=" * 60)
    print()

    print("Test 1: Bounds validation")
    print("-" * 60)
    test_bounds_validation()

    print()
    print("Test 2: Coordinate range validation")
    print("-" * 60)
    test_coordinate_ranges()

    print()
    print("=" * 60)
    print("All validation tests passed! ✨")
    print("=" * 60)
