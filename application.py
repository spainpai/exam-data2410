import argparse
import socket
import struct
import time
import os
from datetime import datetime

#  constants
PACKET_SIZE = 1000 # total size of a packet in bytes
HEADER_FORMAT = 'H H H' # defines header in packet to three unsigned short integers, H = 2 bytes, 6 total. Represents sequence number, ack number and flags respectively. 
HEADER_SIZE = struct.calcsize(HEADER_FORMAT) # calculates size in bytes
DATA_SIZE = PACKET_SIZE - HEADER_SIZE # determines how much data can fit per packet considering header
TIMEOUT = 0.5 # sets timeout to 0.5 seconds, client will wait for this long for ack before retransmitting packages

# flag types, notation 0b gives them binary notations that makes it easier to manipulate them seperately in protocol
SYN = 0b0001
ACK = 0b0010
FIN = 0b0100

def create_packet(seq_num, ack_num, flags, data=b""):       # creates a packet by combining header and data
    header = struct.pack(HEADER_FORMAT, seq_num, ack_num, flags) # struct.pack is a function that structures the packet into binary string based on input and given header format (constant)
    return header + data

def unpack_packet(packet):  # takes in received packet
    header = packet[:HEADER_SIZE]  # slices the packet to get header
    data = packet[HEADER_SIZE:] # slices packet to get everything except header
    seq_num, ack_num, flags = struct.unpack(HEADER_FORMAT, header)  # uses struct.unpack to unpack header content, gets the flags from header 
    return seq_num, ack_num, flags, data # returns unpacked data
#___________________________________________________________________________________________________________________________________________________________________________________
#__________________SERVER SIDE _____________________________________________________________________________________________________________________________________________________
def start_server(server_ip, server_port, output_file):
    
    # create udp socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind((server_ip, server_port))        # binds to the server ip/port
    print(f"Server is listening on {server_ip}:{server_port}") 

    recevied_data = b""     # empty byte string for content
    expected_sequence = 1       # sequence number expected from packet. variable will be updated to make sure we are getting the right content

    while True:
        packet, client_address = server_socket.recvfrom(PACKET_SIZE)  # receives packet from client of defined maximum size
        seq_num, ack_num, flags, data = unpack_packet(packet)   # unpacks packet into the components (sequence number, ack number, etc)

        if flags & SYN:         # if theres a syn flag
            print("SYN packet received")
            syn_ack_packet = create_packet(0, 0, SYN | ACK)     # creates a syn-ack packet
            server_socket.sendto(syn_ack_packet, client_address)    # sends syn-ack to client, waits for ack
            print("SYN-ACK packet is sent")
        
        elif flags & ACK and not data:  # theres ack but no data, indicates that its the ack for the previously sent syn-ack
            print("ACK packet is received \nConnection established") # confirms connection
            start_time = time.time() # starts timer to measure connection duration
        
        elif flags == 0 and data: # if the received packet doesnt have any flags and contains data, its a content packet (regular data packet). 
            if seq_num == expected_sequence: # if sequence number is what we expect, we accent the packet
                print(f"{datetime.now().strftime('%H:%M:%S.%f')} -- packet {seq_num} is received") 
                recevied_data += data # tracks amount of data we've gotten
                ack_packet = create_packet(0, seq_num, ACK)
                server_socket.sendto(ack_packet, client_address) # sends ack for received packet
                print(f"{datetime.now().strftime('%H:%M:%S.%f')} -- sending ack for the received {seq_num}")
                expected_sequence += 1 # adjusts expected sequence number

        elif flags & FIN:  # indicates clients intention to close connection
            print("....\n\nFIN packet is received")
            fin_ack_packet = create_packet(0, 0, FIN | ACK)
            server_socket.sendto(fin_ack_packet, client_address) # sends ack for connection end
            print("FIN ACK packet is sent")
            break # breaks out of the loop to end connection
    
    end_time = time.time() # captures end time for connection
    throughput = (len(recevied_data)*8) / (end_time - start_time) / 1e6 # calculates throughput in mbps 
    print(f"\nThroughput is {throughput:.2f} Mbps")

    with open(output_file, 'wb') as f: # writes out the data we got into an output file
        f.write(recevied_data) 

    print("Connection closes") # closes socket connection
    server_socket.close()

