# -*- coding: utf-8 -*-
"""
Created on Sat May 11 01:24:26 2019

@author: 49176
"""

# -*- coding: utf-8 -*-

import fitparse, datetime, dateutil, pytz
from lxml import objectify
import pandas as pd
import numpy as np
#import geopy.distance
import matplotlib.pyplot as plt
import scipy as sc


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

tcxTime = tcxData.index
tcxTime = tcxTime - tcxTime[0]
tcxTime = tcxTime.seconds + tcxTime.microseconds / 1e+6

fitTime = resampledFitData.index
fitTime = fitTime - fitTime[0]
fitTime = fitTime.seconds + fitTime.microseconds / 1e+6

#dt = 29600  # manual best value

y2 = np.vstack((fitTime.get_values(), resampledFitData.cadence.get_values()))
y1 = np.vstack((tcxTime.get_values(), tcxData.Cadence.get_values()))
maxLen = min(y2.argmax(), y1.argmax())
y2 = y2.T[:maxLen]
y1 = y1.T[:maxLen]

y2=y2.T
y1=y1.T
err = np.sqrt(np.square((y2[1]-y1[1]))+np.square((y2[0]-y1[0])))

from scipy.optimize import fmin

p0 = [0,] # Inital guess of no shift
found_shift = fmin(err_func, p0)[0]

#delta = pd.Timedelta(dt,'ms')
#fitData.index = fitData.index - delta


#plt.plot_date(resampledFitData.index, resampledFitData.cadence, 'r-')
#plt.plot_date(tcxData.index, tcxData.Cadence, 'b-')
#plt.xlim(['2019-05-05 05:45:00+00:00', '2019-05-05 05:47:00+00:00'])
#plt.show()

