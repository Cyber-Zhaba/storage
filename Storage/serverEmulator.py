"""Central server emulator. USE THIS FILE ONLY TO TEST YOUR STORAGE CLIENT"""
import socket
from time import sleep


def create_connection(func):
    """Decorator for creating connection to server"""

    def wrapper(*args, **kwargs):
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        client_socket.connect((host, port))
        print(f"Connected to {host}:{port}")

        func(*args, **kwargs, client_socket=client_socket)
        client_socket.close()

    return wrapper


@create_connection
def add_file(filename, *, client_socket):
    """Add file to storage"""
    client_socket.send("Add".encode())
    sleep(0.01)

    client_socket.send(filename.encode())
    sleep(0.01)

    with open(filename, 'rb') as file:
        file_data = file.read(batch_size)
        while file_data:
            client_socket.send(file_data)
            file_data = file.read(batch_size)

    print(f"{filename} sent successfully")


@create_connection
def delete_file(filename, *, client_socket):
    """Delete file from storage"""
    client_socket.send("Delete".encode())
    sleep(0.01)

    client_socket.send(filename.encode())
    sleep(0.01)

    print(f"{filename} deleted successfully")


@create_connection
def get_file(filename, *, client_socket):
    """Load file from storage"""
    client_socket.send("Get".encode())
    sleep(0.01)

    client_socket.send(filename.encode())
    sleep(0.01)

    with open("serv_root\\" + filename, 'wb') as file:
        file_data = client_socket.recv(batch_size)
        while file_data:
            file.write(file_data)
            file_data = client_socket.recv(batch_size)

    print(f"{filename} received successfully")


@create_connection
def edit_file(filename, *, client_socket):
    """Edit file in storage"""
    client_socket.send("Edit".encode())
    sleep(0.01)

    client_socket.send(filename.encode())
    sleep(0.01)

    current_batch_size = int(input("Enter batch size: "))
    client_socket.send(str(current_batch_size).encode())
    sleep(0.01)

    file_data = client_socket.recv(current_batch_size)
    while file_data:
        # Show to user
        file_data = str(file_data.decode())
        print(file_data)
        new_data = input("Enter new data: ")

        if new_data != file_data:
            client_socket.send("Y".encode())
            sleep(0.01)
            client_socket.send(new_data.encode())
        else:
            client_socket.send("N".encode())
        file_data = client_socket.recv(current_batch_size)

    print(f"{filename} edited successfully")


@create_connection
def find_substring(filename, substring, start_line, end_line, *, client_socket):
    """Find substring in file"""
    client_socket.send("Find".encode())
    sleep(0.01)

    client_socket.send(filename.encode())
    sleep(0.01)
    client_socket.send(substring.encode())
    sleep(0.01)
    client_socket.send(str(start_line).encode())
    sleep(0.01)
    client_socket.send(str(end_line).encode())
    sleep(0.01)

    result = client_socket.recv(batch_size).decode()
    if result == "Y":
        line_numbers = client_socket.recv(batch_size).decode()
        print(f"Substring found in line {line_numbers}")
    else:
        print("Substring not found")


# Constants
host = '127.0.0.1'
port = 12345
batch_size = 1024
