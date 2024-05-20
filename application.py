import argparse
import socket
import struct
import time
import os
from datetime import datetime
import re
import sys

# main source for udp packet code = https://abdesol.medium.com/udp-protocol-with-a-header-implementation-in-python-b3d8dae9a74b
#  constants
PACKET_SIZE = 1000 # total size of a packet in bytes
HEADER_FORMAT = 'H H H' # defines header in packet to three unsigned short integers, H = 2 bytes, 6 total. Represents sequence number, ack number and flags respectively. 
HEADER_SIZE = struct.calcsize(HEADER_FORMAT) # calculates size in bytes
DATA_SIZE = PACKET_SIZE - HEADER_SIZE  # data is 994, eg 1000 - header 
TIMEOUT = 0.5 # sets timeout to 0.5 seconds, client will wait for this long for ack before timing out

# flag types, notation 0b gives them binary notations that makes it easier to manipulate them seperately in protocol src: https://www.geeksforgeeks.org/create-integer-variable-by-assigning-binary-value-in-python/
SYN = 0b0001
ACK = 0b0010
FIN = 0b0100

# Description:
# creates a packet by combining header (seq, ack, flags) and data. Uses struct to make the packet into a binary string based on HEADER_FORMAT
# takes in seq_nr, ack_nr, flags and a data byte variable
# returns the packet consisting of header + any additional data
# no exception handling needed
def create_packet(seq_nr, ack_nr, flags, data=b""):
    header = struct.pack(HEADER_FORMAT, seq_nr, ack_nr, flags)
    return header + data

# Description:
# takes in a packet, slices it, unpacks and returns the unpacked data
# slices the packet to get header data into the variable header
# slices the packet to get everything except header data into the variable data
# uses struct to unpack content and get flags assigned to seq_nr, ack_nr, flags
# returns the unpacked data with flags separated
# no exception handling needed
# src: https://www.geeksforgeeks.org/create-integer-variable-by-assigning-binary-value-in-python/
def unpack_packet(packet): 
    header = packet[:HEADER_SIZE]
    data = packet[HEADER_SIZE:]
    seq_nr, ack_nr, flags = struct.unpack(HEADER_FORMAT, header) 
    return seq_nr, ack_nr, flags, data

# Description:
# cheks that given port is within range defined in assignment terms
# sets the condition that if its within correct range, return boolean var True
# if its outside of the given range, returns false
# no exception handling needed
# code taken from oblig1, args.py
def port_check(port):
    if port in range(1024, 65535):
        return True
    else:
        return False

# Descripion:
# server side handling of the application
# Arguments:
# server_socket: open UDP socket on server side
# server_ip: holds ip for the server
# server_port: holds port of the server
# discard_nr: holds the number of the packet to discard, specified using -d when invoking the server
# received_data: empty byte string for content during transfer
# expected_sequence: sequence number expected for the next incoming packet. variable updates to keep track of incoming packets


def start_server(server_ip, server_port, output, discard_nr):
    # general structure for server side taken from src: https://github.com/safiqul/2410/blob/main/udp/udpserver.py
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) 
    server_socket.bind((server_ip, server_port))
    print(f"Server is listening on {server_ip}:{server_port}") 

    recevied_data = b""
    expected_sequence = 1 

    while True:
        packet, client_address = server_socket.recvfrom(PACKET_SIZE)    # receives packet from client to a max of PACKET_SIZE
        seq_nr, ack_nr, flags, data = unpack_packet(packet)             # unpacks packet into the components (sequence number, ack number, etc)

        if flags & SYN:                                                 # if packet contains a syn flag
            print("SYN packet received")
            syn_ack_packet = create_packet(0, 0, SYN | ACK)             # creates a syn-ack packet
            server_socket.sendto(syn_ack_packet, client_address)        # sends syn-ack to client, waits for ack
            print("SYN-ACK packet is sent")
        
        elif flags & ACK and not data:                               # theres ack but no data, indicates that its the ack for the previously sent syn-ack
            print("ACK packet is received \nConnection established") # confirms connection
            start_time = time.time()                                 # starts timer to measure connection duration
        
        elif flags == 0 and data:               # if the received packet doesnt have any flags and contains data, its a content packet (regular data packet)
            if seq_nr == discard_nr:            # checks if the sequence number is equal to the discard number given by the -d flag (if there is one)
                discard_nr = float('inf')       # set the number to infinite so we only drop packet once
                continue                        # skips rest of the code in this iteration of loop, aka discards rest of packet 
            if seq_nr == expected_sequence:     # if sequence number is what we expect
                print(f"{datetime.now().strftime('%H:%M:%S.%f')} -- packet {seq_nr} is received") # src for formatting https://docs.python.org/3/library/datetime.html, https://www.programiz.com/python-programming/datetime/strftime
                recevied_data += data           # append data received in this packet to our tracker variable
                ack_packet = create_packet(0, seq_nr, ACK)       # creathe an ack packet for this sequence number
                server_socket.sendto(ack_packet, client_address) # sends ack this packet
                print(f"{datetime.now().strftime('%H:%M:%S.%f')} -- sending ack for the received {seq_nr}")
                expected_sequence += 1          # increment expected sequence number by 1 so that we now expect the next packet / sequence number 
            else:
                print(f"{datetime.now().strftime('%H:%M:%S.%f')} -- out of order packet {seq_nr} received")     # prints when we receive a packet that isn't in order

        elif flags & FIN:                                        # if packet contains FIN, indicates client wishing to end connection
            print("....\n\nFIN packet is received") 
            fin_ack_packet = create_packet(0, 0, FIN | ACK)      # creates a packet that acknowledes request to end connection
            server_socket.sendto(fin_ack_packet, client_address) # sends the packet to client
            print("FIN ACK packet is sent")
            break                                                # breaks out of loop to end connection
    
    end_time = time.time()                                              # captures end time for connection
    throughput = (len(recevied_data)*8) / (end_time - start_time) / 1e6 # calculates throughput in mbps src: https://community.arubanetworks.com/discussion/throughput-calculation-in-bits-per-second-and-packets-per-second ,
    print(f"\nThroughput is {throughput:.2f} Mbps")                     # https://data2410.zulipchat.com/#narrow/stream/434992-Home-exam/topic/throughput/near/438325269

    with open(output, 'wb') as f: # writes out the data we got into an output file saved as received_data
        f.write(recevied_data) 

    print("Connection closes") # closes socket connection
    server_socket.close()

