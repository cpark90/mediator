#!/usr/bin/env python
# coding=utf-8
import os
import unittest

import redis

class TestCase(unittest.TestCase):

    def __init__(self, methodName) -> None:
        super().__init__(methodName)
        self.redis = redis.Redis(port=6379)
        self.cities = [(5.94, 45.86, 'Rumilly'), (6.63, 45.93, 'Sallanches'), (6.25, 45.93, 'Annecy')]

    def test_geoadd(self):
        for city in self.cities:
            self.redis.geoadd("cities", city)
        self.assertTrue(False)
            
    def test_georadiusbymember(self):
        result = self.redis.georadiusbymember("cities","Annecy", 50, unit="km")
        print("b")
        print(result)
        print("a")
        self.assertTrue(False)

if __name__ == '__main__':
    unittest.main()