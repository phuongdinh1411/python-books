import selectors
import socket
import asyncio

from selectors import SelectorKey
from types import TracebackType
from typing import List, Optional, Tuple, Type


class ConnectedSocket:
    def __init__(self, server_socket):
        self._connection = None
        self._server_socket = server_socket

    async def __aenter__(self):
        loop = asyncio.get_event_loop()
        connection, address = await loop.sock_accept(self._server_socket)
        self._connection = connection
        return self._connection

    async def __aexit__(self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType]):
        self._connection.close()
        
    

# async def echo(connection, loop: asyncio.AbstractEventLoop):
#     while data := loop.sock_recv(connection, 1024):
#         await loop.sock_sendall(connection, data)


async def main():
    server_socket = socket.socket()
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    server_address = ('127.0.0.1', 8000)
    server_socket.setblocking(False)
    server_socket.bind(server_address)
    server_socket.listen()

    #await listen_on_connection(server_socket, asyncio.get_event_loop())
    loop = asyncio.get_event_loop()
    async with ConnectedSocket(server_socket) as connection:
        data = await loop.sock_recv(connection, 1024)
        print(data)

asyncio.run(main())