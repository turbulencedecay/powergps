# -*- coding: utf-8 -*-

import fitparse
import tcxparser
import pytz
import dateutil
import lxml.etree as et
from lxml import objectify
import csv
import pandas as pd

UTC = pytz.UTC
BER = pytz.timezone('Europe/Berlin')

fitFileName = 'data/fit/1557035072-GIR.fit'
tcxFileName = 'data/tcx/2019-05-05_07-45-08.tcx'

def GetFitData(fitFileName, timeZone):
	fitFile = fitparse.FitFile(fitFileName, data_processor=fitparse.StandardUnitsDataProcessor())
	fitData = [item.get_values() for item in fitFile.get_messages('record')]
	for item in fitData:
		timestamp = item['timestamp']
		timestamp = UTC.localize(timestamp).astimezone(timeZone)
	return fitData

tree = objectify.parse(tcxFileName)
root = tree.getroot()
ns = 'http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2'
xt = 'http://www.garmin.com/xmlschemas/ActivityExtension/'
activity = root.Activities.Activity

heartRate = [i.text for i in root.xpath('//ns:HeartRateBpm/ns:Value', namespaces={'ns': ns})]
time = [i.text for i in root.xpath('//ns:Time', namespaces={'ns': ns})]
cadence = [i.text for i in root.xpath('//ns:Cadence', namespaces={'ns': ns})]
altitude = [i.text for i in root.xpath('//ns:AltitudeMeters', namespaces={'ns': ns})]
distance = [i.text for i in root.xpath('//ns:DistanceMeters', namespaces={'ns': ns})]
latitude = [i.text for i in root.xpath('//ns:Position/ns:LatitudeDegrees', namespaces={'ns': ns})]
longitude = [i.text for i in root.xpath('//ns:Position/ns:LongitudeDegrees', namespaces={'ns': ns})]
trackpoints = [i.text for i in root.xpath('//ns:Trackpoint', namespaces={'ns': ns})]


