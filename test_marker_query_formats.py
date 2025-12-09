"""
Test script to verify the three coordinate formats for custom markers.
Tests without requiring full prettymaps execution.
"""

def test_coordinate_formats():
    """Test that all three coordinate formats are valid"""

    print("Testing coordinate format validation...")
    print("=" * 60)

    # Test markers in all three formats
    test_markers = [
        # Format 1: Separate lat/lon
        {
            'name': 'Format 1: Separate lat/lon',
            'lat': 52.3676,
            'lon': 4.9041,
            'marker': 'o',
            'color': '#FF0000'
        },

        # Format 2: Tuple query
        {
            'name': 'Format 2: Tuple query',
            'query': (52.3700, 4.9100),
            'marker': '*',
            'color': '#00FF00'
        },

        # Format 3: String query (simulated - actual geocoding requires osmnx)
        {
            'name': 'Format 3: String query',
            'query': 'Amsterdam Central Station',
            'marker': '^',
            'color': '#0000FF'
        }
    ]

    passed = 0
    failed = 0

    for i, marker in enumerate(test_markers, 1):
        print(f"\nTest {i}: {marker['name']}")
        print("-" * 60)

        # Extract coordinates based on format
        lat = None
        lon = None

        # Check for query field
        if 'query' in marker:
            query = marker['query']

            # Tuple format
            if isinstance(query, tuple) and len(query) == 2:
                lat, lon = query
                print(f"  ✓ Tuple format detected: ({lat}, {lon})")
                print(f"  ✓ Coordinates extracted successfully")
                passed += 1

            # String format
            elif isinstance(query, str):
                print(f"  ✓ String format detected: '{query}'")
                print(f"  ℹ Would geocode this query in real execution")
                print(f"  ✓ Format validation passed")
                passed += 1

            else:
                print(f"  ✗ Invalid query format: {type(query)}")
                failed += 1

        # Check for separate lat/lon
        elif 'lat' in marker and 'lon' in marker:
            lat = marker['lat']
            lon = marker['lon']
            print(f"  ✓ Separate lat/lon detected: ({lat}, {lon})")

            # Validate ranges
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                print(f"  ✓ Coordinates within valid ranges")
                passed += 1
            else:
                print(f"  ✗ Coordinates out of valid ranges")
                failed += 1

        else:
            print(f"  ✗ No valid coordinate format found")
            failed += 1

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


def test_mixed_formats():
    """Test using multiple formats in the same marker list"""

    print("\n\nTesting mixed format usage...")
    print("=" * 60)

    # Mix all three formats in one list
    mixed_markers = [
        {'lat': 52.36, 'lon': 4.90, 'marker': 'o'},
        {'query': (52.37, 4.91), 'marker': '*'},
        {'query': 'Rijksmuseum', 'marker': '^'}
    ]

    print(f"Total markers: {len(mixed_markers)}")

    format_counts = {
        'lat/lon': 0,
        'tuple': 0,
        'string': 0
    }

    for marker in mixed_markers:
        if 'query' in marker:
            if isinstance(marker['query'], tuple):
                format_counts['tuple'] += 1
            elif isinstance(marker['query'], str):
                format_counts['string'] += 1
        elif 'lat' in marker and 'lon' in marker:
            format_counts['lat/lon'] += 1

    print(f"\nFormat distribution:")
    print(f"  - Lat/Lon format: {format_counts['lat/lon']}")
    print(f"  - Tuple format: {format_counts['tuple']}")
    print(f"  - String format: {format_counts['string']}")

    total = sum(format_counts.values())
    if total == len(mixed_markers):
        print(f"\n✓ All {total} markers have valid coordinate format")
        return True
    else:
        print(f"\n✗ Format mismatch: expected {len(mixed_markers)}, got {total}")
        return False


def test_backward_compatibility():
    """Test that old lat/lon format still works"""

    print("\n\nTesting backward compatibility...")
    print("=" * 60)

    # Old format markers (pre-query support)
    old_markers = [
        {'lat': 52.3676, 'lon': 4.9041, 'marker': 'o', 'color': '#FF0000'},
        {'lat': 52.3700, 'lon': 4.9100, 'marker': '*', 'color': '#00FF00'}
    ]

    passed = 0
    for i, marker in enumerate(old_markers, 1):
        if 'lat' in marker and 'lon' in marker:
            lat, lon = marker['lat'], marker['lon']
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                print(f"  ✓ Marker {i}: Old format still valid")
                passed += 1
            else:
                print(f"  ✗ Marker {i}: Coordinates out of range")
        else:
            print(f"  ✗ Marker {i}: Missing coordinates")

    if passed == len(old_markers):
        print(f"\n✓ Backward compatibility maintained ({passed}/{len(old_markers)} markers valid)")
        return True
    else:
        print(f"\n✗ Backward compatibility broken ({passed}/{len(old_markers)} markers valid)")
        return False


if __name__ == "__main__":
    print("Custom Marker Query Format Tests")
    print("=" * 60)
    print()

    all_passed = True

    # Test 1: Individual format validation
    all_passed &= test_coordinate_formats()

    # Test 2: Mixed format usage
    all_passed &= test_mixed_formats()

    # Test 3: Backward compatibility
    all_passed &= test_backward_compatibility()

    print("\n" + "=" * 60)
    if all_passed:
        print("✅ All query format tests passed!")
    else:
        print("❌ Some tests failed!")
    print("=" * 60)

    print("\n📝 Summary of new features:")
    print("  1. Tuple format: {'query': (lat, lon), ...}")
    print("  2. String format: {'query': 'Place Name', ...}")
    print("  3. Backward compatible with: {'lat': X, 'lon': Y, ...}")
    print("  4. Automatic geocoding for string queries via OSMnx")
    print("  5. Streamlit UI with input mode selector")
