# -*- coding: utf-8 -*-

import fitparse
import pytz
from lxml import objectify
import dateutil
import pandas as pd
#import geopy.distance
import matplotlib.pyplot as plt

UTC = pytz.UTC
BER = pytz.timezone('Europe/Berlin')

fitFileName = 'data/fit/1557035072-GIR.fit'
tcxFileName = 'data/tcx/2019-05-05_07-45-08.tcx'

def GetTcxData(tcxFileName):
    tree = objectify.parse(tcxFileName)
    root = tree.getroot()
    ns = 'http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2'
    trackpoints = [i for i in root.xpath('//ns:Trackpoint', namespaces={'ns': ns})]
    tcxData = []
    for tp in trackpoints:
        point = {}
        attributes = ['Time', 'AltitudeMeters', 'Cadence', 'DistanceMeters']
        for item in attributes:
            if hasattr(tp, item):
                point[item] = tp[item].text
            else:
                point[item] = float('nan')
        if hasattr(tp, 'Position'):
            point['Position.LatitudeDegrees'] = tp.Position.LatitudeDegrees.text
            point['Position.LongitudeDegrees'] = tp.Position.LongitudeDegrees.text
        else:
            point['Position.LatitudeDegrees'] = float('nan')
            point['Position.LongitudeDegrees'] = float('nan')
        if hasattr(tp, 'HeartRateBpm'):
            point['HeartRateBpm.Value'] = tp.HeartRateBpm.Value.text
        else:
            point['HeartRateBpm.Value'] = float('nan')
        tcxData.append(point)
    for item in tcxData:
        item['Time'] = dateutil.parser.parse(item['Time'])
    return tcxData

def GetFitData(fitFileName, timeZone=None):
    fitFile = fitparse.FitFile(fitFileName, data_processor=fitparse.StandardUnitsDataProcessor())
    fitData = [item.get_values() for item in fitFile.get_messages('record')]
    if timeZone:
        for item in fitData:
            item['timestamp'] = timeZone.localize(item['timestamp']).astimezone(timeZone)
    return fitData

tcxData = GetTcxData(tcxFileName)
fitData = GetFitData(fitFileName)

fitData = pd.DataFrame(fitData)
fitData.timestamp = fitData.timestamp.apply(pd.to_datetime)
tcxData = pd.DataFrame(tcxData)
tcxData = tcxData.fillna(value=-1)
tcxData = tcxData.apply(pd.to_numeric)
tcxData.Time = tcxData.Time.apply(pd.to_datetime)

a=fitData.timestamp[5]
b=tcxData.Time[5]
c=b-a
fitData.timestamp = fitData.timestamp - c

plt.plot_date(fitData.timestamp, fitData.cadence, '-')
plt.plot_date(tcxData.Time, tcxData.Cadence, '-')
#plt.xlim(['2019-05-05 05:45:00+00:00', '2019-05-05 05:50:08+00:00'])
plt.show()

