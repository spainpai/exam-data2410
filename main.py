import argsparse
import sys
from server import start_server
from client import send_image

def main():
    parser = argsparse.ArgumentParser(description="UDP File Transfer Program")

    # Creating a mutually exclusive group for -s and -c options
    group = parser.add_mutually_exclusive_group(required=true)
    group.add_argument('-s', '--server', type=bool, action='store_true', help='enable the server mode')
    group.add_argument('-c', '--client', type=bool, action='store_true', help='enable the client mode')

    # Other arguments
    parser.add_argument('-i', '--ip', type=str, required=False, help='The client will use this flag to select servers ip for the connection - uses default value if its not provided. example format: 10.0.1.2. Default: 127.0.0.1')
    parser.add_argument('-p', '--port', type=int, required=True, help='Port number on which the server should listen at the client side, allows to select the servers port number. Must be within integer range [1024,65535]. Default: 8080')
    parser.add_argument('-f', '--file', type=str, required=True, help='Allows you to choose the jpg file')
    parser.add_argument('-w', '--window', type=int, default=3, help='Sliding window size. Default: 3')
    parser.add_argument('-d', '--discard', type=int, )
    

    # Parse arguments
    args = parser.parse_args()

    # Decision making based on arguments
    if args.server:
        print("Running as server...")
        start_server(args.port)
    elif args.client:
        if not args.ip:
            print("Client mode requires an IP address of the server.")
            sys.exit(1)
        print("Running as client...")
        file_path = input("Enter path to the image file: ")
        send_image(args.ip, args.port, file_path, args.window)

if __name__ == '__main__':
    main()



