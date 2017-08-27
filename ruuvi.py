from ruuvitag_sensor.ruuvi import RuuviTagSensor
from datetime import datetime
import dataset
import sys
import time
import datetime
import config

print('running, Python version', sys.version)

if False:
    def handle_data(data_list):
        mac, data = data_list
        record = {'MAC': mac, 'timestamp': datetime.now()}
        record.update(data)
        print(record)
        print()


    RuuviTagSensor.get_datas(handle_data)


def collect_and_store(mac_to_name, get_datas, get_time, log_data=False):
    t = get_time()
    datas = get_datas()
    t_str = t.strftime('%Y-%m-%d %H:%M:%S')
    for mac in mac_to_name:
        record = {'sensor_MAC': mac,
                  'sensor_name': mac_to_name[mac],
                  'timestamp': t_str,
                  'year': t.year,
                  'month': t.month,
                  'day': t.day}
        if mac in datas:
            record.update(datas[mac])
        if log_data:
            print(t, record)
        measurements.insert(record)


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
    parser.add_argument('--mock', action='store_true', help='generate a database of mock sensor values')
    parser.add_argument('--interval', default=60, help='sensor readout interval (seconds), default 60')
    args = parser.parse_args()

    if args.mock:
        from sensor_mock import SensorMock

        interval = 0
        db_name = 'sqlite:///measurements-mock.db'
        mac_to_name = {'dummy_mac_1': 'First',
                       'dummy_mac_2': 'Second',
                       'dummy_mac_3': 'Third'}
        sensor_mock = SensorMock(mac_to_name)
        max_iter = sensor_mock.max_iter
        mock_time = sensor_mock.mock_time_generator()
        mock_datas = sensor_mock.mock_data_generator()
        get_datas = lambda: next(mock_datas)
        get_time = lambda: next(mock_time)
    else:
        interval = args.interval
        db_name = 'sqlite:///measurements.db'
        mac_to_name = config.mac_to_name
        max_iter = None
        get_time = datetime.datetime.now
        get_datas = lambda: RuuviTagSensor.get_data_for_sensors(mac_to_name, timeout=interval*0.75)

    db = dataset.connect(db_name)
    measurements = db['measurements']

    repeat(interval,
           max_iter,
           func=lambda: collect_and_store(mac_to_name, get_datas, get_time, log_data=not args.mock))
