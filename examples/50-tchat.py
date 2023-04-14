from dataclasses import dataclass, field
import msvcrt
import select
import socket
import sys
from typing import Iterable


SERVER_PORT = 3030
MESSAGE_MAX_SIZE = 100


@dataclass
class ClientInfo:
    socket: socket.socket
    name: str
    send_buffer: list[bytes] = field(default_factory=list)


ConnectionDict = dict[socket.socket, ClientInfo]


def address_to_str(address: tuple[str, int] | tuple[str, int, int, int]) -> str:
    try:
        host, port, *_ = address
        return f"{host}:{port}"
    except:
        return str(address)


def connection_made(connections: ConnectionDict, client_socket: socket.socket):
    name = address_to_str(client_socket.getpeername())
    print(f"Connection de {name}")
    connections[client_socket] = ClientInfo(client_socket, name)
    send_message(
        "Bienvenue sur le tchat !",
        connections[client_socket],
    )


def terminate_connection(connections: ConnectionDict, client_socket: socket.socket):
    print(f"Déconnexion de {address_to_str(client_socket.getpeername())}")
    client_name = connections[client_socket].name
    del connections[client_socket]
    broadcast_message_to(f"{client_name} est parti.", connections.values())


def cut_message(message: str, max_size: int):
    data = message.encode()
    data_size = len(data)
    if data_size <= max_size:
        yield data
    else:
        while data:
            beginning = data[:max_size].decode(errors="ignore").encode()
            yield beginning
            data = data[len(beginning) :]


def get_data_from_message(message: str, from_name: str):
    message = message.rstrip()
    header = from_name + "> "
    header_data = header.encode()
    footer_data = "\n".encode()
    overhead_size = len(header_data) + len(footer_data)
    return (
        header_data + body_data + footer_data
        for line in message.split("\n")
        for body_data in cut_message(line, MESSAGE_MAX_SIZE - overhead_size)
    )


def send_message(message: str, destination: ClientInfo, from_name: str = ""):
    broadcast_message_to(message, [destination], from_name)


def broadcast_message_to(
    message: str, destinations: Iterable[ClientInfo], from_name: str = ""
):
    for message_data in get_data_from_message(message, from_name):
        for destination in destinations:
            destination.send_buffer.append(message_data)


def process_ready_to_send(connections: ConnectionDict, client_socket: socket.socket):
    if client_socket in connections and connections[client_socket].send_buffer:
        data = connections[client_socket].send_buffer.pop(0)
        client_socket.send(data)
        print(f"Envoi {data!r} à {address_to_str(client_socket.getpeername())}")


def get_ready_to_send(connections: ConnectionDict) -> list[socket.socket]:
    return [client for client, sending_buffer in connections.items() if sending_buffer]


def command_set_name(
    connections: ConnectionDict, client_info: ClientInfo, client_name: str
):
    if any(
        connection.name == client_name
        for connection in connections.values()
        if connection is not client_info
    ):
        send_message(
            f"Impossible de fixer le pseudo à {client_name} car il est déjà utilisé.",
            client_info,
        )
        return
    client_info.name = client_name
    broadcast_message_to(f"{client_name} est dans la place !", connections.values())


def command_help_set_name(connections: ConnectionDict, client_info: ClientInfo):
    send_message("Usage: /pseudo mon_pseudo", client_info)


def command_help(connections: ConnectionDict, client_info: ClientInfo, name: str = ""):
    global commands
    if name:
        if f"/name" in commands:
            name = f"/name"
        if name not in commands:
            send_message(
                f"La commande {name} est inconnue.",
                client_info,
            )
        else:
            help_function = commands[name][3]
            if help_function: # type: ignore [reportUnnecessaryComparison]
                help_function(connections, client_info)
                return
    command_list = "".join(f"\t{command}\n" for command in sorted(commands.keys()))
    send_message("La liste des commandes disponibles:", client_info)
    send_message(command_list, client_info)


def command_help_help(connections: ConnectionDict, client_info: ClientInfo):
    send_message("Usage: /help [commande]", client_info)


commands = {
    "/pseudo": (command_set_name, 1, 1, command_help_set_name),
    "/help": (command_help, 0, 1, command_help_help),
    "/?": (command_help, 0, 1, command_help_help),
    "/toto": (None, 0, 5, None),
}


def process_command(message: str, client_info: ClientInfo, connections: ConnectionDict):
    global commands

    command_name, *params = message.split()
    command_name = command_name.lower()

    if command_name not in commands:
        send_message("Hmm, cette commande m'est inconnue.", client_info)
        return

    command_function, command_param_min, command_param_max, command_help = commands[
        command_name
    ]
    if not (command_param_max >= len(params) >= command_param_min):
        send_message("Erreur: nombre de paramètre invalide", client_info)
        if command_help: # type: ignore [reportUnnecessaryComparison]
            command_help(connections, client_info)
        return
    if command_function: # type: ignore [reportUnnecessaryComparison]
        command_function(connections, client_info, *params)
    else:
        send_message("Arrgh! Cette commande n'est pas implémentée.", client_info)


