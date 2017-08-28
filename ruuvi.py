from ruuvitag_sensor.ruuvi import RuuviTagSensor
import dataset
import time
from datetime import datetime
import yaml
from os import path


def discover_sensors():
    seen_macs = set()
    n_macs_last_seen = 0

    def handle_data(data_list):
        global n_macs_last_seen
        mac, data = data_list
        seen_macs.add(mac)
        if len(seen_macs) != n_macs_last_seen:
            n_macs_last_seen = len(seen_macs)
            print('Seeing RUUVI MACS:')
            print('\n'.join(sorted(seen_macs)))

    RuuviTagSensor.get_datas(handle_data)


def flood_data():
    def handle_data(data_list):
        mac, data = data_list
        record = {'MAC': mac, 'timestamp': datetime.now()}
        record.update(data)
        print(record)
        print()

    RuuviTagSensor.get_datas(handle_data)


class DataCollector:
    def __init__(self, database_table, sensor_yaml, timeout, mock=False):
        self.database_table = database_table
        self.sensor_yaml = sensor_yaml
        self.timeout = timeout
        self.log_data = not mock
        self.max_iterations = None  # run indefinitely by default
        self.mock = None

        self.sensor_map = None
        self.sensor_map_last_change = -1
        print('Sensors:')
        for mac in sorted(self.get_sensors()):
            print('\t', mac, '<-->', self.sensor_map[mac])

        if mock:
            import sensor_mock
            self.mock = sensor_mock.SensorMock(mock_days=62)
            self._mock_time = self.mock.mock_time_generator()
            self._mock_datas = self.mock.mock_data_generator()
            self.max_iterations = self.mock.max_iter

    def get_sensors(self):
        assert path.exists(self.sensor_yaml), 'Sensor map not found: %s' % self.sensor_yaml
        if path.getmtime(self.sensor_yaml) != self.sensor_map_last_change:
            print('reloading sensor map as file changed')
            self.sensor_map = yaml.load(open(self.sensor_yaml))
            self.sensor_map_last_change = path.getmtime(self.sensor_yaml)
        return self.sensor_map

    def collect_and_store(self):
        if self.mock:
            sensors = self.mock.mac_to_name
            t = next(self._mock_time)
            datas = next(self._mock_datas)
        else:
            sensors = self.get_sensors()
            t = datetime.now()
            datas = RuuviTagSensor.get_data_for_sensors(sensors, int(self.timeout))
        t_str = t.strftime('%Y-%m-%d %H:%M:%S')
        for mac in sensors:
            record = {'sensor_MAC': mac,
                      'sensor_name': sensors[mac],
                      'timestamp': t_str,
                      'year': t.year,
                      'month': t.month,
                      'day': t.day}
            if mac in datas:
                record.update(datas[mac])
            if self.log_data:
                print(t, record)
            self.database_table.insert(record)


def repeat(interval_sec, max_iter, func, *args, **kwargs):
    from itertools import count
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
    parser.add_argument('--discover', action='store_true',
                        help='print a list of Ruuvi MACs, whenever a new one is discovered')
    parser.add_argument('--flood', action='store_true',
                        help='print sensor readout of all discovered Ruuvis')
    parser.add_argument('--mock', action='store_true',
                        help='generate a database of mock sensor values')
    parser.add_argument('--interval', default=60,
                        help='sensor readout interval (seconds), default 60')
    parser.add_argument('--sensors', default='sensors.yml',
                        help='YAML file mapping sensor MACs to names, default "sensors.yml"')
    args = parser.parse_args()

    if args.discover:
        discover_sensors()
        exit()

    elif args.flood:
        flood_data()
        exit()

    if args.mock:
        interval = 0
        db_name = 'sqlite:///measurements-mock.db'

    else:
        interval = int(args.interval)
        db_name = 'sqlite:///measurements.db'

    db = dataset.connect(db_name)
    measurements_table = db['measurements']

    collector = DataCollector(database_table=measurements_table,
                              sensor_yaml=args.sensors,
                              timeout=args.interval * 0.75,
                              mock=args.mock)

    repeat(interval,
           collector.max_iterations,
           func=lambda: collector.collect_and_store())
