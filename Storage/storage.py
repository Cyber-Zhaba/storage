import asyncio
import os.path
import shutil
from logging import basicConfig, INFO, StreamHandler, warning
from logging import info
from shutil import rmtree

from yaml import safe_load


async def read(reader, sep: str = "#"):
    data = await reader.readuntil(sep.encode())
    return data.decode()[:-1]


async def add_file(reader, writer):
    filename = await read(reader)
    info(f"Received {filename}")

    with open(os.path.join("root", filename), 'wb') as file:
        file_data = await reader.read(BATCH_SIZE)
        while file_data:
            file.write(file_data)
            file_data = await reader.read(BATCH_SIZE)
    writer.write("OK#".encode())
    info(f"{filename} received successfully")


async def delete_file(reader):
    filename = await read(reader)
    os.remove(os.path.join("root", filename))
    info(f"{filename} deleted successfully")


async def get_file(reader, writer):
    filename = await read(reader)
    with open(os.path.join("root", filename), 'rb') as file:
        file_data = file.read(BATCH_SIZE)
        while file_data:
            writer.write(file_data)
            file_data = file.read(BATCH_SIZE)
    await writer.drain()
    info(f"{filename} sent successfully")


async def find_substring(reader, writer):
    filename = await read(reader)
    start = await read(reader)
    start = int(start)
    stop = await read(reader)
    stop = int(stop)

    substring = ""
    file_data = await reader.read(BATCH_SIZE)
    while file_data:
        substring += file_data.decode()
        file_data = await reader.read(BATCH_SIZE)

    info(f"Searching for {substring.__repr__()} in {filename} from {start} to {stop}")

    line_number = 0
    found_lines = []
    with open("root\\" + filename, 'r', encoding='utf-8') as file:
        while line := file.readline():
            line_number += 1
            if start <= line_number <= stop:
                if substring in line:
                    found_lines.append(str(line_number))
            elif stop < line_number:
                break

    if found_lines:
        writer.write("Y#".encode())
        await writer.drain()
        writer.write(';'.join(found_lines).encode())
        info(f"Found {len(found_lines)} lines")
    else:
        writer.write("N#".encode())
        info("Substring not found")
    await writer.drain()
    info(f"{filename} sent successfully")


def end():
    info("Removing root dir...")
    rmtree("root")
    info("root dir was successfully removed")
    loop = asyncio.get_running_loop()
    loop.stop()
    info("Session is ended")


async def send_file(host, port, filename):
    reader, writer = await asyncio.open_connection(host, port)
    writer.write("Add#".encode())
    writer.write((filename + "#").encode())
    await writer.drain()

    with open(os.path.join("root", filename), 'rb') as file:
        file_data = file.read(BATCH_SIZE)
        while file_data:
            writer.write(file_data)
            file_data = file.read(BATCH_SIZE)

    await writer.drain()
    writer.close()
    await writer.wait_closed()


async def add_server(reader):
    async def create_task(args):
        func, *args = args
        await func(*args)

    host = await read(reader)
    port = await read(reader)
    port = int(port)

    tasks = [asyncio.create_task(send_file(host, port, f))
             for f in os.listdir('root') if os.path.isfile(os.path.join('root', f))]

    await asyncio.wait(tasks)


async def get_info(writer):
    total, _, free = shutil.disk_usage("/")
    writer.write(f"{free}/{total}#".encode())


async def ping(writer):
    writer.write("OK#".encode())


async def handle_client(reader, writer):
    addr = writer.get_extra_info('peername')
    info(f"Connection from {addr}")

    command = await read(reader)
    info(f"Received {command} from {addr}")

    match command:
        case "Add":
            await add_file(reader, writer)
        case "Delete":
            await delete_file(reader)
        case "Get":
            await get_file(reader, writer)
        case "Find":
            await find_substring(reader, writer)
        case "AddServer":
            await add_server(reader)
        case "End":
            end()
        case "Info":
            await get_info(writer)
        case "Ping":
            await ping(writer)
        case _:
            warning(f"Unknown command {command} from {addr}")

    writer.close()
    await writer.wait_closed()
    info(f"Connection closed from {addr}")


async def main():
    server = await asyncio.start_server(handle_client, HOST, PORT)

    addr = server.sockets[0].getsockname()
    info(f'Serving on {addr}...')

    async with server:
        await server.serve_forever()


if __name__ == '__main__':
    basicConfig(
        level=INFO,
        format='%(asctime)s [%(levelname)s]: %(message)s',
        handlers=[StreamHandler()],
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

    BATCH_SIZE = cfg['batch_size']
    HOST, PORT = cfg['host'], cfg['port']
    try:
        asyncio.run(main())
    except RuntimeError:
        pass
    except Exception as er:
        warning(er)
