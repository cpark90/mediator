import asyncio

from collections import deque
from bisect import insort


class TimestampMessage:
    def __init__(self, timestamp, data, seq=0):
        self.timestamp = timestamp
        self.data = data
        self.seq = seq

    def __lt__(self, other):
        if self.timestamp != other.timestamp:
            return self.timestamp < other.timestamp
        else:
            return self.seq < other.seq

class MessageBuffer:
    def __init__(self):
        self.messages = []

    def __len__(self):
        return len(self.messages)

    def add_timestamp_message(self, timestamp_message):
        insort(self.messages, timestamp_message)

    def get_timestamp_messages(self):
        return self.messages

    def get_past_messages_by_timestamp(self, timestamp):
        index = next((i for i, msg in enumerate(self.messages) if msg.timestamp <= timestamp), None)
        if index is not None:
            return self.messages[:index]
        else:
            return []
    
    def flush_past_messages(self, timestamp):
        index = next((i for i, msg in enumerate(self.messages) if msg.timestamp > timestamp), None)
        if index is not None:
            self.messages = self.messages[index:]
        else:
            self.messages = []


class ConnectionBase:
    def __init__(self, apply_to_function, send_to_function, region_contraint):
        self.receiving_thread = None
        self.sending_thread = None
        self.stop_event = threading.Event()
        
        self.received_message_buffer = MessageBuffer()
        self.sending_message_buffer = deque()
        self.apply_to_function = apply_to_function
        self.send_to_function = send_to_function
        self.region_constraint = region_contraint
        self.applicable_timebound = {"lower":None, "upper":None}
    
    def init_receiving_thread(self, delay):
        self.receiving_delay = delay
        self.receiving_thread = threading.Thread(target=self.receiving_thread_function)

    def init_sending_thread(self, delay):
        self.sending_delay = delay
        self.sending_thread = threading.Thread(target=self.sending_thread_function)
    
    def start(self):
        if self.receiving_thread is not None:
            self.receiving_thread.start()
        if self.sending_thread is not None:
            self.sending_thread.start()

    def stop(self):
        self.stop_event.set()
        if self.receiving_thread is not None:
            self.receiving_thread.join()
        if self.sending_thread is not None:
            self.sending_thread.join()

    def append_sending_messages(self, messages):
        for message in messages:
            self.sending_message_buffer.append(message)

    def flush_past_received_messages(self, timestamp):
        self.received_message_buffer.flush_past_messages(timestamp)

    def update_timebound(self, lower_time, upper_time):
        self.applicable_timebound["lower"] = lower_time
        self.applicable_timebound["upper"] = upper_time
        
        self.process_messages_until_timestamp(timestamp=self.applicable_timebound["upper"])

    def process_messages_until_timestamp(self, timestamp):
        raise NotImplementedError

    def connect(self, host, port):
        raise NotImplementedError
    
    def process_received_message(self, wrapper):
        raise NotImplementedError
    
    def process_sending_message(self):
        raise NotImplementedError

    def validate_out_of_region(self, region, message):
        raise NotImplementedError
    
    def validate_before_timestamp(self, timestamp, message):
        raise NotImplementedError

    def receiving_thread_function(self):
        raise NotImplementedError

    def sending_thread_function(self):
        raise NotImplementedError
    
    def receive_message(self):
        raise NotImplementedError
    