#!/bin/bash

script_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

# We use a virtual environment to manage dependencies on the RPi 

# Test if venv is active
if [ -z "$VIRTUAL_ENV" ]; then
	echo "Virtual environment not active"
	# Create virtual environment if needed
	if [ ! -d "$script_dir/.venv" ]; then
		echo "Creating venv, activating and installing dependencies"
		python3 -m venv $script_dir/.venv
		source $script_dir/.venv/bin/activate
		pip install -r $script_dir/requirements.txt
	else
		echo "Activating venv"
		source $script_dir/.venv/bin/activate
	fi
fi

# Run the app
python $script_dir/app.py