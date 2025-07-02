
import socketio


sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
)

clients = {}
verbose = False


from .core.global_socket_events import *
