
import socketio


sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
)

clients = {}
verbose = False


from common.socket.services.initialize_handlers import initialize_socketio_handlers


initialize_socketio_handlers()
