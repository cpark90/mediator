#!/usr/bin/env python
# coding=utf-8
import os
import unittest

from pyignite import Client
from pyignite.datatypes import FloatObject

class GeoPoint:
    def __init__(self, latitude, longitude):
        self.latitude = latitude
        self.longitude = longitude

class TestCase(unittest.TestCase):

    def __init__(self, methodName) -> None:
        super().__init__(methodName)
        self.client = Client()
        self.client.connect('127.0.0.1', 10800)

        self.cache = self.client.get_or_create_cache('geospatialCache')
        self.cities = [{'name': 'Location A', 'latitude': 40.7128, 'longitude': -74.0060},
                       {'name': 'Location B', 'latitude': 34.0522, 'longitude': -118.2437},
                       {'name': 'Location C', 'latitude': 51.5074, 'longitude': -0.1278}]

    def test_put(self):
        for i, city in enumerate(self.cities):
            self.cache.put(i, city)
        self.assertTrue(False)
            
    def test_query_radius(self):
        center_latitude = 40.7128
        center_longitude = -74.0060
        radius_km = 50
        query = self.client.sql(
            'ST_Distance(ST_PointFromText("POINT(" || longitude || " " || latitude || ")"), ' +
            'ST_PointFromText("POINT(%s %s)")) <= %s' % (center_longitude, center_latitude, radius_km)
        )
        result = query.execute()

        for item in result:
            print(item[0])

        self.assertTrue(False)

if __name__ == '__main__':
    unittest.main()