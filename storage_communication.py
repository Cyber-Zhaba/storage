"""Module for communication between server and storage"""
import asyncio
import os
import socket
from logging import INFO, basicConfig, FileHandler, StreamHandler
from logging import info, warning, error
from string import ascii_letters, digits
from time import sleep
from typing import TypedDict, TypeAlias, Literal, Callable, Any

basicConfig(
    level=INFO,
    format='%(asctime)s [%(levelname)s]: %(message)s',
    handlers=[FileHandler("log"), StreamHandler()],
    encoding='utf-8'
)
batch_size = 1024
debug_storages = [
    {"host": "127.0.0.1", "port": 1111},
    {"host": "127.0.0.1", "port": 2222},
    {"host": "127.0.0.1", "port": 3333},
    {"host": "127.0.0.1", "port": 4444},
]


class Storage(TypedDict):

    """Represents a storage entity with host and port information.

    It is a TypedDict which means it expects specific keys with their associated types.
    The keys are:
    - host: An integer representing the host information.
    - port: An integer representing the port information.
    """

    host: int
    port: int


Mode: TypeAlias = Literal["add", "delete", "get", "edit", "find"]


def id2scrap(file_id: int) -> str:
    """Convert file id to scrap

    :param file_id: id of file in database
    :return: Name of file in storage
    """
    alpha = digits + ascii_letters
    base = len(alpha)
    string = ""
    while file_id > 0:
        string = alpha[file_id % base] + string
        file_id //= base
    return string + ".txt"


def create_connection(func: Callable[..., Any]) -> Callable:
    """Create a connection to the server"""

    def wrapper(*args, **kwargs):  # noqa: ANN202 ANN002 ANN003
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        host, port = None, None
        for p in args:
            if isinstance(p, dict):
                host, port = p["host"], p["port"]

        if not (host and port):
            error("Couldn't find storage in args")
            return

        client_socket.connect((host, port))
        info(f"Connected to {host}:{port}")

        result = func(*args, client_socket, **kwargs)
        client_socket.close()
        return result

    return wrapper


@create_connection
def add_file(file_id: int, filename: str, file_folder: str, s: Storage,
             client_socket: socket.socket) -> None:
    """Add file to storage

    :param file_id: id of file in database
    :param filename: name of uploaded file
    :param file_folder: folder where file is located
    :param s: host and port of storage
    :param client_socket: client socket
    """
    client_socket.send("Add".encode())
    sleep(0.01)

    client_socket.send(id2scrap(file_id).encode())
    sleep(0.01)

    with open(os.path.join(file_folder, filename), 'rb') as file:
        file_data = file.read(batch_size)
        while file_data:
            client_socket.send(file_data)
            file_data = file.read(batch_size)

    info(f"{filename} sent successfully")


@create_connection
def delete_file(file_id: int, filename: str, file_folder: str, s: Storage,
                client_socket: socket.socket) -> None:
    """Delete file from storage

    :param file_id: id of file in database
    :param filename: name of uploaded file
    :param file_folder: OPTIONAL
    :param s: host and port of storage
    :param client_socket: client socket
    """
    client_socket.send("Delete".encode())
    sleep(0.01)

    client_socket.send(id2scrap(file_id).encode())
    sleep(0.01)

    info(f"{filename} deleted successfully")


@create_connection
def get_file(file_id: int, filename: str, destination_folder: str, s: Storage,
             client_socket: socket.socket) -> None:
    """Download file from storage

    :param file_id: id of file in database
    :param filename: name of uploaded file
    :param destination_folder: folder where file will be downloaded
    :param s: host and port of storage
    :param client_socket: client socket
    """
    client_socket.send("Get".encode())
    sleep(0.01)

    client_socket.send(id2scrap(file_id).encode())
    sleep(0.01)

    with open(os.path.join(destination_folder, filename), 'wb') as file:
        file_data = client_socket.recv(batch_size)
        while file_data:
            file.write(file_data)
            file_data = client_socket.recv(batch_size)

    info(f"{filename} received successfully")


