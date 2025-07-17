import asyncio
from typing import Dict, Any
from matrx_utils import settings
from ..socket.core import get_app_factory
from ..socket.core.request_base import validate_object_structure
from ..socket.schema import get_schema_validator
from .http_stream_handler import HTTPStreamHandler


class HTTPExecutor:
    """
    Unified HTTP executor supporting both direct and validated execution modes.

    - Direct mode: Bypasses validation, sets taskData as service attributes directly
    - Validated mode: Full pipeline with schema validation, conversion, etc.
    """

    def __init__(self):
        self.service_factory = None
        self.schema_validator = None

    def _get_service_factory(self):
        """Get or create service factory instance"""
        if not self.service_factory:
            self.service_factory = get_app_factory()
        return self.service_factory

    def _get_schema_validator(self):
        """Get or create schema validator instance"""
        if not self.schema_validator:
            self.schema_validator = get_schema_validator()
        return self.schema_validator

    async def _create_service_instance(self, service_name: str, stream_handler: HTTPStreamHandler):
        """
        Create and configure service instance - shared logic for both execution modes
        """

        try:
            service_factory = self._get_service_factory()
            force_new = service_name in getattr(service_factory, 'multi_instance_services', set())
            service_instance = service_factory.create_service(service_name, force_new=force_new)

            # Configure service instance
            service_instance.add_stream_handler(stream_handler)
            service_instance.set_user_id("system")

            return service_instance

        except Exception as e:
            await stream_handler.fatal_error(
                error_type="service_creation_error",
                message=f"Failed to create service {service_name}: {str(e)}"
            )
            return None

    async def execute_direct(self, service_name: str, task_name: str, task_data: Dict[str, Any]):
        """
        Direct execution bypassing schema validation.
        Service factory → Service instance → Set attributes → Execute method directly.

        Args:
            service_name: Name of the service
            task_name: Method name to call on the service
            task_data: Data to set as attributes on service instance

        Yields:
            SSE-formatted HTTP stream chunks
        """
        # Create stream handler
        stream_handler = HTTPStreamHandler(
            event_name=f"direct_{service_name}_{task_name}"
        )

        try:
            # Create service instance
            service_instance = await self._create_service_instance(service_name, stream_handler)
            if not service_instance:
                async for chunk in stream_handler.get_stream():
                    yield chunk
                return

            if task_data:
                for key, value in task_data.items():
                    setattr(service_instance, key, value)

            # Send confirmation
            await stream_handler.send_status_update(
                status="confirm",
                system_message=f"Direct execution started: {service_name}.{task_name}",
                user_visible_message="Processing..."
            )

            # Execute the method directly
            try:
                if hasattr(service_instance, task_name):
                    method = getattr(service_instance, task_name)
                    if callable(method):
                        if asyncio.iscoroutinefunction(method):
                            await method()
                        else:
                            method()
                    else:
                        await stream_handler.send_error(
                            error_type="method_not_callable",
                            message=f"Attribute {task_name} is not callable"
                        )
                else:
                    await stream_handler.send_error(
                        error_type="method_not_found",
                        message=f"Method {task_name} not found on service {service_name}"
                    )
            except Exception as e:
                await stream_handler.send_error(
                    error_type="execution_error",
                    message=f"Method execution failed: {str(e)}"
                )

            # End stream
            await stream_handler.send_end()

        except Exception as e:
            await stream_handler.fatal_error(
                error_type="direct_executor_error",
                message=f"Direct executor error: {str(e)}"
            )

        # Stream the response
        async for chunk in stream_handler.get_stream():
            yield chunk

    async def execute_validated(self, service_name: str, task_name: str, task_data: Dict[str, Any]):
        """
        Full pipeline execution with schema validation, conversion, etc.
        Exact same process as socket system but streaming via HTTP.

        Args:
            service_name: Name of the service
            task_name: Task method name
            task_data: Task data for validation

        Yields:
            SSE-formatted HTTP stream chunks
        """
        stream_handler = HTTPStreamHandler(
            event_name=f"validated_{service_name}_{task_name}"
        )

        try:
            # Build request data in expected format
            request_data = {
                "task": task_name,
                "taskName": task_name,  # Support both formats
                "taskData": task_data,
                "index": 0,
                "stream": True
            }

            # Validate object structure
            task, index, stream, validated_task_data, structure_errors = validate_object_structure(request_data)

            if structure_errors:
                await stream_handler.fatal_error(
                    error_type="structure_validation_error",
                    message="Request structure validation failed",
                    details={"errors": structure_errors}
                )
                async for chunk in stream_handler.get_stream():
                    yield chunk
                return

            # Schema validation
            try:
                primary_service = service_name
                if service_name== "default_service":
                    primary_service = settings.APP_PRIMARY_SERVICE_NAME

                schema_validator = self._get_schema_validator()
                validation_result = schema_validator.validate(
                    validated_task_data, primary_service, task, "system"
                )
                context = validation_result.get("context", {})
                validation_errors = validation_result.get("errors", {})

                if validation_errors:
                    await stream_handler.fatal_error(
                        error_type="schema_validation_error",
                        message="Schema validation failed",
                        details={"errors": validation_errors}
                    )
                    async for chunk in stream_handler.get_stream():
                        yield chunk
                    return

            except Exception as e:
                await stream_handler.fatal_error(
                    error_type="validation_system_error",
                    message=f"Validation system error: {str(e)}"
                )
                async for chunk in stream_handler.get_stream():
                    yield chunk
                return

            # Send validation success
            await stream_handler.send_status_update(
                status="confirm",
                system_message=f"Validation passed: {service_name}.{task}",
                user_visible_message="Validation successful, processing..."
            )

            # Create service instance
            service_instance = await self._create_service_instance(service_name, stream_handler)
            if not service_instance:
                async for chunk in stream_handler.get_stream():
                    yield chunk
                return

            # Execute using the validated pipeline
            try:
                # Use process_task like the socket system
                await service_instance.process_task(task, context, process=True)
            except Exception as e:
                await stream_handler.send_error(
                    error_type="task_execution_error",
                    message=f"Task execution failed: {str(e)}"
                )

            # End stream
            await stream_handler.send_end()

        except Exception as e:
            await stream_handler.fatal_error(
                error_type="validated_executor_error",
                message=f"Validated executor error: {str(e)}"
            )

        # Stream the response
        async for chunk in stream_handler.get_stream():
            yield chunk

    async def execute_with_mode(self, mode: str, service_name: str, task_name: str, task_data: Dict[str, Any]):
        """
        Convenience method to execute with specified mode

        Args:
            mode: "direct" or "validated"
            service_name: Name of the service
            task_name: Task method name
            task_data: Task data

        Yields:
            SSE-formatted HTTP stream chunks
        """
        if mode == "direct":
            async for chunk in self.execute_direct(service_name, task_name, task_data):
                yield chunk
        elif mode == "validated":
            async for chunk in self.execute_validated(service_name, task_name, task_data):
                yield chunk
        else:
            # Create temporary stream handler for error
            stream_handler = HTTPStreamHandler(event_name=f"error_{service_name}_{task_name}")
            await stream_handler.fatal_error(
                error_type="invalid_execution_mode",
                message=f"Invalid execution mode: {mode}. Must be 'direct' or 'validated'"
            )
            async for chunk in stream_handler.get_stream():
                yield chunk