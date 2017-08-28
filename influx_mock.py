import time
from influxdb import InfluxDBClient
import numpy as np
from datetime import datetime, timedelta

host = 'localhost'
port = 8086
user = 'admin'
password = 'admin'

# The database we created
dbname = 'first'


# Create the InfluxDB object
client = InfluxDBClient(host, port, user, password, dbname)

# Run until keyboard out
try:
    from itertools import count

    N = 3
    temp = np.random.normal(loc=20, scale=5, size=N)
    pressure = np.random.normal(loc=1000, scale=100, size=N)
    humidity = np.random.normal(loc=50, scale=10, size=N)

    t = datetime.now() - timedelta(days=7)

    for i in count():

        json_body = [
        {
          'measurement': 'ruuvi',
              'tags': {
                  'sensor': 'sensor %i' % i,
                  },
              'time': t.strftime('%Y-%m-%d %H:%M:%S'),
              'fields': {
                  'temp': temp[i],
                  'pressure': pressure[i],
                  'humidity': humidity[i]
              }
          } for i in range(N)
        ]

        # Write JSON to InfluxDB
        client.write_points(json_body)
        # Wait for next sample
        time.sleep(0.2)

        print(t.strftime('%Y-%m-%d %H:%M:%S'), temp)

        temp += np.random.normal(scale=1, size=N)
        pressure += np.random.normal(scale=10, size=N)
        humidity += np.random.normal(scale=2, size=N)
        t = t + timedelta(minutes=1)

except KeyboardInterrupt:
    pass
