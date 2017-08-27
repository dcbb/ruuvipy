from ruuvitag_sensor.ruuvi import RuuviTagSensor
from datetime import datetime, timedelta
import numpy as np
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

# for mock mode
mock_sample_period = 1  # minutes
mock_samples_per_day = (24 * 60) / mock_sample_period
mock_days = 21
mock_max_iter = mock_days * mock_samples_per_day


def mock_timeseries(n, day_mid, day_range, largescale_range):
    def largescale_variation(scale=60, base=7):
        B = np.array([np.cos((x / (scale * mock_samples_per_day) * 2 * np.pi) * np.random.normal(loc=1, scale=0.3)) for _ in
                      range(base)])
        v = B.T.dot(2 * np.random.random(size=base) - 1)
        return v / abs(v).max()

    def map_to_range(x, mid, half_width):
        return x * half_width + mid

    x = np.arange(n)
    day_scale = np.sin(x / mock_samples_per_day * 2 * np.pi)
    y = map_to_range(day_scale, mid=day_mid, half_width=day_range / 2) \
        + map_to_range(largescale_variation(), mid=0, half_width=largescale_range / 2)
    return y


def mock_time_generator():
    delta_t = timedelta(minutes=mock_sample_period)
    now = datetime.datetime.now() - timedelta(days=mock_days)
    t = now  # datetime.datetime(year=now.year, month=now.month, day=now.day, hour=6)
    while True:
        yield t
        t += delta_t


def mock_data_generator():
    """
    Generator for mock sensor data. 
    """
    from itertools import count, cycle

    n = mock_max_iter
    temp = {mac: mock_timeseries(int(n), day_mid=15 + np.random.normal(scale=5), day_range=10, largescale_range=5) for
            mac in mac_to_name}
    pressure = {
        mac: mock_timeseries(int(n), day_mid=1000 + np.random.normal(scale=100), day_range=100, largescale_range=20) for
        mac
        in mac_to_name}
    humidity = {mac: mock_timeseries(int(n), day_mid=40 + np.random.normal(scale=10), day_range=20, largescale_range=20)
                for mac in mac_to_name}

    index = cycle(range(int(n)))
    while True:
        i = next(index)
        yield {mac: {'identifier': 'w',
                     'pressure': pressure[mac][i],
                     'temperature': temp[mac][i],
                     'humidity': humidity[mac][i]} for mac in mac_to_name}


mock_data = mock_data_generator()
mock_time = mock_time_generator()


def get_sensor_data(timeout, mock=True):
    if mock:
        datas = next(mock_data)
        t = next(mock_time)
    else:
        datas = RuuviTagSensor.get_data_for_sensors(mac_to_name, timeout)
        t = datetime.datetime.now()
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
        measurements.insert(record)


def repeat(period_sec, max_iter, func, *args, **kwargs):
    from itertools import count
    starttime = time.time()
    for i in count():
        if i % 1000 == 0:
            print('collected %d samples' % i)
        func(*args, **kwargs)
        if period_sec > 0:
            time.sleep(period_sec - ((time.time() - starttime) % period_sec))
        if max_iter and i >= max_iter:
            return


if __name__ == '__main__':
    mock = True

    if mock:
        period_sec = 0
        db_name = 'sqlite:///measurements-mock.db'
        mac_to_name = {'dummy_mac_1': 'First',
                       'dummy_mac_2': 'Second',
                       'dummy_mac_3': 'Third'}
    else:
        period_sec = 60
        db_name = 'sqlite:///measurements.db'
        mac_to_name = config.mac_to_name

    db = dataset.connect(db_name)
    measurements = db['measurements']

    repeat(period_sec, mock_max_iter, get_sensor_data, timeout=period_sec * 0.75)
