import logging
import socket
import struct
import time

from mediator.connections import ConnectionBase, TimestampMessage
from federate_message_wrapper_pb2 import FederateMessageWrapper
from mediator_status_pb2 import MediatorStatus
from types_pb2 import StatusType

class ConnectionMosaic(ConnectionBase):
    def __init__(self, delay, apply_to_function, send_to_function, region_contraint, host='127.0.0.1', port='8913'):
        super().__init__(apply_to_function, send_to_function, region_contraint)
        self.connect(host, port)
        self.init_receiving_thread(delay=delay)
        self.init_sending_thread(delay=delay)

    def connect(self, host, port):
        maxConnectionAttempts = 5
        while maxConnectionAttempts > 0:
            connected = True
            maxConnectionAttempts = maxConnectionAttempts - 1
            try:
                self.mosaic_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.mosaic_socket.connect((host, port))
            except:
                logging.info("reconnect mosaic")
                connected=False
            if connected:
                logging.info('Connection to mosaic. Host: %s Port: %s', host, port)
                logging.info("Mosaic and mediators are connected")
                break
            if maxConnectionAttempts == 0 and connected == False:
                logging.info("Maximum connection attempts reached and connecting to Mosaic failed.")
                raise RuntimeError("Can not connect Mosaic. Check whether Mosaic starts or not.")
    
    def process_messages_until_timestamp(self, timestamp):
        received_messages = self.received_message_buffer.get_past_messages_by_timestamp(timestamp=timestamp)
        for message in received_messages:
            self.process_received_message(message.data)

    def process_received_message(self, wrapper):
        if wrapper.WhichOneof("message") is "mediatorStatus":
            logging.info("mediatorStatus")
        elif wrapper.WhichOneof("message") is "simulationStep":
            logging.info("simulationStep")
            wrapper.simulationStep

    def process_sending_message(self):
        while self.sending_message_buffer:
            message = self.sending_message_buffer.popleft()
            wrapper = FederateMessageWrapper()
            if message.__class__.__name__ is "MediatorStatus":
                wrapper.mediatorStatus.CopyFrom(message)
            elif message.__class__.__name__ is "SimulationStep":
                wrapper.simulationStep.CopyFrom(message)

            self.mosaic_socket.sendall(struct.pack('>I', wrapper.ByteSize()))
            self.mosaic_socket.sendall(wrapper.SerializeToString())

    def validate_out_of_region(self, region, message):
        return False
    
    def validate_before_timestamp(self, timestamp, message):
        return False
    
    def receive_message(self):
        data_len_bytes = self.mosaic_socket.recv(4)
        data_len = struct.unpack('!I', data_len_bytes)[0]

        data = b''
        while len(data) < data_len:
            packet = self.mosaic_socket.recv(data_len - len(data))
            if not packet:
                return None
            data += packet

        wrapper = FederateMessageWrapper()
        wrapper.ParseFromString(data)
        return wrapper
    
    def receiving_thread_function(self):
        while not self.stop_event.is_set():
            wrapper = self.receive_message()
            if wrapper is None:
                break
            time.sleep(self.delay)
            if self.validate_out_of_region(region=self.region_constraint, message=wrapper):
                continue
            if self.validate_before_timestamp(timestamp=self.applicable_timebound["lower"], message=wrapper):
                continue
            message = TimestampMessage(timestamp=0, data=wrapper)
            self.received_message_buffer.add_message(message=message)

            if message.timestamp < self.applicable_timebound["upper"]:
                self.process_messages_until_timestamp(timestamp=self.applicable_timebound["upper"])
    
    def sending_thread_function(self):
        while not self.stop_event.is_set():
            self.process_sending_message()
            time.sleep(self.delay)
