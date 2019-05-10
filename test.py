# -*- coding: utf-8 -*-

import fitparse, datetime, dateutil, pytz
from lxml import objectify
import pandas as pd
import numpy as np
#import geopy.distance
import matplotlib.pyplot as plt
from scipy import signal


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
tcxData = pd.DataFrame(tcxData)
tcxData = tcxData.fillna(value=-1)
tcxData = tcxData.apply(pd.to_numeric)
tcxData.Time = tcxData.Time.apply(pd.to_datetime)

fitData = fitData.set_index('timestamp')
tcxData = tcxData.set_index('Time')

resampledFitData = fitData.resample('1s').ffill()

#dt = 29600
#f = [fitData.cadence.get_values(), fitData.index.get_values()]
#y = [tcxData.Cadence.get_values(), tcxData.index.get_values()]
#delta = pd.Timedelta(dt,'ms')
#fitData.index = fitData.index - delta

#
#plt.plot_date(fitData.index, fitData.cadence, 'r-')
#plt.plot_date(tcxData.index, tcxData.Cadence, 'b-')
#plt.xlim(['2019-05-05 05:45:00+00:00', '2019-05-05 05:55:00+00:00'])
#plt.show()

