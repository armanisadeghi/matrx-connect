from ..socket.core import get_app_factory


async def execute(service_name, task_data):
    service_factory = get_app_factory()

    try:
        results= await service_factory.process_single_request(sid="api-request", user_id="system", data=task_data or {},
                                                     namespace="/UserSession",
                                                     service_name=service_name)
        return {
            "success": True,
            "message": None,
            "response": results
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"An error occurred: {e}",
            "response": None
        }
