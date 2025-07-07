from matrx_utils.conf import settings

from ..core.service_base import SocketServiceBase
from ...socket.core.app_factory import get_registered_services
from ...socket.schema import get_runtime_schema


class AdminServiceBase(SocketServiceBase):
    def __init__(self):
        self.redacted = None
        self.filter = None
        self.remote_logs = None
        self.log_name = None
        self.database_project_name = None
        self.table_name = None
        self.limit = None
        self.setting_name = None
        self.stream_handler = None
        self.mic_check_message = None

        super().__init__(
            app_name="admin-service",
            service_name="AdminService",
            log_level="INFO",
            batch_print=False,
        )

    async def process_task(self, task, task_context=None, process=True):
        return await self.execute_task(task, task_context, process)

    async def mic_check(self):
        await self.stream_handler.send_chunk(
            "[ADMIN SERVICE] Mic Check Response to: "
            + self.mic_check_message
        )
        await self.stream_handler.send_end()

    async def get_environment(self):
        try:
            if self.redacted:
                all_settings = settings.list_settings_redacted()
            else:
                all_settings = settings.list_settings()

            if self.filter is not None:
                filter_lower = self.filter.lower()
                all_settings = {
                    key: value for key, value in all_settings.items()
                    if filter_lower in key.lower()
                }
            await self.stream_handler.send_data_final(all_settings)
        except Exception as e:
            await self.stream_handler.send_error(
                error_type="settings_error",
                message=f"There was a problem accessing settings: {e}",
                user_visible_message="Error with application startup."
            )
            await self.stream_handler.send_end()

    async def list_logs(self):
        await self.stream_handler.send_error(
            error_type="task_not_implemented",
            message=f"This task is not implemented yet",
            user_visible_message="This task is not implemented yet"
        )

        await self.stream_handler.send_end()

    async def get_log(self):
        await self.stream_handler.send_error(
            error_type="task_not_implemented",
            message=f"This task is not implemented yet",
            user_visible_message="This task is not implemented yet"
        )

        await self.stream_handler.send_end()

    async def test_database_connection(self):
        await self.stream_handler.send_error(
            error_type="task_not_implemented",
            message=f"This task is not implemented yet",
            user_visible_message="This task is not implemented yet"
        )

        await self.stream_handler.send_end()

    async def get_registered_databases(self):
        await self.stream_handler.send_error(
            error_type="task_not_implemented",
            message=f"This task is not implemented yet",
            user_visible_message="This task is not implemented yet"
        )

        await self.stream_handler.send_end()

    async def get_registered_services(self):
        try:
            services = get_registered_services()
            await self.stream_handler.send_data_final(services)
        except Exception as e:
            await self.stream_handler.send_error(
                error_type="app_factory_not_configured",
                message=f"App factory is not configured: {e}",
                user_visible_message="Error with application startup."
            )
            await self.stream_handler.send_end()

    async def get_application_schema(self):
        try:
            schema = get_runtime_schema()
            await self.stream_handler.send_data_final(schema)

        except Exception as e:
            await self.stream_handler.send_error(
                error_type="schema_error",
                message=f"schema not found or configured correctly: {e}",
                user_visible_message="An error occurred. Please try again later."
            )
            await self.stream_handler.send_end()