# Description:
# client side handling of the application
# Arguments:
# client_socket: open UDP socket on client side
# server_ip: holds ip for the server
# server_port: holds port of the server
# file_name: holds the file specifie dusing -f that user wants to transfer
# window_size: holds window size either 3 as default or other value specified using -w
# rest of variables and functions are described in comments between / next to the lines of code for readability

def start_client(server_ip, server_port, file_name, window_size):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.settimeout(TIMEOUT)                               # set client timeout to constant value 0.5
    
    print("Connection Established phase:\n")                        # start establishing server-client connection
    syn_packet = create_packet(0, 0, SYN)                           # create syn packet
    client_socket.sendto(syn_packet, (server_ip, server_port))      # sends a syn packet to establish connection and wait for acknowledgement from server
    print("SYN packet is sent")

    try:
        packet, _ = client_socket.recvfrom(PACKET_SIZE)                  # receives packet from server
        seq_num, ack_num, flags, data = unpack_packet(packet)            # unpacks the received packet to get separated values
        if flags & (SYN | ACK):                                          # packet containing SYN and ACK would be connection acknowledgement
            print("SYN-ACK packet is received")                          # notify reception
            ack_packet = create_packet(0, 0, ACK)                        # create ack for connection
            client_socket.sendto(ack_packet, (server_ip, server_port))   # sends an ack for connection established to server
            print("Ack packet is sent\nConnection established\n")
    except socket.timeout:                                               # exception on timeout / couldnt connect to server
        print("Timeout waiting for SYN-ACK")
        return
    

    print("Data Transfer:\n")                       # data transfer begins
    sequence_number = 1                             # variable that keeps track of packages being sent, different from seq_num 
    window = []                                     # empty array for sliding window
    file_size = os.path.getsize(file_name)          # calculates size of the file we want to transfer src: https://www.educative.io/answers/what-is-the-ospathgetsize-method-in-python
    bytes_sent = 0                                  # tracker for how many bytes we've sent

    with open(file_name, 'rb') as f:                                        # open file so we can process data 
        while bytes_sent < file_size or window:                             # as long as we havent sent every byte in the file OR until the window runs out (to ensure that we dont close connection before receiving all ACKs)
            while len(window) < window_size  and bytes_sent < file_size:    # if the packets in the window is less than window size and there is still data we haven't sent in the file
                data = f.read(DATA_SIZE)                                    # read a chunk of data from file
                if not data:
                    break                                                   # break if theres no data left
                packet = create_packet(sequence_number, 0, 0, data)         #create a packet with sequence nr and data chunk
                client_socket.sendto(packet, (server_ip, server_port))      # send data packet to server
                window.append(packet)                                       # add packet to sliding window
                window_seq_numbers = ', '.join(str(unpack_packet(p)[0]) for p in window) # string rep of the sequence nr in packets in the window separated by comma src: https://docs.python.org/3/tutorial/datastructures.html#list-comprehensions
                print(f"{datetime.now().strftime('%H:%M:%S.%f')} -- packet with s = {sequence_number} sent, sliding window = {{{window_seq_numbers}}}")
                sequence_number += 1                                        # increment sequence number for next packet we want to send
                bytes_sent += len(data)                                     # keep track of data we've sent by adding the length data to bytes_sent

            try:
                ack_packet, _ = client_socket.recvfrom(PACKET_SIZE)                                         # receives ack from server and puts it in variable ack_packet (_ used to ignore unnecessary info src: https://www.datacamp.com/tutorial/role-underscore-python)
                _, ack_num, flags, _ = unpack_packet(ack_packet)                                            # unpacks for ack number and flags
                if flags & ACK:                                                                             # if packet contains an ACK
                    print(f"{datetime.now().strftime('%H:%M:%S.%f')} -- ACK for packet {ack_num} received") # notifies reception in given format of assignment
                    while window and unpack_packet(window[0])[0] <= ack_num:                                # if theres packets in the window that have been acked
                        window.pop(0)                                                                       # removes packet src: https://www.w3schools.com/python/ref_list_pop.asp

            except socket.timeout:
                print(f"{datetime.now().strftime('%H:%M:%S.%f')} -- RTO occured")                                                     # notifies timeout
                for packet in window:
                    client_socket.sendto(packet, (server_ip, server_port))                                                            # retansmits all packets in the window
                    print(f"{datetime.now().strftime('%H:%M:%S.%f')} -- Retransmitting packet with seq = {unpack_packet(packet)[0]}") # prints a message for each resent packet

    print("....\nDATA Finished")

   
    print("\n\nConnection Teardown:\n")                             # connection teardown starts
    fin_packet = create_packet(0, 0, FIN)                           # creates a packet to indicate connection end (FIN) to server
    client_socket.sendto(fin_packet, (server_ip, server_port))      # sends FIN to server
    print("FIN packet is sent")

    try:
        packet, _ = client_socket.recvfrom(PACKET_SIZE)             # receive packet from server
        _, _, flags, _ = unpack_packet(packet)                      # unpack
        if flags & (FIN | ACK):                                     # if it contains FIN ACK, notify reception and closing of connection
            print("FIN ACK packet is received")
            print("Connection closes")
    except socket.timeout:                                          # in case of timeout
        print("Timeout waiting for FIN-ACK")

    client_socket.close()                                           # close connection

