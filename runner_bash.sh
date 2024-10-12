#!/bin/bash

apt update

apt install python3-pip
apt install pigz
pip install pillow
pip install shapely geopandas matplotlib simplekml
pip install pykml

read -p "Enter a number: " number

SESSION_NAME="map"

python3 ./cord.py > output.txt

sleep 5

cp output/lat_$number/* .

tmux new-session -d -s $SESSION_NAME 'python3 ./map.py; exec bash'

echo "Started new tmux session: $SESSION_NAME"
