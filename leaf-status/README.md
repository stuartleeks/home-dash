# leaf-summary

A service that can be run periodically to get the latest state of a Nissan Leaf and save it to a file.

This uses https://github.com/filcole/pycarwings2 for the actual communication with the car.




## Installation

Set up a .env file with the env vars below:

```env
LEAF_USERNAME=your-username
LEAF_PASSWORD=your-passwoed
# NNA=USA, NE=Europe, NCI=Canada, NMA=Austrailia, NML=Japan
LEAF_REGION=NE

LEAF_OUTPUT_FILE=/path/to/output-file.json
```

Install requirements: `pip install -r requirements.txt`.

At this point you should be able to successfully run the script: `python leaf_summary.py`.

To install as a service on Linux, copy the `leaf-summary.service` file to `/etc/systemd/system/leaf-summary.service`.
Also copy the `leaf-summary.timer` file to `/etc/systemd/system/leaf-summary.timer`.
Finally, run `systemctl enable leaf-summary.service`.

To start the service immediately, run `systemctl start leaf-summary.service`.

To list timers: `systemctl list-timers`.

## Links

- [Systemd](https://wiki.archlinux.org/title/Systemd)
- [Systemd timers](https://wiki.archlinux.org/title/Systemd/Timers) (has calendar syntax - test with `systemd-analyze calendar "*-*-* *:0/30:00"`)
- [Systemd Services](https://man.archlinux.org/man/systemd.service.5.en)
