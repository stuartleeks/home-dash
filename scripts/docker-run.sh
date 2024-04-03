#!/bin/bash
set -e

docker run --rm -p 8000:8000 -v /home/pi/dashboard-info/:/mnt/dashboard-info -e SKIP_DOTENV=true -e DASHBOARD_INPUT_DIR=/mnt/dashboard-info --env-file /home/pi/dashboard-info/.env --name home-dash home-dash

