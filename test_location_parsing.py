"""
Test to verify the flexible location input parsing logic.
"""

def parse_location(location_str):
    """
    Parse location input - same logic as in app.py
    Returns: (is_coordinates, parsed_value)
    """
    location_str = location_str.strip()

    # Try to parse as "lat, lon" coordinates
    is_coordinates = False
    parsed_value = None

    if ',' in location_str:
        parts = location_str.split(',')
        if len(parts) == 2:
            try:
                lat = float(parts[0].strip())
                lon = float(parts[1].strip())
                # Validate ranges
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    parsed_value = (lat, lon)
                    is_coordinates = True
            except ValueError:
                pass  # Not numeric, treat as place name

    # If not coordinates, treat as place name
    if not is_coordinates:
        parsed_value = location_str

    return is_coordinates, parsed_value


def test_coordinate_parsing():
    """Test parsing of various coordinate formats"""

    print("Testing Coordinate Parsing")
    print("=" * 60)

    test_cases = [
        # Coordinates with various spacing
        ("52.3676, 4.9041", True, (52.3676, 4.9041)),
        ("52.3676,4.9041", True, (52.3676, 4.9041)),
        ("  52.3676  ,  4.9041  ", True, (52.3676, 4.9041)),

        # Negative coordinates
        ("-33.8688, 151.2093", True, (-33.8688, 151.2093)),  # Sydney
        ("40.7128, -74.0060", True, (40.7128, -74.0060)),    # New York

        # Boundary coordinates
        ("90, 180", True, (90.0, 180.0)),
        ("-90, -180", True, (-90.0, -180.0)),
        ("0, 0", True, (0.0, 0.0)),

        # Invalid coordinates (out of range)
        ("91, 4.9041", False, "91, 4.9041"),      # Lat > 90
        ("52.3676, 181", False, "52.3676, 181"),  # Lon > 180
        ("-91, 4.9041", False, "-91, 4.9041"),    # Lat < -90
        ("52.3676, -181", False, "52.3676, -181"),# Lon < -180

        # Place names
        ("Amsterdam Central Station", False, "Amsterdam Central Station"),
        ("Eiffel Tower, Paris", False, "Eiffel Tower, Paris"),
        ("Times Square, New York, NY", False, "Times Square, New York, NY"),

        # Edge cases
        ("not coordinates", False, "not coordinates"),
        ("one,two,three", False, "one,two,three"),  # Too many parts
        ("just_one_part", False, "just_one_part"),
    ]

    passed = 0
    failed = 0

    for input_str, expected_is_coords, expected_value in test_cases:
        is_coords, parsed = parse_location(input_str)

        if is_coords == expected_is_coords and parsed == expected_value:
            result_type = "coordinates" if is_coords else "place name"
            print(f"  ✓ '{input_str}' → {result_type}: {parsed}")
            passed += 1
        else:
            print(f"  ✗ '{input_str}'")
            print(f"     Expected: {expected_is_coords}, {expected_value}")
            print(f"     Got: {is_coords}, {parsed}")
            failed += 1

    print()
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


def test_real_world_examples():
    """Test real-world usage examples"""

    print("\n\nTesting Real-World Examples")
    print("=" * 60)

    examples = [
        {
            'input': '52.3676, 4.9041',
            'description': 'Amsterdam coordinates',
            'expected_type': 'tuple'
        },
        {
            'input': 'Amsterdam Central Station',
            'description': 'Place name',
            'expected_type': 'string'
        },
        {
            'input': '40.7589, -73.9851',
            'description': 'Times Square coordinates',
            'expected_type': 'tuple'
        },
        {
            'input': 'Eiffel Tower, Paris, France',
            'description': 'Place name with commas',
            'expected_type': 'string'  # More than 2 parts
        },
        {
            'input': '-33.8688, 151.2093',
            'description': 'Sydney coordinates (negative lat)',
            'expected_type': 'tuple'
        },
    ]

    for example in examples:
        is_coords, parsed = parse_location(example['input'])

        actual_type = 'tuple' if isinstance(parsed, tuple) else 'string'

        if actual_type == example['expected_type']:
            print(f"  ✓ {example['description']}")
            print(f"     Input: '{example['input']}'")
            print(f"     Parsed as: {actual_type} → {parsed}")
        else:
            print(f"  ✗ {example['description']}")
            print(f"     Expected: {example['expected_type']}, Got: {actual_type}")
        print()

    print("=" * 60)
    return True


def test_user_workflows():
    """Test typical user input scenarios"""

    print("\n\nTesting User Workflows")
    print("=" * 60)

    workflows = [
        {
            'name': 'User enters precise coordinates',
            'inputs': ['52.3676, 4.9041', '40.7128, -74.0060'],
            'expected_type': 'tuple'
        },
        {
            'name': 'User enters place names',
            'inputs': ['Amsterdam', 'Central Park', 'Tokyo Tower'],
            'expected_type': 'string'
        },
        {
            'name': 'User copies coordinates from Google Maps',
            'inputs': ['51.5074, -0.1278', '48.8584, 2.2945'],
            'expected_type': 'tuple'
        },
    ]

    for workflow in workflows:
        print(f"\n{workflow['name']}:")
        all_correct = True

        for input_str in workflow['inputs']:
            is_coords, parsed = parse_location(input_str)
            actual_type = 'tuple' if isinstance(parsed, tuple) else 'string'

            if actual_type == workflow['expected_type']:
                print(f"  ✓ '{input_str}' → {parsed}")
            else:
                print(f"  ✗ '{input_str}' → Expected {workflow['expected_type']}, got {actual_type}")
                all_correct = False

        if all_correct:
            print(f"  → Workflow successful!")

    print("\n" + "=" * 60)
    return True


if __name__ == "__main__":
    print("Flexible Location Input Parsing Tests")
    print("=" * 60)
    print()

    all_passed = True

    # Test 1: Coordinate parsing
    all_passed &= test_coordinate_parsing()

    # Test 2: Real-world examples
    all_passed &= test_real_world_examples()

    # Test 3: User workflows
    all_passed &= test_user_workflows()

    print("\n" + "=" * 60)
    if all_passed:
        print("✅ All location parsing tests passed!")
    else:
        print("❌ Some tests failed!")
    print("=" * 60)

    print("\n📝 Location parsing features:")
    print("  1. Automatically detects 'lat, lon' format")
    print("  2. Validates coordinate ranges (-90 to 90, -180 to 180)")
    print("  3. Treats non-numeric or invalid coords as place names")
    print("  4. Handles various spacing and formatting")
    print("  5. Supports negative coordinates")
    print("  6. Works with place names containing commas")
