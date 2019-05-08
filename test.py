# -*- coding: utf-8 -*-

import fitparse
import tcxparser
import pytz
from lxml import objectify
import dateutil
import pandas as pd

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
			point['Position.LatitudeDegrees'] = tp.Position.LatitudeDegrees
			point['Position.LongitudeDegrees'] = tp.Position.LongitudeDegrees
		else:
			point['Position.LatitudeDegrees'] = float('nan')
			point['Position.LongitudeDegrees'] = float('nan')
		if hasattr(tp, 'HeartRateBpm'):	
			point['HeartRateBpm.Value'] = tp.HeartRateBpm.Value
		else:
			point['HeartRateBpm.Value'] = float('nan')
		tcxData.append(point)
	for item in tcxData:
		item['Time'] = dateutil.parser.parse(item['Time]'])
	return tcxData

def GetFitData(fitFileName, timeZone):
	fitFile = fitparse.FitFile(fitFileName, data_processor=fitparse.StandardUnitsDataProcessor())
	fitData = [item.get_values() for item in fitFile.get_messages('record')]
	for item in fitData:
		item['timestamp'] = timeZone.localize(item['timestamp']).astimezone(timeZone)
	return fitData
