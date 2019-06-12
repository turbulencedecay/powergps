# -*- coding: utf-8 -*-
"""
Created on Sat May 11 01:24:26 2019

@author: 49176
"""

# -*- coding: utf-8 -*-

import fitparse, dateutil, pytz
from datetime import datetime
from lxml import objectify
import pandas as pd
import numpy as np
from scipy import interpolate
#from geopy.distance import geodesic
#import matplotlib.pyplot as plt
import xml.etree.ElementTree as ET

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
tcxData = tcxData.apply(pd.to_numeric)
tcxData.Time = tcxData.Time.apply(pd.to_datetime)

fitData = fitData.set_index('timestamp')
tcxData = tcxData.set_index('Time')

resampledFitData = fitData.resample('1s').ffill()

#   magic number warning add minimum fitting procedure
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

#   fill missing Latitudes / Longitudes
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

def SplitIntoLaps(distance=1000):
    laps = []
    numberOfLaps = int(max(tcxData.DistanceMeters)/distance) + 1
    
    for i in range(numberOfLaps):
        lap = tcxData[(tcxData.DistanceMeters>=i*distance) & (tcxData.DistanceMeters<=(i+1)*distance)]
        lap = lap.reset_index()
        laps.append(lap)
    
    splits = []
    for i in range(len(laps)-1):
        lap = laps[i]
        if lap.iloc[-1].DistanceMeters % distance == 0:
            splitTime = lap.iloc[-1].Time.timestamp()
            splitTime = datetime.fromtimestamp(splitTime)
            splitTime = BER.localize(splitTime).astimezone(UTC)
            splitDistance = lap.iloc[-1].DistanceMeters
        else:
            splitDistance = float((i+1) * distance)
            previousLap = lap
            actualLap = laps[i+1]
            previousLap_ = previousLap.iloc[-1:]
            previousLap_.Time = [x.timestamp() for x in previousLap_.Time]
            actualLap_ = actualLap.iloc[:1]
            actualLap_.Time = [x.timestamp() for x in actualLap_.Time]
            x = np.array([previousLap_.DistanceMeters.get_values(), actualLap_.DistanceMeters.get_values()]).flatten()
            y = np.array([previousLap_.Time.get_values(), actualLap_.Time.get_values()]).flatten()
            f = interpolate.interp1d(x,y)
            splitTime_ = f(splitDistance)
            splitTime = datetime.fromtimestamp(splitTime_, UTC)
        splits.append([splitTime, splitDistance])
    
    for i in range(len(laps)-1):
        cadence = round(laps[i]['Cadence'].mean())
        heartRate = round(laps[i]['HeartRateBpm_Value'].mean())
        formPower = round(laps[i]['Form Power'].mean())
        legSpringStiffness = laps[i]['Leg Spring Stiffness'].mean()
        speed = laps[i]['Speed'].mean()
        power = round(laps[i]['power'].mean())
        stanceTime = round(laps[i]['stance_time'].mean())
        verticalOscillation = laps[i]['vertical_oscillation'].mean()
    return splits
    
#def WriteComplete():
#    root = ET.Element('TrainingCenterDatabase')
#    root.set(
#            'xsi:schemaLocation',
#            ' '.join([
#                    'http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2',
#                    'http://www.garmin.com/xmlschemas/TrainingCenterDatabasev2.xsd',
#                    ])
#            )
#    root.set('xmlns', 'http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2')
#    root.set('xmlns:xsi', 'http://www.w3.org/2001/XMLSchema-instance')
#    
#    initTime = tcxData.index[0].isoformat() + 'Z'
#    
#    activities = ET.SubElement(root, 'Activities')
#    activity = ET.SubElement(activities, 'Activity')
#    activity.set('Sport', 'Running')
#    activity_id = ET.SubElement(activity, 'Id')
#    activity_id.text = initTime
#    activities = ET.SubElement(root, 'Activities')
#    
#    lap = ET.SubElement(activity, 'Lap')
#    lap.set('StartTime', initTime)
#    total_time = ET.SubElement(lap, 'TotalTimeSeconds')
#    total_time.text = '1'
#    intensity = ET.SubElement(lap, 'Intensity')
#    intensity.text = 'Active'
#
#    track = ET.SubElement(lap, 'Track')
#    trackpoint = ET.SubElement(track, 'Trackpoint')
#    time = ET.SubElement(trackpoint, 'Time')
#    time.text = now
#    position = ET.SubElement(trackpoint, 'Position')
#    latitude = ET.SubElement(position, 'LatitudeDegrees')
#    latitude.text = '{:.1f}'.format(random.uniform(-90.0, 90.0))
#    longitude = ET.SubElement(position, 'LongitudeDegrees')
#    longitude.text = '{:.1f}'.format(random.uniform(-180.0, 180.0))
#    altitude = ET.SubElement(trackpoint, 'AltitudeMeters')
#    altitude.text = '{}'.format(random.randrange(0, 4000))
#    distance = ET.SubElement(trackpoint, 'DistanceMeters')
#    distance.text = '0'
#    heart_rate = ET.SubElement(trackpoint, 'HeartRateBpm')
#    heart_rate.text = '{}'.format(random.randrange(60, 180))
#
#    print('<?xml version="1.0" encoding="UTF-8"?>')
#    ET.dump(root)


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
    splitData = SplitIntoLaps()
#    pre = laps[0]
#    act = laps[1]
#    pre_ = pre.iloc[-1:]
#    pre_.Time = [x.timestamp() for x in pre_.Time]
#    act_ = act.iloc[:1]
#    act_.Time = [x.timestamp() for x in act_.Time]
#    ins_ = inserts[0].T
#    int_ = pd.concat(objs=(pre_, ins_, act_))
#    int_ = int_.reset_index()
#    int_ = int_.drop(['index'], axis=1)
#    x = np.array([pre_.DistanceMeters.get_values(), act_.DistanceMeters.get_values()]).flatten()
#    y = np.array([pre_.Time.get_values(), act_.Time.get_values()]).flatten()
#    f = interpolate.interp1d(x,y)
#    int_.Time.iloc[1] = f(inserts[0].T.DistanceMeters.get_values()[0])
#    int_.Time = [datetime.fromtimestamp(x) for x in int_.Time]
    pass