@create_connection
def edit_file(file_id: int, filename: str, s: Storage,
              client_socket: socket.socket) -> None:
    """Edit file in storage

    :param file_id: id of file in database
    :param filename: name of uploaded file
    :param s: host and port of storage
    :param client_socket: client socket
    """
    client_socket.send("Edit".encode())
    sleep(0.01)

    client_socket.send(id2scrap(file_id).encode())
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

        if new_data == "quit":
            break

        if new_data != file_data:
            client_socket.send("Y".encode())
            sleep(0.01)
            client_socket.send(new_data.encode())
        else:
            client_socket.send("N".encode())
        file_data = client_socket.recv(current_batch_size)

    info(f"{filename} edited successfully")


@create_connection
def find_substring(file_id: int, substring: str, start: int, end: int, s: Storage,
                   client_socket: socket.socket) -> str:
    """Find substring in file

    :param file_id: id of file in database
    :param substring: substring to find
    :param start: start line
    :param end: end line
    :param s: host and port of storage
    :param client_socket: client socket
    :return: result of search
    """
    client_socket.send("Find".encode())
    sleep(0.01)

    client_socket.send(id2scrap(file_id).encode())
    sleep(0.01)
    client_socket.send(substring.encode())
    sleep(0.01)
    client_socket.send(str(start).encode())
    sleep(0.01)
    client_socket.send(str(end).encode())
    sleep(0.01)

    result = client_socket.recv(batch_size).decode()
    if result == "Y":
        line_numbers = client_socket.recv(batch_size).decode()
        return f"Substring found in line {line_numbers}"
    else:
        return "Substring not found"


mode2func = {"add": add_file,
             "delete": delete_file,
             "get": get_file,
             "edit": edit_file,
             "find": find_substring}


async def manage(mode: Mode, file_id: int, filename: str, storages: list[Storage], *,
                 substring: str = "", lines: int = 0, file_folder: str = "",
                 destination_folder: str = "") -> list[str] | None:
    """Manage storages
    
    Examples of usage
    
    - Add file "a.txt" located in "downloads", id of file is 15
    asyncio.run(manage("add", 15, "a.txt", storages, file_folder="downloads"))

    - Delete file "a.txt", id of file 15
    asyncio.run(manage("delete", 15, "a.txt", storages))

    - Get file "a.txt", id 15 from storage and download in "tmp" root
    asyncio.run(manage("get", 15, "file.txt", debug_storages, destination_folder="tmp"))

    - Edit file "a.txt"
    asyncio.run(manage("edit", 15, "a.txt", debug_storages))

    - Find substring "SDh" in file "a.txt"
    asyncio.run(manage("find", 15, "a.txt", debug_storages, substring="SDh", number_of_lines=50))


    :param mode: mode of managing. Can be "add", "delete", "get", "edit", "find"
    :param file_id: id of file in database
    :param filename: name of uploaded file
    :param storages: list of hosts and ports of storages with actual version of file
    :param substring: OPTIONAL substring to find
    :param lines: OPTIONAL amount of lines in file
    :param file_folder: OPTIONAL folder where file is located
    :param destination_folder: OPTIONAL folder where file will be downloaded
    :return: OPTIONAL result of search substring in file
    """
    responses = []

    async def create_task(args):  # noqa: ANN202 ANN001
        """Create task for asyncio loop"""
        f, *args = args
        resp = await loop.run_in_executor(None, f, *args)
        responses.append(resp)

    match mode:
        case "add" | "delete":
            loop = asyncio.get_event_loop()
            func = mode2func[mode]
            tmp_task = [(func, file_id, filename, file_folder, storage)
                        for storage in storages]

            await asyncio.wait([loop.create_task(create_task(f)) for f in tmp_task])
        case "get":
            get_file(file_id, filename, destination_folder, storages[0])
        case "edit":
            edit_file(file_id, filename, storages[0])
            get_file(file_id, filename, destination_folder, storages[0])
            await manage("add", file_id, filename, storages,
                         lines=lines, destination_folder=destination_folder)
            os.remove(os.path.join(destination_folder, filename))
        case "find":
            amount_of_lines = lines // min(lines, len(storages))
            tmp_task = []
            f = find_substring
            line = 1
            for i, storage in enumerate(storages):
                if line > lines:
                    break
                if i == len(storages) - 1:
                    amount_of_lines = lines - line

                info(f"{line} {line + amount_of_lines}")
                tmp_task.append(
                    (f, file_id, substring, line, line + amount_of_lines, storage)
                )
                line += amount_of_lines + 1

            loop = asyncio.get_event_loop()
            await asyncio.wait([loop.create_task(create_task(f)) for f in tmp_task])
            return responses
        case _:
            warning("Unknown mode")