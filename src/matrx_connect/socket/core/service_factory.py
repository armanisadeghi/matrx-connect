import asyncio
from matrx_connect.socket.core import SocketRequestBase
from matrx_utils import vcprint


class ServiceFactory:
    def __init__(self):
        self.services = {}
        self.service_instances = {}
        self.multi_instance_services = set()
        # self.global_broker_system = get_global_broker_system()
        self.register_default_services()

    def get_session_manager(self, sid: str, user_id: str, org_id: str = None,
                           client_id: str = None, project_id: str = None):
        """Enhanced session manager creation with optional scope context"""
        return self.global_broker_system.get_session_manager(
            sid, user_id, org_id, client_id, project_id
        )

    def _extract_session_scope_context(self, data):
        """Extract SESSION-level scope context from request data (not task-specific)"""
        # Look for session-level context that applies to ALL tasks
        # This would come from user preferences, URL params, or session state
        if not data or len(data) == 0:
            return {}

        # Check if there's a session-level scope_context
        session_context = data[0].get('taskData', {}).get('session_scope_context', {})

        return {
            'client_id': session_context.get('client_id'),
            'project_id': session_context.get('project_id')
        }

    def cleanup_session(self, sid: str):
        """Clean up session when socket disconnects"""
        self.global_broker_system.cleanup_session(sid)

    def register_service(self, service_name, service_class):
        self.services[service_name] = service_class

    def register_multi_instance_service(self, service_name, service_class):
        self.services[service_name] = service_class
        self.multi_instance_services.add(service_name)

    def create_service(self, service_name, force_new=False):
        if service_name not in self.services:
            raise ValueError(f"Unknown service type: {service_name}")

        if service_name in self.multi_instance_services or force_new:
            vcprint(
                verbose=True,
                data=f"[ServiceFactory] Creating new instance of {service_name}",
                color="green",
            )
            return self.services[service_name]()

        if service_name not in self.service_instances:
            self.service_instances[service_name] = self.services[service_name]()
            vcprint(
                verbose=True,
                data=f"[ServiceFactory] Created new instance of {service_name}",
                color="green",
            )
        else:
            vcprint(
                verbose=True,
                data=f"[ServiceFactory] Reusing existing instance of {service_name}",
                color="blue",
            )
        return self.service_instances[service_name]

    def register_default_services(self):
        pass

    async def process_request(self, sid, user_id, data, namespace, service_name, org_id=None):
        try:
            # Extract SESSION-level scope context (not task-specific)
            # session_scope_context = self._extract_session_scope_context(data)

            # Create session manager with persistent scopes
            # session_manager = self.get_session_manager(
            #     sid=sid,
            #     user_id=user_id,
            #     org_id=org_id,
            #     client_id=session_scope_context.get('client_id'),
            #     project_id=session_scope_context.get('project_id')
            # )

            # Pass session manager to request handler - IT handles task scopes
            request = SocketRequestBase(
                sid, data, namespace, service_name, user_id,
                session_manager=None
            )

            success, prepared_tasks = await request.initialize()

            if success:
                tasks = []
                temp_instances = []

                for task_info in prepared_tasks:
                    try:
                        force_new = service_name in self.multi_instance_services
                        service_instance = self.create_service(service_name, force_new=force_new)

                        if force_new:
                            temp_instances.append(service_instance)

                        # Pass session manager to service
                        # if hasattr(service_instance, 'set_session_manager'):
                        #     service_instance.set_session_manager(session_manager)

                        # Add session_manager to task context
                        # task_info["context"]["session_manager"] = session_manager

                        # NO SCOPE SWITCHING HERE - that's the task's responsibility
                        service_instance.add_stream_handler(task_info["stream_handler"])
                        service_instance.set_user_id(user_id)

                        if "log_level" in task_info and task_info["log_level"]:
                            service_instance.set_log_level(task_info["log_level"])

                        task = service_instance.process_task(
                            task_info["task"], task_info["context"]
                        )
                        tasks.append(task)

                    except Exception as e:
                        import traceback
                        print(f"Error setting up service task: {str(e)}")
                        traceback.print_exc()

                try:
                    await asyncio.gather(*tasks, return_exceptions=True)
                except Exception as e:
                    import traceback
                    print(f"Error during task execution: {str(e)}")
                    traceback.print_exc()

                # Cleanup temp instances
                for instance in temp_instances:
                    try:
                        if hasattr(instance, "cleanup"):
                            await instance.cleanup()
                    except Exception as e:
                        import traceback
                        print(f"Error during instance cleanup: {str(e)}")
                        traceback.print_exc()
                    finally:
                        del instance

            return self.create_service(service_name)

        except Exception as e:
            import traceback
            print(f"Error in process_request: {str(e)}")
            traceback.print_exc()
            try:
                return self.create_service(service_name)
            except Exception:
                return None
