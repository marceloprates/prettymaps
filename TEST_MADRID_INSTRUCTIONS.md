# Testing Madrid Locations - Instructions

The Streamlit app is running at: **http://localhost:8501**

## Test Steps

### 1. Set Main Location
In the **Location** text area at the top left:
```
Glorieta de Piramides, Madrid, Spain
```

### 2. Add Custom Marker
1. Click **"Add New Marker"** expander
2. In the **Location** field, enter:
   ```
   Glorieta de Marques de Vadillo, Madrid, Spain
   ```
3. Configure marker (optional):
   - Marker Type: Star
   - Size: 200
   - Color: Red (#FF0000)
4. Click **"Add Marker"** button

### 3. Generate Map
Click the **"Generate"** button

## Expected Results

✅ **Main Location Geocoding**
- The map should center on "Glorieta de Piramides, Madrid, Spain"
- This tests that the main query parameter accepts string locations

✅ **Marker Location Geocoding**
- A red star marker should appear at "Glorieta de Marques de Vadillo, Madrid, Spain"
- This tests that the custom marker `query` field accepts string locations and geocodes them correctly

✅ **Console Output** (if logging is enabled)
- Should show geocoding results for both locations
- Example: `Geocoded 'Glorieta de Marques de Vadillo, Madrid, Spain' to (40.xxxx, -3.xxxx)`

## What This Tests

This test verifies the complete flexible location input implementation:
1. **String geocoding for main map**: Main location accepts place names
2. **String geocoding for markers**: Custom markers can use place names via the `query` field
3. **Smart parsing**: The Location input field automatically detects that this is a place name (not coordinates)
4. **End-to-end workflow**: User can add markers by typing place names without needing coordinates

## Alternative Test with Coordinates

To test coordinate input, try:
- **Main Location**: `40.3978, -3.7153` (Glorieta de Piramides coordinates)
- **Marker Location**: `40.3940, -3.7240` (Glorieta de Marques de Vadillo coordinates)

The input should automatically detect these as coordinates and parse them as tuples.

## Troubleshooting

If the map doesn't generate:
- Check that both locations geocode successfully (watch for error messages)
- Verify the marker appears in the "Current markers" count
- Check the browser console for any errors
- Ensure you have internet connection (required for geocoding)
