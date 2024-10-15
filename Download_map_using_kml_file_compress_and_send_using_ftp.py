import requests
from PIL import Image
from io import BytesIO
import os
import math
from concurrent.futures import ThreadPoolExecutor, as_completed
from pykml import parser
import time
import shutil
import subprocess
import gzip
import tarfile

ZOOM_LEVELS = range(1, 17) # Zoom levels 1 to 16

def latlon_to_tile(lat, lon, zoom):
    """Convert latitude and longitude to tile coordinates."""
    xtile = int((lon + 180.0) / 360.0 * (1 << zoom))
    ytile = int((1.0 - math.log(math.tan(lat * math.pi / 180.0) + 1.0 / math.cos(lat * math.pi / 180.0)) / math.pi) / 2.0 * (1 << zoom))
    return xtile, ytile

def download_tile(url, save_path):
    """Download a tile from the given URL and save it to the specified path."""
    response = requests.get(url)
    if response.status_code == 200:
        img = Image.open(BytesIO(response.content))
        img.save(save_path)
        return True
    return False

def extract_coordinates_from_kml(kml_file):
    """Extract coordinates from a KML file."""
    with open(kml_file, 'r') as f:
        doc = parser.parse(f).getroot()
    
    coordinates = []
    # Check for different possible structures
    if hasattr(doc.Document, 'Folder'):
        placemarks = doc.Document.Folder.getchildren()
    elif hasattr(doc.Document, 'Placemark'):
        placemarks = doc.Document.getchildren()
    else:
        placemarks = doc.getchildren()

    for placemark in placemarks:
        if hasattr(placemark, 'Polygon'):
            coords = placemark.Polygon.outerBoundaryIs.LinearRing.coordinates.text.strip().split()
            polygon_coords = [(float(lon), float(lat)) for lon, lat, _ in (coord.split(',') for coord in coords)]
            coordinates.append(polygon_coords)
    
    return coordinates

