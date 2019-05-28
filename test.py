# -*- coding: utf-8 -*-
"""
Created on Sat May 11 01:24:26 2019

@author: 49176
"""

# -*- coding: utf-8 -*-

import fitparse, dateutil, pytz
from lxml import objectify
import pandas as pd
import numpy as np
#import geopy.distance
import matplotlib.pyplot as plt
#import scipy as sc
#from scipy import optimize
#from scipy import signal

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

#   magic number warning
delta = pd.Timedelta(30,'s')

resampledFitData.index = resampledFitData.index - delta

resampledFitData = resampledFitData[(resampledFitData.index >= min(tcxData.index)) & (resampledFitData.index <= max(tcxData.index))]

tcxData.index = tcxData.index.round('s')
resampledFitData = resampledFitData.loc[tcxData.index]

for item in(resampledFitData.columns):
    tcxData = tcxData.join(resampledFitData[item])

tcxData = tcxData.drop('heart_rate', axis=1) # empty
tcxData = tcxData.drop('position_lat', axis=1) # empty
tcxData = tcxData.drop('position_long', axis=1) # empty
tcxData = tcxData.drop('speed', axis=1) #speed in m/h
#tcxData = tcxData.drop('Speed', axis=1) #speed in m/s
tcxData = tcxData.drop('enhanced_speed', axis=1) #speed in km/h
tcxData = tcxData.drop('distance', axis=1) #distance in km

def GetPace():
    # speed in m/s
    decimalPace = 1000 / tcxData.Speed.get_values() # min/km
    decimalPace[decimalPace == np.inf] = 0
    minutes, seconds = divmod(decimalPace, 60)
    return (minutes,seconds)

#y1 = np.vstack((tcxTime.get_values(), tcxData.Cadence.get_values()))
#y2 = np.vstack((fitTime.get_values(), resampledFitData.cadence.get_values()))
#
#maxLen = 100
#
#y1 = y1.T[:maxLen].T
#y2 = y2.T[:maxLen].T
#
#y1Filtered = sc.ndimage.filters.gaussian_filter1d(y1[1],3)
#y2Filtered = sc.ndimage.filters.gaussian_filter1d(y2[1],3)
#
#maxTimeShift = 0
#bestShift = 0
#for shift in range(-maxLen, maxLen):
#    timeShift = (np.roll(y1Filtered, shift) * y2Filtered).sum()
#    if timeShift > maxTimeShift:
#        maxTimeShift = timeShift
#        bestShift = shift
#
#bestShift=bestShift-2

if __name__ == '__main__':
#    plt.plot_date(tcxData.index, tcxData.Speed, 'r-')
#    plt.plot_date(tcxData.index, tcxData.speed/1000, 'b-')
#    plt.show()
#    plt.xlim(['2019-05-05 07:00:00+00:00', '2019-05-05 07:30:00+00:00'])
#    a=GetPace()
    pass
#
