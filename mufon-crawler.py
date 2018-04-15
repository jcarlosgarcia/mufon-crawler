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
BASE_URL_BY_COUNTRY = "http://ufostalker.com:8080/search?type=all&size=10&term="
SOURCE = "MUFON"
REPORTS_BY_PAGE = 10
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


def check_arguments(initial, end, country, output):
  if country is None:
    if initial is None or end is None:
      print("'initial' and 'end' must be passed unless you specify a country")
      return False
    if initial > end:
      print("'initial' must be less than or equal to 'end'")
      return False

  if output is None:
    print("'output' must be specified")
    return False

  # If country is passed, 'initial' and 'end' are ignored
  return True



def clean(text):
  text.gsub("(\n|\r|\t)+", '').lstrip()

def geolocate(city, country):
  geolocator = Nominatim()
  loc = geolocator.geocode("%s, %s" % (city, country))
  return loc

def parse_report(base_url, x):
  source = requests.get("%s%s" % (base_url, x), headers = {'User-Agent': 'mufon-crawler'}, stream = True)
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

def parse_reports_by_country(base_url, country, page_number):
  source = requests.get("%s%s&page=%s" % (base_url, country, page_number), headers = {'User-Agent': 'mufon-crawler'})
  #source.raw.decode_content = True

  print(source.content)

  doc = json.loads(source.text)
  content = doc['content']

  print(content)

  reports = []

  for report in content:
    id = report['id']
    reported_at = datetime.fromtimestamp(int(report['submitted']) / 1000.0).strftime('%Y-%m-%d %H:%M:%S')
    sighted_at = datetime.fromtimestamp(int(report['occurred']) / 1000.0).strftime('%Y-%m-%d %H:%M:%S')
    location = "%s (%s)" % (report['city'], report['country'])
    shape = report['shape']
    duration = report['duration']
    description = report['detailedDescription']
    latitude = report['latitude']
    longitude = report['longitude']
    case_number = report['logNumber']

    if latitude is None or longitude is None:
      loc = geolocate(report['city'], report['country'])
      latitude = loc.latitude
      longitude = loc.longitude

    sighting = Sighting(id, sighted_at, reported_at, location, shape, duration, description, latitude, longitude, case_number)

    reports.append(sighting)

  return reports


parser = argparse.ArgumentParser(description = 'Generates a CSV from MUFON reports')
parser.add_argument('-i', '--initial', type = int, help = 'Initial report id')
parser.add_argument('-e', '--end', type = int, help = 'Final report id')
parser.add_argument('-c', '--country', type = str, help = 'Only reports from this country')
parser.add_argument('-l', '--limit', default = 10, type = int, help = 'Max number of reports by country')
parser.add_argument('-o', '--output', type = str, help = 'CSV file name')

args = parser.parse_args()

begin_index = args.initial
end_index = args.end
out_file = args.output
country = args.country
limit = args.limit

if not check_arguments(begin_index, end_index, country, out_file):
  sys.exit()

header = ["id", "sighted_at", "reported_at", "location", "shape", "duration", "description", "latitude", "longitude", "case_number"]
out = csv.writer(open(out_file, "w"), delimiter = ',', quoting = csv.QUOTE_ALL)
out.writerow(header)

if country is None:
  for x in range(int(begin_index), int(end_index) + 1):
    print("Downloading reports by report number... %s%s" % (BASE_URL_BY_ID, x))

    report = parse_report(BASE_URL_BY_ID, x)
    out.writerow(report.to_array())
    time.sleep(TIME_DELAY)
else:
  print("Downloading reports by country... %s%s" % (BASE_URL_BY_COUNTRY, country))
  n_pages = limit // REPORTS_BY_PAGE
  if limit % REPORTS_BY_PAGE is not 0:
    n_pages += 1

  total_reports = 0

  for x in range(1, n_pages + 1):
    reports = parse_reports_by_country(BASE_URL_BY_COUNTRY, country, x)
    for report in reports:
      out.writerow(report.to_array())
      total_reports += 1
      if total_reports == limit:
        sys.exit()

    time.sleep(TIME_DELAY)