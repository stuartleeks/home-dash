import requests
import os
import adafruit_ahtx0
import board
from dotenv import load_dotenv

load_dotenv()


api_base_url = os.getenv('API_BASE_URL')
if not api_base_url:
    print('ERROR: API_BASE_URL environment variable not set')
    exit(1)
print('API_BASE_URL:', api_base_url)

sensor_id = os.getenv('SENSOR_ID')
if not sensor_id:
    print('ERROR: SENSOR_ID environment variable not set')
    exit(1)
print('SENSOR_ID:', sensor_id)

# Setup I2C Sensor
sensor = adafruit_ahtx0.AHTx0(board.I2C())


# Convert to two decimal places cleanly
# round() won't include trailing zeroes
def round_num(input):
    return '{:.2f}'.format(input)


print('Temperature', round_num(sensor.temperature), 'C')
print('Humidity', round_num(sensor.relative_humidity), '%')

# Send data to API
resp = requests.put(f"{api_base_url}/temperature/{sensor_id}", json={
    "temperature": sensor.temperature,
    "humidity": sensor.relative_humidity
})
resp.raise_for_status()
