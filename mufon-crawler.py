from datetime import datetime
from geopy.geocoders import Nominatim
from lxml import etree
import argparse
import csv
import json
import re
import requests
import sys
import time

BASE_URL_BY_ID = "http://www.ufostalker.com:8080/event?id="
BASE_URL_BY_TERM = "http://ufostalker.com:8080/search?type=all&size=10&term="
SOURCE = "MUFON"
REPORTS_BY_PAGE = 20
TIME_DELAY = 5

class Sighting:

  def __init__(self, id, sighted_at, reported_at, location, shape, duration, description, latitude, longitude, case_number):
    self.id = id
    self.sighted_at = sighted_at
    self.reported_at = reported_at
    self.location = location
    self.shape = shape
    self.duration = duration
    self.description = description
    self.source = SOURCE
    self.latitude = latitude
    self.longitude = longitude
    self.case_number = case_number

  def __str__(self):
    return "%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s" % (self.id, self.sighted_at, self.reported_at, self.location, self.shape, self.duration, self.description, self.source, self.latitude, self.longitude, self.case_number)

  def to_array(self):
    return [self.id, self.sighted_at, self.reported_at, self.location, self.shape, self.duration, self.description, self.latitude, self.longitude, self.case_number]


def check_arguments(initial, end, term, output):
  if term is None:
    if initial is None or end is None:
      print("'initial' and 'end' must be passed unless you specify a term")
      return False
    if initial > end:
      print("'initial' must be less than or equal to 'end'")
      return False

  if output is None:
    print("'output' must be specified")
    return False

  # If term is passed, 'initial' and 'end' are ignored
  return True



def clean(text):
  text.gsub("(\n|\r|\t)+", '').lstrip()

def geolocate(city, country):
  geolocator = Nominatim()
  loc = geolocator.geocode("%s, %s" % (city, country))
  return loc

def parse_report(base_url, x):
  source = requests.get("%s%s" % (base_url, x), headers = {'User-Agent': 'mufon-crawler'}, stream = True)

  if source.status_code is not 200:
    print('Did not get a status OK', source.status_code)

  source.raw.decode_content = True

  doc = etree.parse(source.raw)
  event = doc.getroot()

  id = event.find("id").text
  reported_at = event.find("submitted").text
  sighted_at = event.find("occurred").text
  location = "%s (%s)" % (event.find("city").text, event.find("country").text)
  shape = event.find("shape").text
  duration = event.find("duration").text
  description = event.find("detailedDescription").text
  latitude = event.find("latitude").text
  longitude = event.find("longitude").text
  case_number = event.find("logNumber").text

  if latitude is None or longitude is None:
    loc = geolocate(event.find("city").text, event.find("country").text)
    latitude = loc.latitude
    longitude = loc.longitude

  report = Sighting(id, sighted_at, reported_at, location, shape, duration, description, latitude, longitude, case_number)

  return report

def parse_reports_by_term(base_url, term, page_number):
  source = requests.get("%s%s&page=%s" % (base_url, term, page_number), headers = {'User-Agent': 'mufon-crawler'})

  if source.status_code is not 200:
    print('Did not get a status OK', source.status_code)

  doc = json.loads(source.text)
  content = doc['content']

  reports = []

  for report in content:
    id = report['id']
    reported_at = None
    try:
      reported_at = datetime.fromtimestamp(int(report['submitted']) / 1000.0).strftime('%Y-%m-%d %H:%M:%S')
    except:
      print('Could not generate a valid report date')

    sighted_at = None
    try:
      sighted_at = datetime.fromtimestamp(int(report['occurred']) / 1000.0).strftime('%Y-%m-%d %H:%M:%S')
    except:
      print('Could not generate a valid sighting date')

    location = "%s (%s)" % (report['city'], report['country'])
    shape = report['shape']
    duration = report['duration']
    description = report['detailedDescription']
    latitude = report['latitude']
    longitude = report['longitude']
    case_number = report['logNumber']

    if latitude is None or longitude is None:
      try:
        loc = geolocate(report['city'], report['country'])
        latitude = loc.latitude
        longitude = loc.longitude
      except:
        print('Could not geolocate the sighting')
        latitude = None
        longitude = None

    sighting = Sighting(id, sighted_at, reported_at, location, shape, duration, description, latitude, longitude, case_number)

    reports.append(sighting)

  return reports


parser = argparse.ArgumentParser(description = 'Generates a CSV from MUFON reports')
parser.add_argument('-i', '--initial', type = int, help = 'Initial report id')
parser.add_argument('-e', '--end', type = int, help = 'Final report id')
parser.add_argument('-t', '--term', type = str, help = 'Only reports including this term, e.g., country, shape, etc.')
parser.add_argument('-l', '--limit', default = 10, type = int, help = 'Max number of reports by term')
parser.add_argument('-o', '--output', type = str, help = 'CSV file name')

args = parser.parse_args()

begin_index = args.initial
end_index = args.end
out_file = args.output
term = args.term
limit = args.limit

if not check_arguments(begin_index, end_index, term, out_file):
  sys.exit()

header = ["id", "sighted_at", "reported_at", "location", "shape", "duration", "description", "latitude", "longitude", "case_number"]
out = csv.writer(open(out_file, "w"), delimiter = ',', quoting = csv.QUOTE_ALL)
out.writerow(header)

if term is None:
  for x in range(int(begin_index), int(end_index) + 1):
    print("Downloading reports by report number... %s%s" % (BASE_URL_BY_ID, x))
    try:
      report = parse_report(BASE_URL_BY_ID, x)
      out.writerow(report.to_array())
    except:
      print('Could not parse the report')

    time.sleep(TIME_DELAY)
else:
  print("Downloading reports by term... %s%s" % (BASE_URL_BY_TERM, term))
  n_pages = limit // REPORTS_BY_PAGE
  if limit % REPORTS_BY_PAGE is not 0:
    n_pages += 1

  total_reports = 0

  for x in range(1, n_pages + 1):
    try:
      print(x)
      print("total", total_reports)
      reports = parse_reports_by_term(BASE_URL_BY_TERM, term, x)
      for report in reports:
        out.writerow(report.to_array())
        total_reports += 1
        if total_reports == limit:
          sys.exit()
    except:
      print('Could not parse the report')

    time.sleep(TIME_DELAY)
