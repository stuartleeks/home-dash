# temp-sensor

## systemd setup

```bash

sudo cp temp-sensor.service /etc/systemd/system/
sudo cp temp-sensor.timer /etc/systemd/system/
sudo systemctl daemon-reload

sudo systemctl enable temp-sensor.timer
sudo systemctl enable temp-sensor.service


sudo systemctl start temp-sensor.timer
journalctl -u temp-sensor -f

```