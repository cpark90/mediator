#!/usr/bin/env python
# coding=utf-8
import os
import unittest

import mosaic_proto.protos.federate.simulation_step_pb2 as simulation_step

class TestCase(unittest.TestCase):

    def __init__(self, methodName) -> None:
        super().__init__(methodName)
        self.tmp_path = os.path.join("/tmp", "test.pb.txt")
        self.sample_data = "test"

    def test_proto_text_write(self):
        proto_data = simulation_step.SimulationStep()
        proto_data.fedName = self.sample_data
        self.assertTrue(False)
            

    def test_proto_text_read(self):
        self.assertTrue(False)

if __name__ == '__main__':
    unittest.main()