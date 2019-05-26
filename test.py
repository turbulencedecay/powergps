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
from scipy import optimize
from scipy import signal
#from signal_alignment import *

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

y1 = np.vstack((tcxTime.get_values(), tcxData.Cadence.get_values()))
y2 = np.vstack((fitTime.get_values(), resampledFitData.cadence.get_values()))

#maxLen = min(y2.argmax(), y1.argmax())
maxLen = 100

y1 = y1.T[:maxLen].T
y2 = y2.T[:maxLen].T

#corr = np.correlate(y1[1],y2[1],'full')
#position = np.argmax(corr)

y1Filtered = sc.ndimage.filters.gaussian_filter1d(y1[1],3)
y2Filtered = sc.ndimage.filters.gaussian_filter1d(y2[1],3)

maxTimeShift = 0
bestShift = 0
for shift in range(-maxLen, maxLen):
    timeShift = (np.roll(y1Filtered, shift) * y2Filtered).sum()
    if timeShift > maxTimeShift:
        maxTimeShift = timeShift
        bestShift = shift

bestShift=bestShift-2

fitTime = fitTime + bestShift


#def getWindow(X, windowWidth):
#    position = int(len(X.T)/2)
#    return X.T[position-int(windowWidth/2):position+int(windowWidth/2)]

#def err(deltaX):
#    return np.sqrt((y2[0]+deltaX-y1[0])**2 + (y2[1]-y1[1])**2 ).sum()

#initDelta = 0.0
#shiftX = optimize.fmin(err, initDelta)
#shiftX = -70
#y2[0] = y2[0]+shiftX
#delta = pd.Timedelta(dt,'ms')
#fitData.index = fitData.index - delta


plt.plot_date(resampledFitData.index, resampledFitData.cadence, 'r-')
plt.plot_date(tcxData.index, tcxData.Cadence, 'b-')
plt.xlim(['2019-05-05 05:45:00+00:00', '2019-05-05 05:47:00+00:00'])
plt.show()

#plt.plot(y1[0][:100], y1[1][:100], 'r-')
#plt.plot(y2[0][:100], y2[1][:100], 'b-')
#plt.plot(y1[0], y1[1], 'r-')
#plt.plot(y2[0]-abs(bestShift), y2[1], 'g-')
#plt.show()