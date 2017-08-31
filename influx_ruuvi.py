from influxdb import InfluxDBClient
from datetime import datetime, timedelta
from ruuvi import RuuviTagSensor
from os import path
import yaml


class DataCollector:
    def __init__(self, influx_client, sensor_yaml, timeout, mock=False, mock_days=3):
        self.influx_client = influx_client
        self.sensor_yaml = sensor_yaml
        self.timeout = timeout
        self.log_data = not mock
        self.max_iterations = None  # run indefinitely by default
        self.mock = False

        self.sensor_map = None
        self.sensor_map_last_change = -1
        print('Sensors:')
        for mac in sorted(self.get_sensors()):
            print('\t', mac, '<-->', self.sensor_map[mac])

        if mock:
            import sensor_mock
            self.mock = sensor_mock.SensorMock(mock_days=int(mock_days))
            self._mock_time = self.mock.mock_time_generator()
            self._mock_datas = self.mock.mock_data_generator()
            self.max_iterations = self.mock.max_iter if int(mock_days) > 0 else None

    def get_sensors(self):
        assert path.exists(self.sensor_yaml), 'Sensor map not found: %s' % self.sensor_yaml
        if path.getmtime(self.sensor_yaml) != self.sensor_map_last_change:
            try:
                print('reloading sensor map as file changed')
                new_map = yaml.load(open(self.sensor_yaml))
                self.sensor_map = new_map
                self.sensor_map_last_change = path.getmtime(self.sensor_yaml)
            except Exception as e:
                print('failed to re-load sensor map, going on with the old one:')
                print(e)
        return self.sensor_map

    def collect_and_store(self):
        metrics = ['battery',
                   'pressure',
                   'humidity',
                   'acceleration',
                   'acceleration_x',
                   'acceleration_y',
                   'acceleration_z',
                   'temperature']
        # metrics = ['pressure',
        #            'humidity',
        #            'temperature',
        #            'battery']

        if self.mock:
            sensors = self.mock.mac_to_name
            t_utc = next(self._mock_time)
            datas = next(self._mock_datas)
        else:
            sensors = self.get_sensors()
            t_utc = datetime.utcnow()
            datas = RuuviTagSensor.get_data_for_sensors(sensors, int(self.timeout))

        if len(datas) == 0:
            return

        # t_str = t.strftime('%Y-%m-%d %H:%M:%S')

        t_str = t_utc.isoformat() + 'Z'

        print('sensors seen:', list(datas.keys()))
        json_body = [
            {
                'measurement': 'ruuvi',
                'tags': {
                    'sensor': sensors[mac],
                },
                'time': t_str,
                'fields': {metric: datas[mac][metric] for metric in metrics if metric in datas[mac]}  # datas[mac]
            }
            for mac in datas if mac in sensors
        ]
        if len(json_body) > 0:
            if not self.influx_client.write_points(json_body):
                print('not written!')
            else:
                print(t_utc, json_body)
        else:
            print(t_utc, 'no data')


def repeat(interval_sec, max_iter, func, *args, **kwargs):
    from itertools import count
    import time
    starttime = time.time()
    for i in count():
        if i % 1000 == 0:
            print('collected %d samples' % i)
        func(*args, **kwargs)
        if interval_sec > 0:
            time.sleep(interval_sec - ((time.time() - starttime) % interval_sec))
        if max_iter and i >= max_iter:
            return


if __name__ == '__main__':

    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--mock', action='store_true',
                        help='generate a database of mock sensor values')
    parser.add_argument('--mock_days', help='days of data to mock', default=30, type=int)
    parser.add_argument('--interval', default=60,
                        help='sensor readout interval (seconds), default 60')
    parser.add_argument('--sensors', default='sensors.yml',
                        help='YAML file mapping sensor MACs to names, default "sensors.yml"')
    args = parser.parse_args()

    if args.mock:
        interval = 5
    else:
        interval = int(args.interval)

    # Create the InfluxDB object
    influx_config = yaml.load(open('influx_config.yml'))
    client = InfluxDBClient(influx_config['host'],
                            influx_config['port'],
                            influx_config['user'],
                            influx_config['password'],
                            influx_config['dbname'])

    collector = DataCollector(influx_client=client,
                              sensor_yaml='sensors.yml',
                              timeout=int(0.75 * interval),
                              mock=args.mock,
                              mock_days=args.mock_days)
    repeat(interval,
           max_iter=collector.max_iterations,
           func=lambda: collector.collect_and_store())
