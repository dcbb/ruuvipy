from datetime import datetime, timedelta
import numpy as np


class SensorMock:
    def __init__(self, mock_days):
        self.mock_sample_period = 1  # minutes
        self.mock_samples_per_day = (24 * 60) / self.mock_sample_period
        self.mock_days = mock_days
        self.max_iter = self.mock_days * self.mock_samples_per_day
        self.mac_to_name = {'dummy_mac_1': 'First',
                            'dummy_mac_2': 'Second',
                            'dummy_mac_3': 'Third'}

    def mock_timeseries(self, n, day_mid, day_range, largescale_range):
        if self.mock_days < 0:
            # simple random walk for "real time" mock
            return np.random.normal(loc=day_mid, scale=day_range, size=1000)
        else:
            def largescale_variation(scale=60, base=7):
                B = np.array(
                    [np.cos((x / (scale * self.mock_samples_per_day) * 2 * np.pi) * np.random.normal(loc=1, scale=0.3))
                     for
                     _ in
                     range(base)])
                v = B.T.dot(2 * np.random.random(size=base) - 1)
                return v / abs(v).max()

            def map_to_range(x, mid, half_width):
                return x * half_width + mid

            x = np.arange(n)
            day_scale = np.sin(x / self.mock_samples_per_day * 2 * np.pi)
            y = map_to_range(day_scale, mid=day_mid, half_width=day_range / 2) \
                + map_to_range(largescale_variation(), mid=0, half_width=largescale_range / 2)
            return y

    def mock_time_generator(self):
        if self.mock_days < 0:
            # real-time mode
            while True:
                yield datetime.utcnow()
        else:
            delta_t = timedelta(minutes=self.mock_sample_period)
            now = datetime.utcnow() - timedelta(days=self.mock_days)
            t = now  # datetime.datetime(year=now.year, month=now.month, day=now.day, hour=6)
            while True:
                yield t
                t += delta_t

    def mock_data_generator(self):
        """
        Generator for mock sensor data. 
        """
        from itertools import count, cycle

        n = self.max_iter if self.mock_days > 0 else 1000
        temp = {
            mac: self.mock_timeseries(int(n),
                                      day_mid=15 + np.random.normal(scale=5),
                                      day_range=10,
                                      largescale_range=5)
            for mac in self.mac_to_name}
        pressure = {
            mac: self.mock_timeseries(int(n),
                                      day_mid=1000 + np.random.normal(scale=100),
                                      day_range=100,
                                      largescale_range=20) for
            mac in self.mac_to_name}
        humidity = {
            mac: self.mock_timeseries(int(n),
                                      day_mid=40 + np.random.normal(scale=10),
                                      day_range=20,
                                      largescale_range=20)
            for mac in self.mac_to_name}

        index = cycle(range(int(n)))
        while True:
            i = next(index)
            yield {mac: {'identifier': 'w',
                         'pressure': pressure[mac][i],
                         'temperature': temp[mac][i],
                         'humidity': humidity[mac][i]} for mac in self.mac_to_name}
