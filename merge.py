# -*- coding: utf-8 -*-

import fitparse
import tcxparser
import pytz
import dateutil
import lxml.etree as et
import csv
import pandas as pd

UTC = pytz.UTC
BER = pytz.timezone('Europe/Berlin')

fitFileName = 'data/fit/1557035072-GIR.fit'
tcxFileName = 'data/tcx/2019-05-05_07-45-08.tcx'

# def writeCSV(outFileName, data):
#     with open(outFileName, 'w') as f:
#         writer = csv.writer(f)
#         writer.writerow([k for k in data[-1].keys()])
#         for entry in data:
#             writer.writerow(entry.values())

def fit2CSV(fitFileName, outFileName, timeZone):
    fitFile = fitparse.FitFile(fitFileName, data_processor=fitparse.StandardUnitsDataProcessor())
    fitData = [i.get_values() for i in fitFile.get_messages('record')]
    for item in fitData:
        item['timestamp'] = UTC.localize(item['timestamp']).astimezone(timeZone)
    return fitData

def tcx2CSV(tcxFileName, outFileName, timeZone):
    tree = et.parse(tcxFileName)
    root = tree.getroot()
    ns1 = 'http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2'
    timePointsData = []
    for element in root.iter():
        if element.tag == '{%s}Trackpoint'%ns1:
            children =  element.getchildren()
            values = {}
            
            altitudePresent = False
            for child in children:
                if child.tag == '{%s}AltitudeMeters'%ns1:
                    altitudePresent = True
            
            for child in children:
                if child.tag =='{%s}Time'%ns1:
                    timePoint = child.text
                    timePoint = dateutil.parser.parse(timePoint[:19])
                    timePoint = UTC.localize(timePoint).astimezone(timeZone)
                    values[child.tag[len(ns1)+2:]] = timePoint
                elif child.tag == '{%s}Position'%ns1:
                    for child2 in child.getchildren():
                        values[child2.tag[len(ns1)+2:]] = child2.text
                elif not altitudePresent:
                    values['AltitudeMeters'] = 0.0
                elif child.tag == '{%s}AltitudeMeters'%ns1 and altitudePresent:
                    values['AltitudeMeters'] = child.text
                else:
                    pass
            
            for child in children:
                if child.tag =='{%s}HeartRateBpm'%ns1:
                    for child2 in child.getchildren():
                        values['HeartRateBpm'] = child2.text
                elif child.tag =='{%s}Cadence'%ns1:
                    values[child.tag[len(ns1)+2:]] = child.text
            
            for child in children:
                if child.tag =='{%s}DistanceMeters'%ns1:
                    values[child.tag[len(ns1)+2:]] = child.text
            
            timePointsData.append(values)
    
    writeCSV(outFileName=outFileName, data=timePointsData)

fit2CSV(fitFileName=fitFileName, outFileName=fitOutFileName, timeZone=UTC)
tcx2CSV(tcxFileName=tcxFileName, outFileName=tcxOutFileName, timeZone=UTC)

dfFootpod = pd.read_csv(fitOutFileName, delimiter=',', header=0)
dfWatch = pd.read_csv(tcxOutFileName, delimiter=',', header=0)
mask = (dfFootpod['timestamp'] >= dfWatch['Time'].iloc[0]) & (dfFootpod['timestamp'] <= dfWatch['Time'].iloc[-1])
dfFootpod = dfFootpod[mask]

dfFootpod.timestamp = pd.to_datetime(dfFootpod.timestamp, utc=True)
dfFootpod = dfFootpod.set_index('timestamp')
dfWatch.Time = pd.to_datetime(dfWatch.Time, utc=True)
dfWatch = dfWatch.set_index('Time')

resampled = dfFootpod.resample('1S').asfreq()
dfFootpodInterp = resampled.interpolate(method='linear')

completeData = pd.concat([dfWatch, dfFootpodInterp], axis=1)
completeData = completeData.drop(['position_lat', 'position_long', 'distance', 'heart_rate', 'enhanced_speed', 'cadence', 'enhanced_altitude', 'altitude', 'speed', 'Distance', 'Speed'], axis=1)
completeData = completeData.fillna(0)

#   time vs power vs heartrate
#fig, ax1 = plt.subplots()
#color = 'tab:red'

#ax1.set_xlabel('Time (s)')
#ax1.set_ylabel('Heart Rate', color=color)
#ax1.plot_date(completeData.index, completeData['Cadence'], '-', color=color)
#ax1.tick_params(axis='y', labelcolor=color)

#ax2 = ax1.twinx()  # instantiate a second axes that shares the same x-axis

#color = 'tab:blue'
#ax2.set_ylabel('Power (W)', color=color)  # we already handled the x-label with ax1
#ax1.plot_date(completeData.index, completeData['power'], '-', color=color)
#ax2.tick_params(axis='y', labelcolor=color)

#fig.tight_layout()  # otherwise the right y-label is slightly clipped
#plt.show()
#plt.plot_date(completeData.index, completeData['power'], '-')
#plt.show()
#
##   time vs hr
#plt.plot_date(completeData.index, completeData['HeartRateBpm'], '-')
#plt.show()
#
##   time vs distance
#plt.plot_date(completeData.index, completeData['vertical_oscillation'], '-')
#plt.show()
#
##   time vs cadence
#plt.plot_date(completeData.index, completeData['Cadence'], '-')
#plt.show()