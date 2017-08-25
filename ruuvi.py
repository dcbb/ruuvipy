#from ruuvitag_sensor.ruuvi import RuuviTagSensor
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
matplotlib.use('Cairo')
import dataset
import sys

if True:
    plt.style.use('ggplot')
else:
    plt.xkcd()


print('running, Python version', sys.version)

if False:
    # List of macs of sensors which data will be collected
    # If list is empty, data will be collected for all found sensors
    macs = {'EC:F2:E8:09:E4:79': 'First'}
    # get_data_for_sensors will look data for the duration of timeout_in_sec
    timeout_in_sec = 4

    datas = RuuviTagSensor.get_data_for_sensors(macs, timeout_in_sec)
    for mac in macs:
        print(macs[mac], datas[mac])

if False:
    def handle_data(data_list):
        mac, data = data_list
        record = {'MAC': mac, 'timestamp': datetime.now(), **data}
        print(record)
        print()

    RuuviTagSensor.get_datas(handle_data)

import time
import datetime

mac_to_name = {'EC:F2:E8:09:E4:79': 'First',
               'dummy_mac_1': 'Second' }
update_every_n_sec = 5
sample_period = 5 # minutes
samples_per_day = (24 * 60) / sample_period
max_iter = 120 * samples_per_day


def mock_timeseries(n, day_mid, day_range, largescale_range):
    
    def largescale_variation(scale=60, base=7):
        B = np.array([np.cos( (x / (scale*samples_per_day) * 2*np.pi) * np.random.normal(loc=1, scale=0.3) ) for _ in range(base)])
        v = B.T @ (2*np.random.random(size=base) - 1)
        return v / abs(v).max() 

    def map_to_range(x, mid, half_width):
        return x * half_width + mid

    x = np.arange(n)
    day_scale = np.sin(x / samples_per_day * 2*np.pi) 
    y = map_to_range(day_scale, mid=day_mid, half_width=day_range/2) \
        + map_to_range(largescale_variation(), mid=0, half_width=largescale_range/2)
    return y


def mock_time_generator():
    delta_t = timedelta(minutes=sample_period)
    now = datetime.datetime.now()
    t = now # datetime.datetime(year=now.year, month=now.month, day=now.day, hour=6)
    while True:
        yield t
        t += delta_t


def mock_data_generator():
    """
    Generator for mock sensor data. 
    """
    from itertools import count, cycle

    n = max_iter
    temp     = {mac: mock_timeseries(int(n), day_mid=15 + np.random.normal(scale=5), day_range=10, largescale_range=5) for mac in mac_to_name}
    pressure = {mac: mock_timeseries(int(n), day_mid=1000 + np.random.normal(scale=100), day_range=100, largescale_range=20) for mac in mac_to_name}
    humidity = {mac: mock_timeseries(int(n), day_mid=40 + np.random.normal(scale=10), day_range=20, largescale_range=20) for mac in mac_to_name}

    index = cycle(range(int(n)))
    while True:
        i = next(index)
        yield {mac: { 'identifier': 'w', 
                      'pressure': pressure[mac][i], 
                      'temperature': temp[mac][i], 
                      'humidity': humidity[mac][i]} for mac in mac_to_name}

mock_data = mock_data_generator()
mock_time = mock_time_generator()


def capitalize(str):
    return str[0].upper() + str[1:]


def process_records_dataset():

    print('processing result')

    print('tables', db.tables)
    print('columns', db['measurements'].columns)
    print('rows', len(db['measurements']))
    print('sensors', [name for name in measurements.distinct('sensor_name')])
    # strftime('%d', timestamp) AS day
    if False:
        sql = "SELECT * FROM measurements WHERE sensor_name='First'"
        result = db.query(sql)
        print(pd.DataFrame([r for r in result]).head(10))
    else:
        result = db.query("SELECT timestamp, sensor_name, temperature FROM measurements")
        df = pd.DataFrame([r for r in result]).pivot_table(index='timestamp', columns='sensor_name', values='temperature')
        print(df.head(20))
    #for row in result:
    #    print(row)

def process_records(records):

    SMALL_SIZE = 8
    MEDIUM_SIZE = 10
    BIGGER_SIZE = 12
    plt.rc('font', size=SMALL_SIZE)          # controls default text sizes

    df = pd.DataFrame(records) #.set_index(['timestamp','name'])
    for metric in ['temperature', 'pressure', 'humidity']:
        df_metric = pd.pivot_table(df.rename(columns={'name': 'Sensor'}), 
            index='timestamp', 
            columns='Sensor', 
            values=metric)
        if True: # export CSV
            df_metric.to_csv("static/%s.csv" % metric)
            print('exported to csv')
    print('DONE', len(records), df.shape)


def get_sensor_data(timeout, mock=True):
    if mock: 
        datas = next(mock_data)
        t = next(mock_time)
    else: 
        datas = RuuviTagSensor.get_data_for_sensors(mac_to_name, timeout)
        t = datetime.datetime.now()
    t_str = t.strftime('%Y-%m-%d %H:%M:%S')     
    for mac in mac_to_name:
        if mac in datas:
            record = {'sensor_MAC': mac, 
                      'sensor_name': mac_to_name[mac], 
                      'timestamp': t_str, 
                      'missing': False,
                      **datas[mac]}
        else:
            record = {'sensor_MAC': mac, 
                      'sensor_name': mac_to_name[mac], 
                      'timestamp': t_str, 
                      'missing': True}
        #records.append(record)
        measurements.insert(record)


def repeat(freq_sec, function, *args, **kwargs):

    starttime = time.time()
    for i in range(int(max_iter)):
        if i%samples_per_day==0:
            print('tick %03d' % i)
        function(*args, **kwargs)
        if freq_sec>0:
            time.sleep(freq_sec - ((time.time() - starttime) % freq_sec))

    process_records_dataset()
    exit()


def func():
    print('called')

db = dataset.connect('sqlite:///measurements.db')
measurements = db['measurements']

repeat(0, get_sensor_data, timeout=update_every_n_sec*0.75)
