
import socket
import struct
import time

# constants
PACKET_SIZE = 1000
HEADER_FORMAT = 'H H H' # sequence nr, ack nr, flags
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
WINDOW_SIZE = 3
TIMEOUT = 0.5 # 500 ms

# packet types / flags
SYN = 0b0001
ACK = 0b0010
FIN = 0b0100

def create_packet(seq_num, ack_num, flags, data=b""):
    header = struct.pack(HEADER_FORMAT, seq_num, ack_num, flags)
    return header + data

def unpack_packet(packet):
    header = packet[:HEADER_SIZE]
    data = packet[HEADER_SIZE:]
    seq_num, ack_num, flags = struct.unpack(HEADER_FORMAT, header)
    return seq_num, ack_num, flags, data

def start_server(server_ip, server_port, output_file):
    # Create a UDP socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind((server_ip, server_port))

    print(f"Server is running and listening on port {server_ip}:{server_port}...")

    received_data = b""
    expected_sequence = 1

    while True:
        packet, client_address = server_socket.recvfrom(PACKET_SIZE)
        seq_num, ack_num, flags, data = unpack_packet(packet)

        if flags & SYN:
            print("SYN packet received")
            syn_ack_packet = create_packet(0, 0, SYN | ACK)
            server_socket.sendto(syn_ack_packet, client_address)
            print("SYN-ACK is sent")

        elif flags & ACK and not data:
            print("ACK received, connection established")
            start_time = time.time()
        
        elif flags & data:
            if seq_num == expected_sequence:
                print(f"Received packet {seq_num}")
                received_data += data
                ack_packet = create_packet(0,seq_num, ACK)
                server_socket.sendto(ack_packet, client_address)
                expected_sequence += 1
        
        elif flags & FIN:
            print("FIN packet is received")
            fin_ack_packet = create_packet(0, 0, FIN | ACK)
            server_socket.sendto(fin_ack_packet, client_address)
            print("FIN ACK is sent")
            break
    
    end_time = time.time()
    throughput = (len(received_data)*8) / (end_time - start_time) / 1e6 # in Mbps
    print(f"Throughput is {throughput:.2f} Mbps")

    with open(output_file, 'wb') as f:
        f.write(received_data)
    
    print("Connection closed")
