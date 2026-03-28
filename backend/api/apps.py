from django.apps import AppConfig


class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api'
    verbose_name = 'LiveStock IQ API'

    def ready(self):
        """Setup MongoDB indexes when Django starts."""
        try:
            from . import mongo_models as mongo
            mongo.setup_mongodb_indexes()
        except Exception:
            pass  # MongoDB may not be running — gracefully skip
