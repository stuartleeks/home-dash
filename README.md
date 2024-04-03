# home-dash

An API for gathering data to show on an [InkyFrame](https://pimoroni.com/inkyframe).

Download FiraCode-Regular.ttf and place in a `fonts` directory under `home-dash`.

## Installation

Set up https://github.com/stuartleeks/leaf-status to run on a schedule and output to a directory.

Set up a `pi.env`` file with the env vars below:

```env
DASHBOARD_INPUT_DIR=/path/to/output-files
```

Install requirements: `pip install -r requirements.txt`.

To install as a service on Linux, copy the `home-dash.service` file to `/etc/systemd/system/home-dash.service`.
Then run `systemctl enable home-dash.service`.

To start the service immediately, run `systemctl start leaf-summary.service`.

