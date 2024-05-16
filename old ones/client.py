import socket
import struct
import time
import os

# constants
PACKET_SIZE = 1000
HEADER_FORMAT = 'H H H'  # sequence nr, ack nr, flags
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
DATA_SIZE = PACKET_SIZE - HEADER_SIZE
WINDOW_SIZE = 3
TIMEOUT = 0.5 # 500ms

# packet types
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

def start_client(server_ip, server_port, file_name):
    # create DUP socket
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.settimeout(TIMEOUT)

    syn_packet = create_packet(0, 0, SYN)
    client_socket.sendto(syn_packet, (server_ip, server_port))
    print("SYN sent")

    try:
        packet, _ = client_socket.recvfrom(PACKET_SIZE)
        seq_num, ack_num, flags, data = unpack_packet(packet)
        if flags & (SYN | ACK):
            print("SYN ACK received")
            ack_packet = create_packet(0, 0, ACK)
            client_socket.sendto(ack_packet, (server_ip, server_port))
            print("ACK sent")
            print("Connection established")
    except socket.timeout:
        print("Timeout waiting for SYN-ACK")
        return
    
    # data transfer
    sequence_number = 1
    window_base = 1
    window = []
    file_size = os.path.getsize(file_name)
    bytes_sent = 0

    with open(file_name, 'rb') as f:
        while bytes_sent < file_size:
            while len(window) < WINDOW_SIZE and bytes_sent < file_size:
                data = f.read(DATA_SIZE)
                if not data:
                    break
                packet = create_packet(sequence_number, 0, 0, data)
                client_socket.sendto(packet, (server_ip, server_port))
                window.append(packet)
                print(f"{time.strftime('%H:%M:%S')} -- packet with s = {sequence_number} sent, sliding window = {', '.join(str(seq) for seq, _, _, _ in [unpack_packet(p) for p in window])}")
                sequence_number += 1
                bytes_sent += len(data)

            try:
                ack_packet, _ = client_socket.recvfrom(PACKET_SIZE)
                _, ack_num, flags, _ = unpack_packet(ack_packet)
                if flags & ACK:
                    print(f"ACK for packet {ack_num} received")
                    while window and unpack_packet(window[0])[0] <= ack_num:
                        window.pop(0)
                    window_base = ack_num + 1
            except socket.timeout:
                print("Timeout, resending window")
                for packet in window:
                    client_socket.sendto(packet, (server_ip, server_port))
                    print(f"Resent packet {unpack_packet(packet)[0]}")

    print("Data transfer complete")

    # connection teardown
    fin_packet = create_packet(0, 0, FIN)
    client_socket.sendto(fin_packet, (server_ip, server_port))
    print("FIN packet sent")

    try:
        fin_ack_packet, _ = client_socket.recvfrom(PACKET_SIZE)
        seq_num, ack_num, flags, data = unpack_packet(fin_ack_packet)
        if flags & (FIN | ACK):
            print("FIN ACK received")
            print("Connection closed")
    except socket.timeout:
        print("Timeout waiting for FIN-ACK")

    client_socket.close()
    

