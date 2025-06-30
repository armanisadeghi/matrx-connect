app_service_factory = None

class AlreadyConfiguredFactoryError(Exception):
    pass

class FactoryNotConfiguredError(Exception):
    pass

def configure_factory(class_object):
    global app_service_factory
    if app_service_factory is not None:
        raise AlreadyConfiguredFactoryError("Factory is already configured.")

    app_service_factory = class_object

def get_app_factory():
    global app_service_factory
    if not app_service_factory:
        raise FactoryNotConfiguredError("Please configure App service factory")
    return app_service_factory()