def data_received(
    connections: ConnectionDict, data: bytes, client_socket: socket.socket
):
    peername = address_to_str(client_socket.getpeername())
    print(f"Reçu {data!r} de {peername}")

    message = data.decode()
    client_info = connections[client_socket]

    if message.startswith("/"):
        process_command(message, client_info, connections)
        return

    # Broadcast the message
    for connection, info in connections.items():
        if connection is not client_socket:
            send_message(message, info, client_info.name)


def server_main(host: str, port: int):
    addresses = socket.getaddrinfo(host, port, family=socket.AF_INET)
    if not addresses:
        print(f"Impossible de résoudre l'adresse {host}:{port}")
        return
    server_address = addresses[0][-1]
    server_socket = socket.socket()
    server_socket.setblocking(False)
    server_socket.bind(server_address)
    server_socket.listen()
    print(f"Serveur en écoute {host}:{port}")

    all_sockets = [server_socket]
    connections: ConnectionDict = {}

    try:
        while all_sockets:
            output_sockets = get_ready_to_send(connections)
            readable_sockets, writable_sockets, error_sockets = select.select(
                all_sockets, output_sockets, all_sockets, 0.1
            )

            for readable_socket in readable_sockets:
                if readable_socket is server_socket:
                    # server socket is ready to accept a connection
                    client_socket, _ = server_socket.accept()
                    client_socket.setblocking(False)
                    all_sockets.append(client_socket)
                    connection_made(connections, client_socket)
                else:
                    try:
                        data = readable_socket.recv(MESSAGE_MAX_SIZE)
                    except ConnectionError:
                        data = None
                    if data:
                        data_received(connections, data, readable_socket)
                    else:
                        terminate_connection(connections, readable_socket)
                        all_sockets.remove(readable_socket)
                        readable_socket.close()

            for writable_socket in writable_sockets:
                process_ready_to_send(connections, writable_socket)

            for error_socket in error_sockets:
                terminate_connection(connections, error_socket)
                all_sockets.remove(error_socket)
                error_socket.close()

    except KeyboardInterrupt:
        pass

    server_socket.close()


_readline_cached_line = ""


def readline(echo: bool = True):
    global _readline_cached_line

    if msvcrt.kbhit():
        key_pressed = msvcrt.getch()
        if key_pressed in b"\x00\xe0":
            key_pressed += msvcrt.getch()
        elif key_pressed == b"\x03":
            raise KeyboardInterrupt
        elif key_pressed == b"\r":
            line = _readline_cached_line + "\n"
            _readline_cached_line = ""
            print(flush=True)
            return line
        elif key_pressed == b"\x08":
            _readline_cached_line = _readline_cached_line[:-1]
            if echo:
                print("\b \b", end="", flush=True)
        else:
            decoded_char = key_pressed.decode("cp850", errors="ignore")
            _readline_cached_line += decoded_char
            print(decoded_char, end="", flush=True)
    return _readline_cached_line


def client_main(host: str, port: int):
    prompt = "# "
    try:
        addresses = socket.getaddrinfo(host, port, family=socket.AF_INET)
        if not addresses:
            print(f"Impossible de résoudre l'adresse {host}:{port}")
            return
        server_address = addresses[0][-1]
        with socket.socket() as client:
            client.connect(server_address)
            print(f"Connecté à {address_to_str(server_address)}")
            client.settimeout(0.001)
            message = ""
            print(f"\33[2K\r{prompt}", end="", flush=True)
            has_said_bye = False
            while not has_said_bye:
                message = readline()
                if message.endswith("\n"):
                    has_said_bye = message.lower() == "bye\n"
                    client.send(message.encode())
                    print(prompt, end="", flush=True)
                    message = ""
                try:
                    data = client.recv(MESSAGE_MAX_SIZE)
                    if data:
                        received_message = data.decode()
                        print(
                            f"\33[2K\r{received_message}{prompt}{message}",
                            end="",
                            flush=True,
                        )
                except socket.timeout:
                    pass
    except KeyboardInterrupt:
        pass
    except ConnectionError as error:
        print("\n" + error.strerror)


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
            port = int(sys.argv[i])
        else:
            print(f"Option invalide: {argument}", file=sys.stderr)
            exit(1)
        i += 1

    if start_server:
        server_main(host, port)
    else:
        client_main(host, port)
