from datetime import datetime, timedelta
import importlib
import logging
import uuid
from matrx_connect import sio, get_user_session_namespace, clients
from matrx_utils import vcprint
from matrx_connect import Task, get_task_queue

user_sessions = get_user_session_namespace()

verbose = True


@sio.event
async def connect(sid, _, auth):
    token = auth.get("token")
    vcprint(
        verbose=True,
        data=f"[GLOBAL SOCKET EVENTS] Client connected with session ID: {sid} and token: {token}",
        color="green",
    )
    clients[sid] = {"is_connected": True, "last_acknowledged_chunk": 0}


@sio.event
async def disconnect(sid):
    vcprint(
        verbose=True,
        data=f"[GLOBAL SOCKET EVENTS] Client disconnected with session ID: {sid}",
        color="green",
    )
    if sid in clients:
        clients[sid]["is_connected"] = False


@sio.on("ping", namespace="/UserSession")
async def handle_ping(sid, data):
    """Handle ping requests for keep-alive functionality"""
    vcprint(
        verbose=True,
        data=f"[GLOBAL SOCKET EVENTS] Ping received from {sid}",
        color="cyan",
    )

    if user_sessions.is_authenticated(sid):
        user_sessions.session_expiry[sid] = datetime.now(
        ) + timedelta(minutes=30)

        # Get user ID for logging
        user_id = user_sessions.get_user_id(sid)

        vcprint(
            verbose=True,
            data=f"[GLOBAL SOCKET EVENTS] Extended session for user {user_id} (SID: {sid})",
            color="green",
        )

    # Simply respond with a pong and the same timestamp
    response = {
        "status": "pong",
        "timestamp": data.get("timestamp") if isinstance(data, dict) else None,
        # Current server timestamp in ms
        "server_timestamp": int(datetime.now().timestamp() * 1000)
    }

    # Emit pong response directly back to the client
    await sio.emit("pong", response, room=sid, namespace="/UserSession")

    # Update client's last activity
    if sid in clients:
        clients[sid]["last_ping"] = response["server_timestamp"]

    return response


@sio.on("*", namespace="/UserSession")
async def generic_user_session_event_handler(event=None, sid=None, data=None):
    if verbose:
        print_socket_request(
            handler="[GLOBAL SOCKET EVENTS] Dynamic User Session Event Handler",
            event=event,
            namespace="/UserSession",
            sid=sid,
            data=data,
        )

    user_id, service_factory = await user_sessions.get_user_factory_and_id(sid)

    event_names = []
    # Ensure data is a list to iterate over
    data = [data] if isinstance(
        data, dict) else data if isinstance(data, list) else []

    for item in data:
        # Safely access taskData and response_listener_event
        task_data = item.get("taskData", {}) if isinstance(item, dict) else {}
        response_listener_event = (
            task_data.get("response_listener_event", str(uuid.uuid4()))
            if isinstance(task_data, dict)
            else str(uuid.uuid4())
        )
        event_names.append(response_listener_event)
        # Only set the value if item is a dict and taskData exists or can be created
        if isinstance(item, dict):
            item.setdefault("taskData", {})[
                "response_listener_event"] = response_listener_event

    try:
        task_queue = get_task_queue()
        await task_queue.add_task(Task(service_name=event, user_id=user_id, sid=sid, namespace="/UserSession", data=data))
        response = {"status": "received",
                    "response_listener_events": event_names}
        vcprint(response, title="Response", color="green")
        return response

    except Exception as e:
        vcprint(e, title="Error", color="red")
        sio.emit("error", str(e), room=sid, namespace="/UserSession")


@sio.event
async def user_message(sid, data):
    print_socket_request(
        handler="[ @sio.event('user_message') ]",
        event="user_message",
        namespace="",
        sid=sid,
        data=data,
    )

    vcprint(
        verbose=verbose,
        pretty=True,
        data=",".join(data),
        title=f"[Socket] User Message with SID: {sid}",
        color="cyan",
    )

    page_identifier = data.get("page")
    try:
        module_name = page_identifier
        function_module = importlib.import_module(module_name)
        if hasattr(function_module, "process"):
            response = await function_module.process(data)
            logging.info(f"Response: {response}")
        else:
            response = f"No 'process' function found in module {module_name}"
            logging.warning(response)
    except Exception as e:
        response = f"Error in processing: {e}"
        logging.error(response, exc_info=True)

    await sio.emit("ai_response", response, room=sid)


@sio.on("*")
def any_event(event, sid, data):
    print_socket_request(handler="[ @sio.on('*') ]",
                         event=event, namespace="", sid=sid, data=data)


@sio.on("*", namespace="*")
def any_event_any_namespace(event, namespace, sid, data):
    print_socket_request(
        handler="[ @sio.on('*', namespace='*') ]",
        event=event,
        namespace=namespace,
        sid=sid,
        data=data,
    )


def print_socket_request(handler, event, namespace, sid, data):
    if verbose:
        print("\n")
        start = "=" * 10 + \
            f"  NEW SOCKET EVENT RECEIVED BY {handler}" + "=" * 10
        end = "=" * 25 + "  CONFIRMATION END " + "=" * 25
        vcprint(start, verbose=verbose, color="green")
        vcprint(event, "Event", verbose=verbose, color="blue", inline=True)
        vcprint(namespace, "Namespace", verbose=verbose,
                color="blue", inline=True)
        vcprint(sid, "SID", verbose=verbose, color="blue", inline=True)
        vcprint(data, "Data", verbose=verbose, pretty=True, color="blue")
        print("")
        vcprint(end, verbose=verbose, color="green")
        print("\n")
    else:
        print("\n")
        vcprint(f"NEW SOCKET EVENT RECEIVED BY {handler}", color="blue")
        vcprint(event, "Event", color="blue", inline=True)
        vcprint(namespace, "Namespace", color="blue", inline=True)
        vcprint(sid, "SID", color="blue", inline=True)
        print("\n")


vcprint(
    "[GLOBAL SOCKET EVENTS] Global Socket Events Initialized",
    verbose=True,
    color="green",
    inline=True,
)
