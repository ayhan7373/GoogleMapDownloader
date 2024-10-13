#!/bin/bash

apt update

apt install -y python3-pip pigz

pip install pillow shapely geopandas matplotlib simplekml pykml

read -p "Enter a lat number: " number

SESSION_NAME="map"

python3 ./KML_polygonal_conversion_to_kml_files_based_on_latitude.py > output.txt

sleep 5

cp output/lat_$number/* .

tmux new-session -d -s $SESSION_NAME 'python3 ./Download_map_using_kml_file_compress_and_send_using_ftp.py; exec bash'

echo "Started new tmux session: $SESSION_NAME"
