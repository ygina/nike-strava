#!/usr/bin/env python
import datetime
import json
import os
import sys
from typing import List


def to_datetime(time_ms: int) -> str:
    dt = datetime.datetime.fromtimestamp(time_ms // 1000)
    return "{}T{}Z".format(str(dt.date()), str(dt.time()))


class TRKPoint:
    def __init__(self, time: int, lat = None, lon = None, ele = None):
        self.time = time
        self.lat = lat
        self.lon = lon
        self.ele = ele

    def __str__(self):
        return """<trkpt lat="{}" lon="{}">
    <ele>{}</ele>
    <time>{}</time>
   </trkpt>
   """.format(self.lat, self.lon, self.ele, to_datetime(self.time))


def validate(filename: str, data) -> bool:
    """Might have data from NTC or manual entries"""
    if data['type'] != 'run':
        print("{} (not a run)".format(filename))
        return False
    for x in data['summaries']:
        if x['metric'] == 'distance' and x['source'] == 'com.nike.running.ios.manualentry':
            print("{} (manual entry)".format(filename))
            return False
    return True


def to_gpx(data):
    name = data['tags']['com.nike.name']
    start_time = to_datetime(data['start_epoch_ms'])

    for metric in data['metrics']:
        if metric['type'] == 'latitude':
            lat_values = metric['values']
        if metric['type'] == 'longitude':
            lon_values = metric['values']
        if metric['type'] == 'elevation':
            ele_values = metric['values']

    points = []
    for i in range(len(lat_values)):
        lat = lat_values[i]
        lon = lon_values[i]
        assert lat['start_epoch_ms'] == lon['start_epoch_ms']
        point = TRKPoint(time = lat['start_epoch_ms'], lat = lat['value'], lon = lon['value'])
        points.append(point)

    # there isn't a one-to-one correspondence between elevation and lat/lon points
    j = 0
    for i in range(len(points)):
        point_time = points[i].time
        while True:
            if ele_values[j]['start_epoch_ms'] >= point_time:
                points[i].ele = ele_values[j]['value']
                break
            else:
                j += 1

    return """<?xml version="1.0" encoding="UTF-8"?>
<gpx creator="NRC to Strava" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd" version="1.1" xmlns="http://www.topografix.com/GPX/1/1">
 <metadata>
  <time>{}</time>
 </metadata>
 <trk>
  <name>{}</name>
  <type>9</type>
  <trkseg>
   {}</trkseg>
 </trk>
</gpx>
""".format(start_time, name, "".join([str(point) for point in points]))


def handle_file(filename: str) -> bool:
    try:
        with open(filename) as f:
            data = json.loads(f.read())
        if validate(filename, data):
            gpx = to_gpx(data)
            out = os.path.join('gpx', os.path.splitext(os.path.basename(filename))[0] + '.gpx')
            with open(out, 'w') as f:
                f.write(gpx)
        return False
    except Exception as e:
        return True


if len(sys.argv) > 2:
    print('USAGE: python3 json_to_gpx.py [NIKE_JSON]?')
    exit()
elif len(sys.argv) == 2:
    handle_file(sys.argv[1])
else:
    res = input('Convert all activities in json/? [y/n] ')
    if res != 'y':
        exit()
    filenames = [os.path.join('json', filename) for filename in os.listdir('json')]
    failed = []
    for filename in filenames:
        if handle_file(filename):
            failed.append(filename)
    for fail in failed:
        print('FAILED: ' + fail)
