from django.apps import AppConfig


class PropertiesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'properties'

    def ready(self):
        from . import location_models  # noqa: F401
        from . import location_signals  # noqa: F401
