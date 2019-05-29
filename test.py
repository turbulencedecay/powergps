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
from geopy.distance import geodesic
import matplotlib.pyplot as plt
#import scipy as sc
#from scipy import optimize

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
            point['Position_LatitudeDegrees'] = tp.Position.LatitudeDegrees.text
            point['Position_LongitudeDegrees'] = tp.Position.LongitudeDegrees.text
        else:
            point['Position_LatitudeDegrees'] = float('nan')
            point['Position_LongitudeDegrees'] = float('nan')
        if hasattr(tp, 'HeartRateBpm'):
            point['HeartRateBpm_Value'] = tp.HeartRateBpm.Value.text
        else:
            point['HeartRateBpm_Value'] = float('nan')
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
#tcxData = tcxData.fillna(value=-1)
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

tcxData = tcxData.drop('heart_rate', axis=1) # empty, footpod
tcxData = tcxData.drop('position_lat', axis=1) # empty, footpod
tcxData = tcxData.drop('position_long', axis=1) # empty, footpod
tcxData = tcxData.drop('speed', axis=1) #speed in m/h
tcxData = tcxData.drop('enhanced_speed', axis=1) #speed in km/h
tcxData = tcxData.drop('distance', axis=1) #distance in km
tcxData = tcxData.drop('cadence', axis=1) # footpod cadence
tcxData = tcxData.drop('altitude', axis=1) # what the hell is this, footpod

#   fill missing AltitudeMeters
tcxData.AltitudeMeters=tcxData.AltitudeMeters.fillna(method='backfill')

#   fill missing DistanceMeters
tcxData.DistanceMeters=tcxData.DistanceMeters.interpolate(method='linear', limit_area='inside')
tcxData.DistanceMeters=tcxData.DistanceMeters.interpolate(method='linear', limit_area='outside')

#   fill missing AltitudeMeters
tcxData.Position_LongitudeDegrees=tcxData.Position_LongitudeDegrees.interpolate(method='linear', limit_area='inside')
tcxData.Position_LongitudeDegrees=tcxData.Position_LongitudeDegrees.interpolate(method='linear', limit_area='outside')
tcxData.Position_LatitudeDegrees=tcxData.Position_LatitudeDegrees.interpolate(method='linear', limit_area='inside')
tcxData.Position_LatitudeDegrees=tcxData.Position_LatitudeDegrees.interpolate(method='linear', limit_area='outside')



def GetPace():
    # speed in m/s
    decimalPace = 1000 / tcxData.Speed.get_values() # min/km
    decimalPace[decimalPace == np.inf] = 0
    minutes, seconds = divmod(decimalPace, 60)
    paceElements = np.array((np.abs(minutes),np.round(seconds)))
    return paceElements.T

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
#    plt.plot_date(tcxData.index, tcxData.enhanced_altitude, 'r-')
#    plt.plot_date(tcxData.index, tcxData.AltitudeMeters, 'b-')
#    factor=(tcxData.enhanced_altitude-tcxData.AltitudeMeters).mean()
#    plt.plot(tcxData.enhanced_altitude.get_values()-factor, 'r-')
#    plt.plot(tcxData.AltitudeMeters.get_values(), 'b-')
#    plt.plot(tcxData.power.get_values()/100, 'b-')
#    plt.plot(tcxData.Speed.get_values(), 'r-')
#    plt.show()
#    plt.xlim(['2019-05-05 07:00:00+00:00', '2019-05-05 07:30:00+00:00'])
#    a=GetPace()
#    pass
    firstLat = tcxData.Position_LatitudeDegrees[0::2].get_values()
    secondLat = tcxData.Position_LatitudeDegrees[1::2].get_values()
    firstLon = tcxData.Position_LongitudeDegrees[0::2].get_values()
    secondLon = tcxData.Position_LongitudeDegrees[1::2].get_values()
    firsts = np.array((firstLat, firstLon))
    seconds = np.array((secondLat, secondLon))
    d=[]
    sum=0
    for a,b in zip(firsts.T, seconds.T):
        sum +=geodesic(a, b).meters
        d.append(sum)
    d=np.array(d)
    plt.plot(tcxData.distance.get_values(),'-')
    plt.plot(tcxData.DistanceMeters.get_values(), '-')
    plt.show()
#for item in 1