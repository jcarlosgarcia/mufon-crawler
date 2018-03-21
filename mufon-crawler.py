from lxml import etree
import requests
import re
import sys
import time

BASE_URL =  "http://www.ufostalker.com:8080/event?id="
SOURCE = "MUFON"

class Sighting:

  def __init__(self, id, sighted_at, reported_at, location, shape, duration, description, latitude, longitude, links, case_number):
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
    self.links = links
    self.case_number = case_number

  def __str__(self):
    return "%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s" % (self.id, self.sighted_at, self.reported_at, self.location, self.shape, self.duration, self.description, self.source, self.latitude, self.longitude, self.links, self.case_number)


def clean(text):
  text.gsub("(\n|\r|\t)+", '').lstrip()


begin_index = sys.argv[1]
end_index = sys.argv[2]

for x in range(int(begin_index), int(end_index) + 1):

  print("%s%s" % (BASE_URL, x))

  source = requests.get("%s%s" % (BASE_URL, x), headers = {'User-Agent': 'mufon-crawler'}, stream = True)
  source.raw.decode_content = True

  doc = etree.parse(source.raw)
  event = doc.getroot()

  print(event.find("id").text)
  print(event.find("altitude").text)
  print(event.find("city").text)
  print(event.find("country").text)
  print(event.find("detailedDescription").text)
  print(event.find("distance").text)
  print(event.find("duration").text)
  print(event.find("latitude").text)
  print(event.find("longitude").text)
  print(event.find("logNumber").text)

  time.sleep(5)

 