def main():
    # Find the first existing KML file in the directory
    kml_files = [f for f in os.listdir('.') if f.endswith('.kml')]

    if not kml_files:
        print("No KML file found in the directory.")
        return

    kml_file = kml_files[0]
    coordinates = extract_coordinates_from_kml(kml_file)

    # Get the bottom-right latitude of the first polygon
    first_polygon_coords = coordinates[0]
    bottom_right_lat = min(coord[1] for coord in first_polygon_coords)

    # Check for existing ZIP files and skip corresponding directories
    existing_zip_files = {f.split('.zip')[0] for f in os.listdir('tiles') if f.endswith('.zip')}

    for polygon_coords in coordinates:
        # Print the coordinates of the polygon
        print(f"Polygon Coordinates: {polygon_coords}")

        # Define the top-left and bottom-right coordinates for each polygon
        top_left_lat = max(coord[1] for coord in polygon_coords)
        top_left_lon = min(coord[0] for coord in polygon_coords)
        bottom_right_lat = min(coord[1] for coord in polygon_coords)
        bottom_right_lon = max(coord[0] for coord in polygon_coords)

        # Create a directory name based on the polygon coordinates
        polygon_dir_name = f"{top_left_lat}_{top_left_lon}_{bottom_right_lat}_{bottom_right_lon}_zoom_1_to_16_google_hybrid_map"
        polygon_dir_path = os.path.join("tiles", polygon_dir_name)

        # Skip if the directory has already been zipped
        if polygon_dir_name in existing_zip_files:
            print(f"Skipping {polygon_dir_name} as it has already been zipped.")
            continue

        # Check if the directory already exists and clear it
        if os.path.exists(polygon_dir_path):
            print(f"Clearing existing directory: {polygon_dir_path}")
            shutil.rmtree(polygon_dir_path)

        os.makedirs(polygon_dir_path, exist_ok=True)

        for zoom_level in ZOOM_LEVELS:
            # Convert coordinates to tile coordinates
            x1, y1 = latlon_to_tile(top_left_lat, top_left_lon, zoom_level)
            x2, y2 = latlon_to_tile(bottom_right_lat, bottom_right_lon, zoom_level)

            # Ensure x1, y1 are the top-left and x2, y2 are the bottom-right
            if x1 > x2:
                x1, x2 = x2, x1
            if y1 > y2:
                y1, y2 = y2, y1

            # Calculate the number of tiles to download
            num_tiles = (x2 - x1 + 1) * (y2 - y1 + 1)
            print(f"Number of tiles to download for zoom {zoom_level}: {num_tiles}")

            # Create a list of tasks
            tasks = []
            for x in range(x1, x2 + 1):
                for y in range(y1, y2 + 1):
                    url = f"http://mt0.google.com/vt/lyrs=y&hl=en&x={x}&y={y}&z={zoom_level}"
                    save_path = os.path.join(polygon_dir_path, f"{zoom_level}", f"{x}", f"{y}.jpg")

                    # Create directories if they don't exist
                    os.makedirs(os.path.dirname(save_path), exist_ok=True)

                    tasks.append((url, save_path))

            # Use ThreadPoolExecutor to download tiles concurrently
            downloaded_count = 0
            with ThreadPoolExecutor(max_workers=12) as executor:
                futures = [executor.submit(download_tile, url, save_path) for url, save_path in tasks]

                for future in as_completed(futures):
                    if future.result():
                        downloaded_count += 1
                        print(f"Downloaded tile: {downloaded_count}/{tasks[futures.index(future)][1]}")
                    else:
                        print(f"Failed to download tile: {tasks[futures.index(future)][0]}")

                    # Print the coordinate being downloaded
                    x, y = tasks[futures.index(future)][1].split('/')[-2:]
                    x = int(x)
                    y = int(y.split('.')[0])
                    lat, lon = tile_to_latlon(x, y, zoom_level)
                    print(f"Downloading tile for coordinate: ({lat}, {lon})")

            print(f"Total tiles downloaded for zoom {zoom_level}: {downloaded_count}/{num_tiles}")

        # Compress the downloaded tiles into a ZIP file
        zip_file_path = os.path.join("tiles", f"{polygon_dir_name}.zip")
        shutil.make_archive(polygon_dir_path, 'zip', polygon_dir_path)
        
        # Remove the original directory after compression
        shutil.rmtree(polygon_dir_path)

        # Wait for 5 minutes after downloading each polygon
        print("Waiting for 4 minutes before processing the next polygon...")
        time.sleep(240)

    # After all polygons are processed, compress all ZIP files into a single GZ file
    all_zip_files = [f for f in os.listdir("tiles") if f.endswith(".zip")]
    gz_file_path = os.path.join("tiles", f"{bottom_right_lat}.tar.gz")
    with tarfile.open(gz_file_path, "w:gz") as tar:
        for zip_file in all_zip_files:
            tar.add(os.path.join("tiles", zip_file), arcname=zip_file)

    # Upload the GZ file via FTP using curl
    ftp_command = f'curl -T {gz_file_path} --user "aseman.ayhan@gmail.com:Ayhan1400" ftp://ir61.uploadboy.com'
    subprocess.run(ftp_command, shell=True)

def tile_to_latlon(xtile, ytile, zoom):
    """Convert tile coordinates to latitude and longitude."""
    n = 1 << zoom
    lon_deg = xtile / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / n)))
    lat_deg = math.degrees(lat_rad)
    return lat_deg, lon_deg

if __name__ == "__main__":
    main()

""" Google_Hybrid_Map_URL: http://mt0.google.com/vt/lyrs=y&hl=en&x={x}&y={y}&z={zoom_level}"""
""" Google_Satellite_Map_URL: http://mt0.google.com/vt/lyrs=s&hl=en&x={x}&y={y}&z={zoom_level}"""
""" Bing_Hybrid_Map_URL: https://t.ssl.ak.dynamic.tiles.virtualearth.net/comp/ch/{zoom_level}/{x}/{y}?mkt=en-US&it=A&og=1&n=z"""
