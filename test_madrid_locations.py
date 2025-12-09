"""
Test prettymaps with Madrid locations using string geocoding
"""
import prettymaps
import matplotlib.pyplot as plt

# Test configuration
main_location = "Glorieta de Piramides, Madrid, Spain"
marker_location = "Glorieta de Marques de Vadillo, Madrid, Spain"

print("=" * 60)
print("Testing Madrid Locations with Geocoding")
print("=" * 60)
print(f"\nMain map location: {main_location}")
print(f"Marker location: {marker_location}")
print("\nGenerating map...")

# Define custom marker with string query
markers = [
    {
        'query': marker_location,  # String query - will be geocoded
        'marker': '*',
        'size': 300,
        'color': '#FF0000',
        'edgecolor': '#2F3737',
        'linewidth': 2.0,
        'alpha': 0.9,
        'zorder': 1000,
        'name': 'Marques de Vadillo'
    }
]

try:
    # Generate the map
    plot = prettymaps.plot(
        query=main_location,
        radius=1000,
        preset='default',
        custom_markers=markers,
        figsize=(10, 10),
        show=False,
        logging=True  # Enable logging to see geocoding results
    )

    print("\n" + "=" * 60)
    print("✅ SUCCESS!")
    print("=" * 60)
    print("\nMap generated successfully with:")
    print(f"  • Main location: {main_location}")
    print(f"  • Custom marker: {marker_location}")
    print("\nSaving to file...")

    # Save the result
    plt.savefig('/tmp/madrid_test.png', dpi=150, bbox_inches='tight')
    print(f"  • Saved to: /tmp/madrid_test.png")

    print("\n✅ Test completed successfully!")

except Exception as e:
    print("\n" + "=" * 60)
    print("❌ ERROR!")
    print("=" * 60)
    print(f"\nFailed to generate map: {e}")
    import traceback
    traceback.print_exc()
