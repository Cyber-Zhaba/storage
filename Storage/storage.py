"""Storage server"""
import logging
import os
import socket
import sys
from logging import info, warning
from shutil import rmtree
from time import sleep

from yaml import safe_load


def run_server(host: str, port: int) -> None:
    """Run the server

    :param host:
    :param port:
    :return:
    """
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))

    server_socket.listen(1)
    server_socket.settimeout(1)
    info(f"Starting server on {host}:{port}")

    try:
        while True:
            info("Waiting for new connection...")
            while True:
                try:
                    client_socket, addr = server_socket.accept()
                except socket.timeout:
                    pass
                else:
                    break

            info(f"Connection from {addr}")
            command = client_socket.recv(batch_size).decode()

            try:
                match command:
                    case "Add":
                        add_file(client_socket)
                    case "Delete":
                        delete_file(client_socket)
                    case "Get":
                        get_file(client_socket)
                    case "Edit":
                        edit_file(client_socket)
                    case "Find":
                        find_substring(client_socket)
                    case "Copy":
                        copy_files(client_socket)
                    case "End":
                        delete_all_files(client_socket)
                    case _:
                        warning("Unknown command")
            except Exception as error_:
                warning(error_)

            client_socket.close()
            info("Connection closed")

    except KeyboardInterrupt:
        server_socket.close()
        info("Server closed")
        sys.exit(0)


def add_file(client_socket: socket.socket) -> None:
    """Receive a file from the central server

    :param client_socket:
    :return:
    """
    filename = client_socket.recv(batch_size).decode()
    if not filename:
        raise ConnectionAbortedError("Failed to receive filename")

    with open("root\\" + filename, 'wb') as file:
        file_data = client_socket.recv(batch_size)
        while file_data:
            file.write(file_data)
            file_data = client_socket.recv(batch_size)
    info(f"{filename} received successfully")


def delete_file(client_socket: socket.socket) -> None:
    """Delete a file

    :param client_socket:
    :return: None
    """
    filename = client_socket.recv(batch_size).decode()

    os.remove("root\\" + filename)

    info(f"{filename} deleted successfully")


def get_file(client_socket: socket.socket) -> None:
    """Send file to the central server

    :param client_socket:
    :return:
    """
    filename = client_socket.recv(batch_size).decode()

    with open("root\\" + filename, 'rb') as file:
        file_data = file.read(batch_size)
        while file_data:
            client_socket.send(file_data)
            file_data = file.read(batch_size)

    info(f"{filename} sent successfully")


def edit_file(client_socket: socket.socket) -> None:
    """Edit a file by single batch

    :param client_socket:
    :return:
    """
    filename = client_socket.recv(batch_size).decode()
    current_batch_size = int(client_socket.recv(batch_size).decode())
    filename = "root\\" + filename

    os.rename(filename, filename + ".tmp")
    aborted = False

    with open(filename, 'wb') as file:
        with open(filename + ".tmp", 'rb') as tmp_file:
            tmp_file_data = tmp_file.read(current_batch_size)
            while tmp_file_data:
                edited = None

                if not aborted:
                    try:
                        client_socket.send(tmp_file_data)
                        edited = client_socket.recv(batch_size).decode() == "Y"
                    except ConnectionAbortedError as error_:
                        aborted = True
                        warning(error_)

                if not edited or aborted:
                    file.write(tmp_file_data)
                else:
                    new_file_data = client_socket.recv(batch_size)
                    file.write(new_file_data)
                tmp_file_data = tmp_file.read(current_batch_size)

    os.remove(filename + ".tmp")
    if not aborted:
        info(f"{filename} edited successfully")


def find_substring(client_socket: socket.socket) -> None:
    """Find substring in a file

    :param client_socket:
    :return:
    """
    filename = client_socket.recv(batch_size).decode()
    substring = client_socket.recv(batch_size).decode()
    start_line = int(client_socket.recv(batch_size).decode())
    end_line = int(client_socket.recv(batch_size).decode())

    line_number = 0
    found_lines = []
    with open("root\\" + filename, 'r', encoding='utf-8') as file:
        while line := file.readline():
            line_number += 1
            if start_line <= line_number <= end_line:
                if substring in line:
                    found_lines.append(str(line_number))
            elif end_line < line_number:
                break
    if found_lines:
        client_socket.send("Y".encode())
        sleep(0.01)
        client_socket.send(';'.join(found_lines).encode())
    else:
        client_socket.send("N".encode())


def copy_files(client_socket: socket.socket) -> None:
    """Copy files from current storage to new one

    :param client_socket:
    :return:
    """
    host = client_socket.recv(batch_size).decode()
    port = client_socket.recv(batch_size).decode()
    if not port.isdigit():
        warning("Wrong Port")
        return
    client_socket.close()

    port = int(port)
    all_files = [f for f in os.listdir('root') if os.path.isfile(os.path.join('root', f))]

    for filename in all_files:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((host, port))
        client_socket.send("Add".encode())
        sleep(0.01)

        client_socket.send(filename.encode())
        sleep(0.01)

        with open(os.path.join('root', filename), 'rb') as file:
            file_data = file.read(batch_size)
            while file_data:
                client_socket.send(file_data)
                file_data = file.read(batch_size)
        client_socket.close()


def delete_all_files(client_socket: socket.socket):
    """Deleting all files from server"""
    info("Removing root dir...")
    rmtree("root")
    info("root dir was successfully removed")
    info("Session is ended")
    sys.exit(0)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s]: %(message)s',
        handlers=[logging.FileHandler("log"), logging.StreamHandler()],
        encoding='utf-8'
    )
    info("Starting new session")

    try:
        os.mkdir("root")
        info("Created root directory")
    except FileExistsError:
        info("Root directory already exists")

    with open("config.yaml", "r", encoding='utf-8') as cfg_file:
        cfg = safe_load(cfg_file)

    batch_size = cfg['batch_size']

    run_server(host=cfg["host"], port=cfg["port"])
