import socket

def start_server(port):
    # Create a UDP socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind(('', port))

    print(f"Server is running and listening on port {port}...")

    try:
        while True:
            # Receive data from client
            data, addr = server_socket.recvfrom(1000) # buffer size includes 994 bits of data and 6 bits of header
        
        if data:
            # Process header to manage data reliability
            header = data[:1] # example: First byte for header
            print(f"Received image data of length {len(image_data)} frp, {addr}")

            # actual image data
            image_data = data[:1]
            print(f"Received image data of length {len(image_data)} from {addr}")

            # example response or ack
            server_socket.sendto(b'ACK', addr)

            # Check for teardown signal (this should be based on specific header content)
            if header == b'\x00': # Example header byte indicating teardown
                print(" Teardown signal received. Closing connection")
    
    finally: 
        server_socket.close()
        print("Server socket closed.")

if __name__ == '__main__':
    # example usage: start server on port 12345
    start_server(12345)

