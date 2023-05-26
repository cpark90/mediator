import os

from utils import proto_text_write, proto_text_read

from vnv_proto.tcp.tcp_configuration_pb2 import TCPServerConf, TCPClientConf, TCPServiceConf


def proto_text_read_test(tmp_path):
    proto_data = proto_text_read(tmp_path, TCPServiceConf)
    return proto_data

def main():
    write_path = os.path.join("/home/cpark/git/vnv_framework/vnv_tcp_toolkit/conf", "tcp_server_conf.pb.txt")
    sample_data = TCPServiceConf()
    sample_data.id = 1
    sample_data.service_name = "ScenarioInstanceService"
    sample_data.data = "test"
    sample_data.protocol_info.tcp_header = 4

    result = proto_text_write(write_path, sample_data)

    read_path = os.path.join("/home/cpark/git/vnv_framework/vnv_tcp_toolkit/conf", "tcp_server_conf.pb.txt")
    result = proto_text_read_test(read_path)
    print(result.service_name)

if __name__ == '__main__':
    main()