#___________________________________________________________________________________________________________________________________________________________________________________
#__________________CLIENT SIDE______________________________________________________________________________________________________________________________________________________
def start_client(server_ip, server_port, file_name, window_size):
    # UDP socket
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.settimeout(TIMEOUT) # set client timeout to constant value

    # establishing server-client connection
    print("Connection Established phase:\n") 
    syn_packet = create_packet(0, 0, SYN)  
    client_socket.sendto(syn_packet, (server_ip, server_port))  # sends a syn packet to establish connection and wait for acknowledgement
    print("SYN packet is sent")

    try:
        packet, _ = client_socket.recvfrom(PACKET_SIZE)  # receives packet from server
        seq_num, ack_num, flags, data = unpack_packet(packet)  # unpacks the gotten package to get values
        if flags & (SYN | ACK):   # if it has both syn and ack, its the connection acknowledgement
            print("SYN-ACK packet is received")
            ack_packet = create_packet(0, 0, ACK)
            client_socket.sendto(ack_packet, (server_ip, server_port))  # sends an ack for connection
            print("Ack packet is sent\nConnection established\n")
    except socket.timeout:
        print("Timeout waiting for SYN-ACK")  # failure to establish connection
        return
    

    # data transfer
    print("Data Transfer:\n")
    sequence_number = 1  # keeps track of packages being sent
    window = []  # sliding window variable
    file_size = os.path.getsize(file_name)  # calculates size of the file we want to transfer
    bytes_sent = 0  # nr of bytes sent

    with open(file_name, 'rb') as f:   
        while bytes_sent < file_size: # as long as we havent sent every byte in the file
            while len(window) < window_size  and bytes_sent < file_size: # as long as the window isnt full, and there are still bytes to be sent in the file
                data = f.read(DATA_SIZE) # read a chunk of data from file
                if not data:
                    break # break if theres no data left
                packet = create_packet(sequence_number, 0, 0, data)  #create a packet with sequence nr and data chunk
                client_socket.sendto(packet, (server_ip, server_port)) # send to server
                window.append(packet) # add packet to sliding window
                window_seq_numbers = ', '.join(str(unpack_packet(p)[0]) for p in window) # string rep of the sequence nr in packets of windows separated by comma
                print(f"{datetime.now().strftime('%H:%M:%S.%f')} -- packet with s = {sequence_number} sent, sliding window = {{{window_seq_numbers}}}") # prints in the given format of assignment
                sequence_number += 1 # increment nr for next packet
                bytes_sent += len(data) # keep track of data we've sent

            try:
                ack_packet, _ = client_socket.recvfrom(PACKET_SIZE)  # receives ack from server
                _, ack_num, flags, _ = unpack_packet(ack_packet)    # unpacks for ack number and flags
                if flags & ACK: # checks ack in packet
                    print(f"{datetime.now().strftime('%H:%M:%S.%f')} -- ACK for packet {ack_num} received") # notifies reception in given format of assignment
                    while window and unpack_packet(window[0])[0] <= ack_num:  # if theres packets in the window that have been acked, remove them
                        window.pop(0)

            except socket.timeout:
                print("Timeout, resending window")  # notifies timeout
                for packet in window:
                    client_socket.sendto(packet, (server_ip, server_port)) # retansmits all packets in the window
                    print(f"Resent packet {unpack_packet(packet)[0]}") # prints a message for each resent packet

    print("....\nDATA Finished")

    #connection teardown
    print("\n\nConnection Teardown:\n")
    fin_packet = create_packet(0, 0, FIN)  # creates a packet to indicate connection end to server
    client_socket.sendto(fin_packet, (server_ip, server_port))
    print("FIN packet is sent")

    try:
        fin_ack_packet, _ = client_socket.recvfrom(PACKET_SIZE)     # received a fin ack from server
        seq_num, ack_num, flags, data = unpack_packet(fin_ack_packet)   # unpacks data from packet
        if flags & (FIN | ACK):     # if it contains fin ack, notify reception and closing of connection
            print("FIN ACK packet is received")
            print("Connection closes")
    except socket.timeout:
        print("Timeout waiting for FIN-ACK")

    client_socket.close()   # close connection

#___________________________________________________________________________________________________________________________________________________________________________________
#_________________ MAIN ____________________________________________________________________________________________________________________________________________________________        
def main():
    parser = argparse.ArgumentParser(description="UDP File Transfer Program")

    parser.add_argument('-s', '--server', action='store_true', help='enable the server mode')
    parser.add_argument('-c', '--client', action='store_true', help='enable the client mode')
    parser.add_argument('-i', '--ip', type=str, required=True, help='The client will use this flag to select servers ip for the connection - uses default value if its not provided. example format: 10.0.1.2. Default: 127.0.0.1')
    parser.add_argument('-p', '--port', type=int, required=True, help='Port number on which the server should listen at the client side, allows to select the servers port number. Must be within integer range [1024,65535]. Default: 8080')
    parser.add_argument('-f', '--file', type=str, required=False, help='Allows you to choose the jpg file')
    parser.add_argument('-w', '--window', type=int, default=3, help='Sliding window size. Default: 3')

    args = parser.parse_args()

    if args.server:
        if not args.file:
            output_file = 'received_file.jpg'
        else:
            output_file = args.file
        start_server(args.ip, args.port, output_file)

    elif args.client:
        if not args.file:
            print("Please specify the file to be sent using -f option")
        else:
            start_client(args.ip, args.port, args.file, args.window)
    else:
        print("Specify launch option server or client using -s or -c")


if __name__ == '__main__':
    main()



