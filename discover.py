from datetime import datetime
from ruuvi import RuuviTagSensor
from os import path
import yaml


def discover_sensors():
    seen_macs = set()
    n_macs_last_seen = [0]
    sensor_names = yaml.load(open('sensors.yml')) if path.exists('sensors.yml') else {}

    def handle_data(data_list):
        mac, data = data_list
        seen_macs.add(mac)
        if len(seen_macs) != n_macs_last_seen[0]:
            n_macs_last_seen[0] = len(seen_macs)
            print()
            print('Seeing Ruuvi MACS:')
            for mac in sorted(seen_macs):
                print('mac <<>> %s' % sensor_names[mac] if mac in sensor_names else '%s (!)' % mac)

    print('Looking for Ruuvi tags...')
    RuuviTagSensor.get_datas(handle_data)


def flood_data():
    def handle_data(data_list):
        mac, data = data_list
        record = {'MAC': mac, 'timestamp': datetime.now()}
        record.update(data)
        print(record)
        print()

    print('Flooding console with Ruuvi tag data...')
    RuuviTagSensor.get_datas(handle_data)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--flood', action='store_true',
                        help='print sensor readout of all discovered Ruuvis')
    args = parser.parse_args()

    if args.flood:
        flood_data()
    else:
        discover_sensors()