# Description
# main function for running the program. mostly contains run conditions and parsing
# Arguments: 
# start_server: calls the function to start server taking in the given parameters
# start_client: calls the function to start client taking in the given parameters
# # rest of variables and functions are described in comments between / next to the lines of code for readability
def main():

    # template from parsing src: https://docs.python.org/3/library/argparse.html , https://github.com/safiqul/2410/blob/main/argparse-and-oop/optional-arg.py as well as oblig 2 of the course
    parser = argparse.ArgumentParser(description="UDP File Transfer Program")
    
    # arguments constructed based on invokation table from https://github.com/safiqul/drtp-oppgave/ 
    parser.add_argument('-s', '--server', action='store_true', help='enable the server mode')
    parser.add_argument('-c', '--client', action='store_true', help='enable the client mode')
    parser.add_argument('-i', '--ip', type=str, required=True, help='The client will use this flag to select servers ip for the connection - uses default value if its not provided. example format: 10.0.1.2. Default: 127.0.0.1')
    parser.add_argument('-p', '--port', type=int, default=8080, help='Port number on which the server should listen at the client side, allows to select the servers port number. Must be within integer range [1024,65535]. Default: 8080')
    parser.add_argument('-f', '--file', type=str, required=False, help='Allows you to choose the jpg file')
    parser.add_argument('-w', '--window', type=int, default=3, help='Sliding window size. Default: 3')
    parser.add_argument('-d', '--discard', type=int, default=float('inf'), help='Sequence number to discard for testing')

    args = parser.parse_args()

    # code for port checking taken from oblig 2 of the course 
    if args.port != None and port_check(args.port) == True:         # checks that if there is a port number and that it got True on the port check
        port = args.port                                            # set port
    elif args.port != None and port_check(args.port) == False:      # checks that if there is a port number and that it got False on the port check
        print("Invalid port. Choose range between [1024, 65535]")   # error message
        sys.exit(1)                                                 # exit program

    if args.server and args.client:                                 # if someone tries to invoke both server and client
        print("Cannot invoke both server and client")               # error message
        sys.exit(1)                                                 # exit program

    elif args.server:                                               # if someone invokes server        
        if not args.file:                                           # check that theres no filename provided
            output = 'received_file.jpg'                            # set location for output to received_file.jpg
        else:                                                       # otherwise set output to the provided file
            output = args.file
        start_server(args.ip, args.port, output, args.discard)      # call server 

    elif args.client:                                                       # if someone invokes client
        if not args.file:                                                   # check that they provided a file to transfer
            print("Please specify the file to be sent using -f option")     # error message
        else:
            start_client(args.ip, args.port, args.file, args.window)        # start client if they did provide a file
    else:
        print("Specify launch option server or client using -s or -c")      # if they didnt invoke -s nor -c, error message 


if __name__ == '__main__':
    main()