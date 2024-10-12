from shapely.geometry import Polygon, box
import geopandas as gpd
import matplotlib.pyplot as plt
import simplekml
import os

def divide_polygon_by_degree(polygon):
    """
    Divides a polygon into smaller rectangles with a size of 1 degree in latitude and longitude.

    :param polygon: Shapely Polygon object.
    :return: List of smaller polygons.
    """
    minx, miny, maxx, maxy = polygon.bounds

    smaller_polygons = []

    for lat in range(int(miny), int(maxy)):
        for lon in range(int(minx), int(maxx)):
            smaller_polygon = box(lon, lat, lon + 1, lat + 1)
            if smaller_polygon.intersects(polygon):
                smaller_polygons.append(smaller_polygon)

    return smaller_polygons

# Example usage:
# Define the polygon coordinates (e.g., a rectangle)
polygon_coords = [(21, 53), (20, 35), (20, 7), (42, 8), (71, 20), (80, 30), (82, 36), (66, 46), (43, 47), (38, 54), (21, 53)]
polygon = Polygon(polygon_coords)

smaller_polygons = divide_polygon_by_degree(polygon)

# Convert the list of polygons to a GeoDataFrame for visualization
gdf = gpd.GeoDataFrame({'geometry': smaller_polygons})

# Print the coordinates of each smaller polygon
for idx, row in gdf.iterrows():
    print(f"Polygon {idx + 1}:")
    print(f"  Coordinates: {list(row['geometry'].exterior.coords)}")
    print()

# Optionally, visualize the polygons
gdf.plot()
plt.show()

# Create a KML file with different colors for each polygon
colors = ['ff0000ff', 'ff00ff00', 'ffff0000', 'ff00ffff', 'ffff00ff', 'ffffff00']

# Create directories based on latitude
lat_dirs = {}
for idx, row in gdf.iterrows():
    lat = int(row['geometry'].bounds[1])  # Get the latitude
    if lat not in lat_dirs:
        lat_dirs[lat] = []
    lat_dirs[lat].append(row['geometry'])

# Create the main output directory
output_dir = "output"
os.makedirs(output_dir, exist_ok=True)

# Create KML files in each latitude directory inside the main output directory
for lat, polygons in lat_dirs.items():
    lat_dir = os.path.join(output_dir, f"lat_{lat}")
    os.makedirs(lat_dir, exist_ok=True)
    
    kml = simplekml.Kml()
    for j, polygon in enumerate(polygons):
        coords = list(polygon.exterior.coords)
        pol = kml.newpolygon(name=f"Polygon {j + 1}", outerboundaryis=coords)
        pol.style.polystyle.color = colors[j % len(colors)]
    
    kml.save(os.path.join(lat_dir, f"polygons_lat_{lat}.kml"))

print("KML files have been created successfully.")
