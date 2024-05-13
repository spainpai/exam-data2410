import socket
import os

def send_image(ip, port, file_path, window_size):
    # create UDP socket
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # open the image file to read it in bionary mode
    with open(file_path, 'rb') as image:
        image_data = image.read()

    # calculate the number of chunks
    chunk_size = 994
    total_chunks = len(image_data) // chunk_size + (len(image_data) % chunk_size != 0)
    print(f"Total chunks to send: {total_chunks}")

    # send data in chunks
    for i in range(total_chunks):
        start = i * chunk_size
        end = start + chunk_size
        chunk_data = image_data[start:end]

        # add a header (sequence number as header)
        header = i.to_bytes(1, byteorder='big')
        packet = header + chunk_data

        # send packet
        client_socket.sendto(packet, (ip, port))

        # wait for ack
        try:
            client.socket.settimeout(2)
            ack, _ = client_socket.recvfrom(1024)
            print(f"Received ACK for chunk {i}: {ack}")
        except socket.timeout:
            print(f"No ACK received for chunk {i}, resending...")
            client_socket.sendto(packet, (ip,port))

        if (i+1) % window_size == 0:
            input("Press enter to continue sending the next window...")
    
    # send teardown singal
    client_socket.sendto(b'\x00', (ip, port))
    print("All data sent. Sending teardown signal and closing socket.")
    client_socket.close()

if __name__ == '__main__':
    send_image('192.168.1.1', 12345, 'path_to_image.jpg',3)

