# -*- coding: utf-8 -*-
"""
Created on Sat May 11 01:24:26 2019

@author: 49176
"""

# -*- coding: utf-8 -*-

import fitparse, dateutil, pytz, random
from datetime import datetime
from lxml import objectify
import pandas as pd
import numpy as np
import scipy as sc
#from geopy.distance import geodesic
#import matplotlib.pyplot as plt
import xml.etree.ElementTree as ET
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
            splitTime = datetime.utcfromtimestamp(splitTime).strftime('%Y-%m-%d %H:%M:%S.%f')
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
            f = sc.interpolate.interp1d(x,y)
            splitTime_ = f(splitDistance)
            splitTime = datetime.utcfromtimestamp(splitTime_).strftime('%Y-%m-%d %H:%M:%S.%f')
        cadence = round(laps[i]['Cadence'].mean())
        heartRate = round(laps[i]['HeartRateBpm_Value'].mean())
        maxHeartRate = round(laps[i]['HeartRateBpm_Value'].max())
        formPower = round(laps[i]['Form Power'].mean())
        legSpringStiffness = laps[i]['Leg Spring Stiffness'].mean()
        speed = laps[i]['Speed'].mean()
        power = round(laps[i]['power'].max())
        stanceTime = round(laps[i]['stance_time'].mean())
        verticalOscillation = laps[i]['vertical_oscillation'].mean()
        
        splits.append([splitDistance, 
                       splitTime,
                       cadence,
                       heartRate,
                       maxHeartRate,
                       formPower,
                       legSpringStiffness,
                       speed,
                       power,
                       stanceTime,
                       verticalOscillation])
    return splits, laps
    
def WriteComplete(splits, laps):
    root = ET.Element('TrainingCenterDatabase')
    root.set('xmlns', 'http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2')
#    root.set(
#            'xsi:schemaLocation',
#            ' '.join([
#                    'http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2',
#                    'http://www.garmin.com/xmlschemas/TrainingCenterDatabasev2.xsd',
#                    ])
#            )
#    root.set('xmlns:xsi', 'http://www.w3.org/2001/XMLSchema-instance')
    activities = ET.SubElement(root, 'Activities')
    activity = ET.SubElement(activities, 'Activity')
    activity.set('Sport', 'Running')
    activityId = ET.SubElement(activity, 'Id')

    for i in range(len(splits)):
        if i == 0:
            startTime = laps[i].iloc[0].Time.isoformat() + 'Z'
        else:
            time_ = datetime.strptime(splits[i][1], '%Y-%m-%d %H:%M:%S.%f')
            startTime = time_.isoformat() + 'Z'
        
        activityId.text = startTime
        lap = ET.SubElement(activity, 'Lap')
        lap.set('StartTime', startTime)
        
        totalTime = ET.SubElement(lap, 'TotalTimeSeconds')
        delta = laps[i].iloc[-1].Time - laps[i].iloc[0].Time
        totalTime.text = str(delta.seconds)
        
        distance = ET.SubElement(lap, 'DistanceMeters')
        distance.text = str(splits[i][0])
        
        maximumSpeed = ET.SubElement(lap, 'MaximumSpeed')
        maximumSpeed.text = str(splits[i][7])
        
#        calories = ET.SubElement(lap, 'Calories')
#        calories.text = '507'
        
        avgHeartRate = ET.SubElement(lap, 'AverageHeartRateBpm')
        avgHeartRateValue = ET.SubElement(avgHeartRate, 'Value')
        avgHeartRateValue.text = str(splits[i][3])
        
        maxHeartRate = ET.SubElement(lap, 'MaximumHeartRateBpm')
        maxHeartRateValue = ET.SubElement(maxHeartRate, 'Value')
        maxHeartRateValue.text = str(splits[i][4])
        
        intensity = ET.SubElement(lap, 'Intensity')
        intensity.text = 'Active'
        
        cadence = ET.SubElement(lap, 'Cadence')
        cadence.text = str(splits[i][2])
        
        triggerMethod = ET.SubElement(lap, 'TriggerMethod')
        triggerMethod.text = 'Distance'
        
        track = ET.SubElement(lap, 'Track')
        for j in range(len(laps[i])):
            trackpoint = ET.SubElement(track, 'Trackpoint')
            
            time = ET.SubElement(trackpoint, 'Time')
            time.text = str(laps[i].iloc[j].Time)
            
            position = ET.SubElement(trackpoint, 'Position')
            latitude = ET.SubElement(position, 'LatitudeDegrees')
            latitude.text = str(laps[i].iloc[j].Position_LatitudeDegrees)
            longitude = ET.SubElement(position, 'LongitudeDegrees')
            longitude.text = str(laps[i].iloc[j].Position_LongitudeDegrees)
            
            altitude = ET.SubElement(trackpoint, 'AltitudeMeters')
            altitude.text = str(laps[i].iloc[j].AltitudeMeters)
            
            distance = ET.SubElement(trackpoint, 'DistanceMeters')
            distance.text = str(laps[i].iloc[j].DistanceMeters)
            
            heartRateBpm = ET.SubElement(trackpoint, 'HeartRateBpm')
            heartRateBpmValue = ET.SubElement(heartRateBpm, 'Value')
            heartRateBpmValue.text = str(laps[i].iloc[j].HeartRateBpm_Value)
            
            cadence = ET.SubElement(trackpoint, 'Cadence')
            cadence.text = str(laps[i].iloc[j].Cadence)
            
            sensorState = ET.SubElement(trackpoint, 'SensorState')
            sensorState.text = 'Present'
#    print('<?xml version="1.0" encoding="UTF-8"?>')
#    ET.dump(root)
    tree = ET.ElementTree(root)
    tree.write('out.xml')


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
    splitData, lapData = SplitIntoLaps()
    WriteComplete(splitData, lapData)
    pass