#!/usr/bin/env python
# coding=utf-8
import os
import unittest

from utils import proto_text_write, proto_text_read

from vnv_proto.tcp.tcp_server_conf_pb2 import TCPServerConf

class TestCase(unittest.TestCase):

    def __init__(self, methodName) -> None:
        super().__init__(methodName)
        self.tmp_path = os.path.join("/tmp", "test.pb.txt")
        self.sample_data = "test"

    def proto_text_write(self):
        proto_data = TCPServerConf()
        proto_data.data = self.sample_data
        try:
            result = proto_text_write(self.tmp_path, proto_data)
            self.assertTrue(result)
        except Exception as e:
            print(e)
        self.assertTrue(False)
            

    def proto_text_read(self):
        try:
            proto_data = proto_text_read(self.tmp_path, TCPServerConf)
            self.assertEqual(self.sample_data, proto_data.data)
        except Exception as e:
            print(e)
        self.assertTrue(False)

if __name__ == '__main__':
    unittest.main()