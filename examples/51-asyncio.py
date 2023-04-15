import asyncio
import functools
import msvcrt
import sys
from typing import Any, Coroutine, Iterable, MutableSet


SERVER_PORT = 3030
MESSAGE_MAX_SIZE = 10240


INETAddress = tuple[str, int] | tuple[str, int, int, int]


###############################################################################
## Server                                                                    ##
###############################################################################


def create_background_task(coro: Coroutine[Any, Any, Any], bg_tasks: MutableSet[asyncio.Task[Any]]):
    task = asyncio.create_task(coro)
    bg_tasks.add(task)
    task.add_done_callback(bg_tasks.discard)
    return task


async def handle_client_connection(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    *,
    lock: asyncio.Lock,
    connections: dict[INETAddress, asyncio.StreamWriter],
):
    background_tasks: set[asyncio.Task[Any]] = set()
    addr = writer.get_extra_info("peername")
    async with lock:
        connections[addr] = writer
    print(f"Connection de {addr}")

    client_data = {
        "addr": addr,
        "connections": connections,
        "lock": lock,
    }

    try:
        read_message_task = create_background_task(reader.readline(), background_tasks)

        message = "Bienvenu sur le tchat !"
        create_background_task(send_message(message, writer), background_tasks)

        while background_tasks:
            await asyncio.wait(background_tasks, return_when=asyncio.FIRST_COMPLETED)
            if read_message_task.done():
                message = await read_message_task
                if message:
                    create_background_task(
                        receive_data(message, client_data), background_tasks
                    )
                    read_message_task = create_background_task(
                        reader.readline(), background_tasks
                    )
                else:
                    break

    finally:
        async with lock:
            del connections[addr]
        writer.close()
        await writer.wait_closed()
        print(f"Déconnexion de {addr}")


async def send_data(data: bytes, writer: asyncio.StreamWriter):
    peername = writer.get_extra_info("peername")
    print(f"Envoi {data!r} à {peername}")
    writer.write(data)
    await writer.drain()


async def send_message(message: str, writer: asyncio.StreamWriter):
    if not message.endswith("\n"):
        message += "\n"
    await send_data(message.encode(), writer)


async def broadcast_message(message: str, writers: Iterable[asyncio.StreamWriter]):
    if not message.endswith("\n"):
        message += "\n"
    data = message.encode()
    for writer in writers:
        await send_data(data, writer)


async def process_command(command: str, client_data: dict[str, Any]):
    client_addr = client_data["addr"]
    client_writer = client_data["connections"][client_addr]
    others_writer = (
        writer
        for writer in client_data["connections"].values()
        if writer is not client_writer
    )
    command_parts = command.split()
    match command_parts:
        case ["/pseudo", name]:
            client_data["pseudo"] = name
            await send_message(f"Bienvenue {name}", client_writer)
            await broadcast_message(f"{name} est dans la place !", others_writer)
        case _:
            await send_message(f"Erreur commande inconnue: '{command}'", client_writer)


async def receive_data(data: bytes, client_data: dict[str, Any]):
    client_addr = client_data["addr"]
    connections = client_data["connections"]
    client_writer = connections[client_addr]
    message = data.decode()
    print(f"Reçu {data!r} de {client_addr}")

    command = message.strip()
    if command.startswith("/"):
        await process_command(command, client_data)
    elif "pseudo" not in client_data:
        message = "Spécifiez votre pseudo pour envoyer un message avec la commande:\n /pseudo mon_pseudo"
        await send_message(message, connections[client_addr])
    else:
        message = f"{client_data['pseudo']}> {message}"
        await broadcast_message(
            message,
            (writer for writer in connections.values() if writer is not client_writer),
        )


async def server_main(host: str, port: int | str):
    connections = {}
    lock = asyncio.Lock()
    client_connected_cb = functools.partial(
        handle_client_connection, lock=lock, connections=connections
    )
    try:
        server = await asyncio.start_server(client_connected_cb, host, port)
        addrs = ", ".join(str(sock.getsockname()) for sock in server.sockets)
        print(f"Serveur en écoute {addrs}")

        async with server:
            await server.serve_forever()
    except OSError as err:
        print(err)


###############################################################################
## Client                                                                    ##
###############################################################################

current_input_line = bytearray()


async def readline(echo: bool = True) -> str:
    global current_input_line
    current_input_line.clear()
    end_of_line = False

    while not end_of_line:
        while msvcrt.kbhit():
            key_pressed = msvcrt.getch()
            if key_pressed in b"\x00\xe0":
                key_pressed += msvcrt.getch()
            elif key_pressed == b"\x03":
                raise KeyboardInterrupt
            elif key_pressed == b"\r":
                current_input_line += b"\n"
                msvcrt.putch(b"\n")
                end_of_line = True
                break
            elif key_pressed == b"\x08":
                if len(current_input_line) > 0:
                    current_input_line = current_input_line[:-1]
                    if echo:
                        # print("\b \b", end="", flush=True)
                        msvcrt.putch(b"\b")
                        msvcrt.putch(b" ")
                        msvcrt.putch(b"\b")
            else:
                current_input_line += key_pressed
                msvcrt.putch(key_pressed)
        else:
            await asyncio.sleep(0.03)
    return get_input_line()


def get_input_line():
    global current_input_line
    return current_input_line.decode("cp850", errors="ignore")


async def client_main(host: str, port: int | str):
    prompt = "# "
    reader: asyncio.StreamReader | None = None
    writer: asyncio.StreamWriter | None = None
    try:
        reader, writer = await asyncio.open_connection(host, port)
        print(f"Connecté à {host}:{port}")
        read_message_task = asyncio.create_task(reader.readline())

        print(f"\33[2K\r{prompt}", end="", flush=True)
        read_input_task = asyncio.create_task(readline())

        message = ""
        while message.strip().lower() != "bye":
            await asyncio.wait(
                (read_input_task, read_message_task),
                return_when=asyncio.FIRST_COMPLETED,
            )
            if read_input_task.done():
                message = await read_input_task
                writer.write(message.encode())
                await writer.drain()
                print(prompt, end="", flush=True)
                read_input_task = asyncio.create_task(readline())
            if read_message_task.done():
                received_data = await read_message_task
                if not received_data:
                    print("\33[2K\rConnexion terminée")
                    break
                received_message = received_data.decode()
                edited_message = get_input_line()
                print(
                    f"\33[2K\r{received_message}{prompt}{edited_message}",
                    end="",
                    flush=True,
                )
                read_message_task = asyncio.create_task(reader.readline())
    except ConnectionError as err:
        print(f"\n{err}")
    finally:
        if writer and not writer.is_closing():
            writer.close()
            await writer.wait_closed()


###############################################################################
## Main                                                                      ##
###############################################################################

if __name__ == "__main__":
    start_server = False
    host = ""
    port = SERVER_PORT

    i = 1
    while i < len(sys.argv):
        argument = sys.argv[i]
        if argument == "-s":
            start_server = True
        elif argument == "-h":
            i += 1
            if i == len(sys.argv):
                print("Adresse du serveur manquante.", file=sys.stderr)
                exit(1)
            host = sys.argv[i]
        elif argument == "-p":
            i += 1
            if i == len(sys.argv):
                print("Port du serveur manquant.", file=sys.stderr)
                exit(1)
            port = sys.argv[i]
        else:
            print(f"Option invalide: {argument}", file=sys.stderr)
            exit(1)
        i += 1

    if start_server:
        main = server_main
    else:
        main = client_main
    try:
        asyncio.run(main(host, port))
    except KeyboardInterrupt:
        print("Interruption du programme")
