import asyncio
import os
import time
from asyncio import IncompleteReadError
from logging import basicConfig, StreamHandler, DEBUG, warning
from logging import info, error, debug
from string import digits, ascii_lowercase
from typing import TypedDict, Literal

basicConfig(
    level=DEBUG,
    format='%(asctime)s [%(levelname)s]: %(message)s',
    handlers=[StreamHandler()],
    encoding='utf-8'
)

BATCH_SIZE = 1024

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

    host: str
    port: int


def id2scrap(file_id: int) -> str:
    """Convert file id to scrap

    :param file_id: id of file in database
    :return: Name of file in storage
    """
    alpha = digits + ascii_lowercase
    base = len(alpha)
    string = ""
    while file_id > 0:
        string = alpha[file_id % base] + string
        file_id //= base
    return string + ".txt#"


async def add_file(storage: Storage, file_id: int, file_name: str, file_folder: str) -> dict[str, str]:
    try:
        reader, writer = await asyncio.open_connection(storage["host"], storage["port"])
    except ConnectionRefusedError:
        return {f"{storage['host']}:{storage['port']}": "Fail"}
    # Send command
    writer.write("Add#".encode())
    # Send filename
    writer.write(id2scrap(file_id).encode())
    await writer.drain()
    # Send file data
    counter = 0
    total = os.path.getsize(os.path.join(file_folder, file_name)) / BATCH_SIZE
    with open(os.path.join(file_folder, file_name), 'rb') as file:
        file_data = file.read(BATCH_SIZE)
        while file_data:
            writer.write(file_data)
            file_data = file.read(BATCH_SIZE)
            counter += 1
            debug(f"Progress: {counter / total * 100:.2f}%")

    writer.write_eof()
    try:
        _ = await reader.readuntil("#".encode())
    except IncompleteReadError:
        return {f"{storage['host']}:{storage['port']}": "Fail"}
    return {f"{storage['host']}:{storage['port']}": "OK"}


async def delete_file(storage: Storage, file_id: int) -> None:
    reader, writer = await asyncio.open_connection(storage["host"], storage["port"])
    # Send command
    writer.write("Delete#".encode())
    # Send filename
    writer.write(id2scrap(file_id).encode())
    writer.close()
    await writer.wait_closed()


async def download_file(storage: Storage, file_id: int, file_name: str, file_folder: str) -> bool:
    try:
        reader, writer = await asyncio.open_connection(storage["host"], storage["port"])
    except ConnectionRefusedError:
        return False
    # Send command
    writer.write("Get#".encode())
    # Send filename
    writer.write(id2scrap(file_id).encode())
    await writer.drain()
    # Receive file data
    with open(os.path.join(file_folder, file_name), 'wb') as file:
        file_data = await reader.read(BATCH_SIZE)
        while file_data:
            file.write(file_data)
            file_data = await reader.read(BATCH_SIZE)
    await writer.drain()
    writer.close()
    await writer.wait_closed()
    return True


async def find_substring(storage: Storage, file_id: int, start: int, stop: int, substring: str) -> [str]:
    reader, writer = await asyncio.open_connection(storage["host"], storage["port"])
    # Send command
    writer.write("Find#".encode())
    # Send filename
    writer.write(id2scrap(file_id).encode())
    # Send start and stop
    writer.write(f"{start}#{stop}#".encode())
    # Send substring
    writer.write(substring.encode())
    writer.write_eof()

    found = await reader.readuntil("#".encode())
    if found.decode() == "Y#":
        found_lines = ""
        found_data = await reader.read(BATCH_SIZE)
        while found_data:
            found_lines += found_data.decode()
            found_data = await reader.read(BATCH_SIZE)
        writer.close()
        await writer.wait_closed()
        return found_lines.split(";")
    elif found.decode() == "N#":
        writer.close()
        await writer.wait_closed()
        return []
    else:
        error("Wrong response from storage")
        writer.close()
        await writer.wait_closed()
        return []


