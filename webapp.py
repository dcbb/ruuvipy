from flask import Flask, render_template, url_for, request
import pandas as pd
import dataset
import config
import logging

pretty_colors = ["#3366cc", "#dc3912", "#ff9900", "#109618", "#990099", "#0099c6", "#dd4477", "#66aa00", "#b82e2e", "#316395", "#994499", "#22aa99", "#aaaa11", "#6633cc", "#e67300", "#8b0707", "#651067", "#329262", "#5574a6", "#3b3eac"]

app = Flask(__name__)


def dataframe_for_dygraph(df):
    # This is a bit hacky, and it leaves CSV parsing to to the client.
    # Given that the server is a RasPi, this is not unreasonable though.
    # Converting to dygraph array (native) format is a pain, and still just generates a huge string.
    return '"' + '\\n'.join(df.round(2).to_csv().split('\n')) + '"'


def n_pretty_hex_colors(n):
    from itertools import islice, cycle
    return list(islice(cycle(pretty_colors), n))


def sql_date_filter(filter_type):
    assert filter_type[0].isdigit(), 'Filter {filter_type} not recognized. Not starting with a single digit number?'.format(filter_type=filter_type)
    n = int(filter_type[0])
    unit = filter_type[1]
    if unit=='d':
        offset = '-%d days' % (n-1)
    elif unit=='w':
        offset = '-%d days' % (n*7-1)
    elif unit=='m':
        offset = '-%d months' % n
    else:
        raise ValueError('Filter unit in {filter_type} not recognized.').format(filter_type=filter_type)
    print('using offset', offset)
    # TODO replace date with 'now'
    return "datetime(t) >= datetime('2017-12-20', '{offset}')".format(offset=offset)


def to_day_level(data):
    """
    Re-index data to daily minimum and maximum.
    """
    print('converting data to to daily')
    data.index = pd.to_datetime(data.index)
    data = data.resample('d').agg({'max': 'max', 'min': 'min'})
    # collapse hiearchical index to to one title row
    data.columns = [' '.join(col).strip() for col in data.columns.values]
    return data


@app.route('/')
def root_ui():
    sql = """SELECT timestamp AS t, sensor_name, temperature, humidity, pressure
             FROM measurements 
             WHERE [date_filter] """

    return render_data_ui(sql=sql, 
                          metrics=['temperature', 'humidity', 'pressure'])


@app.route('/metric/<metric>')
def metric_ui(metric):
    sql = """SELECT timestamp AS t, sensor_name, {metric}
              FROM measurements 
              WHERE [date_filter]""".format(metric=metric)
    return render_data_ui(sql, 
                          metrics=[metric],
                          show_back_to_all=True)


@app.route('/sensor/<sensor_name>')
def sensor_ui(sensor_name):
    sql = """SELECT timestamp AS t, sensor_name, temperature, humidity, pressure
              FROM measurements 
              WHERE [date_filter]
                AND sensor_name='{sensor_name}' """.format(sensor_name=sensor_name)
    return render_data_ui(sql, 
                          metrics=['temperature', 'humidity', 'pressure'],
                          show_back_to_all=True)


def render_data_ui(sql,
                   metrics, 
                   show_back_to_all=False):

    assert len(metrics)>0, 'No metrics specified to render!'

    db = dataset.connect('sqlite:///measurements.db')

    time_range = request.args.get('range')
    if not time_range:
        time_range = '1w'

    # inject date filter into SQL query
    sql = sql.replace('[date_filter]', sql_date_filter(time_range))
    logging.debug('query and dataframe construction')
    all_data = pd.DataFrame([r for r in db.query(sql)])
    # make sure returned data is consistent with specified metrics
    assert all(metric in all_data.columns for metric in metrics), \
        'The data returned is not consistent with the specified metrics. '\
        + 'Metrics: {metrics}. Data columns: {columns}'.format(metrics=metric, columns=list(all_data.columns))

    logging.debug('data transformation')
    # get names of ALL sensors to allow for consistent coloring, regardless of the sensors currently displayed
    all_sensors = [r['sensor_name'] for r in db.query("SELECT DISTINCT sensor_name FROM measurements ORDER BY sensor_name")]   
    sensor_colors = {sensor: color for sensor, color in zip(all_sensors, n_pretty_hex_colors(len(all_sensors)))}
    
    data_per_metric = {metric: all_data.pivot_table(index='t', columns='sensor_name', values=metric) for metric in metrics}

    # Names of the sensors currently displayed.
    current_sensors = data_per_metric[metrics[0]].columns

    # determine whether to aggregate data to a day level
    aggregate_to_day_level = data_per_metric[metrics[0]].shape[0] > config.aggregate_daily_row_threshold


    # latest single data point for each metric
    latest_data = []
    for sensor in current_sensors:
        record = {'sensor_name': sensor, 
                  'color': sensor_colors[sensor]}
        record.update({metric: data_per_metric[metric][sensor].iloc[-1] for metric in metrics}) 
        latest_data.append(record)


    # history for each metric, CSV formatted to inject into dygraph 
    def csv_data_for_metric(metric):
        if aggregate_to_day_level:
            return dataframe_for_dygraph(to_day_level(data_per_metric[metric]))
        else:
            return dataframe_for_dygraph(data_per_metric[metric])
    graph_data = [ {'metric': metric, 'csv': csv_data_for_metric(metric)} for metric in metrics ]


    # graph options per series are different when data is aggregated on a day level - then we need to
    # differentiate the min and max series visually
    if aggregate_to_day_level:
        series_options = {}
        for sensor_name in current_sensors:
            series_options.update({'max ' + sensor_name: {'color': sensor_colors[sensor_name]}})
            series_options.update({'min ' + sensor_name: {'color': sensor_colors[sensor_name], 'strokePattern': [3,3]}})
    else:
        series_options = {sensor_name : {'color': sensor_colors[sensor_name]} for sensor_name in current_sensors}


    logging.debug('call to render_template')
    return render_template(
        'ui_main.html', 
        metrics=metrics,
        latest_data=latest_data,
        graph_data=graph_data,
        metric_units={'temperature': '°', 'pressure': ' hPa', 'humidity': '%'},
        metric_icons={'temperature': 'thermometer', 'pressure': 'weather-lightning-rainy', 'humidity': 'water'},
        ui_width=480,
        show_back_to_all=show_back_to_all,
        time_range=time_range,
        series_options=series_options
    )

