#!/bin/bash

# From https://github.com/alexedwards/go-reload/blob/master/go-reload
# sudo apt-get install inotify-tools

function monitor() {
  if [ "$2" = "true" ];  then
    # Watch all files in the specified directory
    # Call the restart function when they are saved
    inotifywait -q -m -r -e close_write -e moved_to $1 |
    while read line; do
      restart
    done
  else
    # Watch all *.go files in the specified directory
    # Call the restart function when they are saved
    inotifywait -q -m -r -e close_write -e moved_to --exclude '[^g][^o]$' $1 |
    while read line; do
      restart
    done
  fi
}

# Terminate and rerun the main Go program
function restart {
  # PROCESS_NAME="dash-api" # TODO filter this!
  echo ">> Stopping... (PROCESS_NAME=$PROCESS_NAME)"
  if [ "$(pidof $PROCESS_NAME)" ]; then
    killall -q -w -9 $PROCESS_NAME
  fi
  # sleep 5
  echo ">> Reloading..."
  eval "go run $ARGS &"
}

# Make sure all background processes get terminated
function close {
  killall -q -w -9 inotifywait
  exit 0
}

echo "here"
trap close INT
echo "== Go-reload"

WATCH_ALL=false
while getopts ":a" opt; do
  case $opt in
    a)
      WATCH_ALL=true
      ;;
    \?)
      echo "Invalid option: -$OPTARG" >&2
      exit 0
      ;;
  esac
done

shift "$((OPTIND - 1))"

if [[ "$1" == "." ]]; then
  if [[ "$2" == "" ]]; then
    echo "Pass process name as second argument"
    exit 1
  else
    PROCESS_NAME=$2
  fi
else
  FILE_NAME=$(basename $1)
  PROCESS_NAME=${FILE_NAME%%.*}
fi

ARGS=$@

# Start the main Go program
echo ">> Watching directories, CTRL+C to stop"
eval "go run $ARGS &"

# Monitor all /src directories on the GOPATH
OIFS="$IFS"
IFS=':'
for path in $GOPATH
do
  if [[ -d "$path/src" ]]; then
    monitor $path/src $WATCH_ALL &
  fi
done
IFS="$OIFS"

# If the current working directory isn't on the GOPATH, monitor it too
if [[ $PWD != "$GOPATH/"* ]]
then
  monitor $PWD $WATCH_ALL
fi

wait