async def get_info(storage: Storage) -> list[int]:
    reader, writer = await asyncio.open_connection(storage["host"], storage["port"])
    writer.write("Info#".encode())
    data = await reader.readuntil("#".encode())
    data = data.decode()[:-1]
    nums = list(map(int, data.split('/')))
    return nums


async def end_server(storage: Storage) -> None:
    reader, writer = await asyncio.open_connection(storage["host"], storage["port"])
    # Send command
    writer.write("End#".encode())
    writer.close()
    await writer.wait_closed()


async def add_server(storage: Storage, new_storage: Storage) -> None:
    reader, writer = await asyncio.open_connection(storage["host"], storage["port"])
    # Send command
    writer.write("AddServer#".encode())
    # Send new storage host
    writer.write(new_storage["host"].encode() + "#".encode())
    # Send new storage port
    writer.write(str(new_storage["port"]).encode() + "#".encode())
    writer.close()
    await writer.wait_closed()


async def ping_server(storage: Storage) -> dict[str, int]:
    start_time = time.time()

    reader, writer = await asyncio.open_connection(storage["host"], storage["port"])
    writer.write("Ping#".encode())
    await reader.readuntil("#".encode())
    writer.close()
    await writer.wait_closed()

    end_time = time.time()
    response_time = end_time - start_time
    return {f"{storage['host']}:{storage['port']}": round(response_time * 1000)}


async def manage(mode: Literal["add", "delete", "get", "find", "copy", "end", "ping", "remove"],
                 file_id: int = -1,
                 filename: str = "",
                 storages: list[Storage] = None,
                 *,
                 substring: str = "",
                 lines: int = 0,
                 file_folder: str = "",
                 destination_folder: str = "",
                 storage: Storage = None,
                 files: list[dict] = None,
                 ) -> list[int] | dict[str, int] | None:
    if storage is None:
        storage = {}
    if storages is None:
        storages = []
    if files is None:
        files = []

    try:
        match mode:
            case "add":
                tasks = [asyncio.create_task(add_file(s, file_id, filename, file_folder))
                         for s in storages]

                response, _ = await asyncio.wait(tasks)
                result = {}
                for e in response:
                    result.update(e.result())
                return result
            case "delete":
                tasks = [asyncio.create_task(delete_file(s, file_id))
                         for s in storages]

                await asyncio.wait(tasks)
            case "get":
                for storage in storages:
                    if await download_file(storage, file_id, filename, destination_folder):
                        break
            case "find":
                if len(storages) == 0:
                    return
                amount_of_lines = lines // min(lines, len(storages))
                task = []
                line = 1
                for i, storage_object in enumerate(storages):
                    if line > lines:
                        break
                    if i == len(storages) - 1:
                        amount_of_lines = lines - line

                    info(f"Split by {line}:{line + amount_of_lines}")
                    task.append(asyncio.create_task(
                        find_substring(storage_object, file_id, line, line + amount_of_lines, substring)
                    ))
                    line += amount_of_lines + 1

                response, _ = await asyncio.wait(task)
                result = []
                for e in response:
                    result.extend(list(map(int, e.result())))
                return result
            case "copy":
                if len(storages) == 0:
                    return
                await add_server(storages[0], storage)
            case "end":
                await end_server(storage)
            case "info":
                return await get_info(storage)
            case "ping":
                tasks = [asyncio.create_task(ping_server(s))
                         for s in storages]

                response, _ = await asyncio.wait(tasks)
                result = {}
                for e in response:
                    for k, v in e.result().items():
                        result[k] = v
                return result
            case "remove":
                tasks = [asyncio.create_task(delete_file(s, f["id"]))
                         for s in storages for f in files]
                await asyncio.wait(tasks)
            case _:
                warning("Unknown mode")
    except ConnectionRefusedError:
        warning("ConnectionRefusedError")
    except ValueError:
        warning("Server List is empty")
    except IndexError:
        warning("Server List is empty")


if __name__ == '__main__':
    print(asyncio.run(manage(
        "ping", storages=debug_storages
    )))
