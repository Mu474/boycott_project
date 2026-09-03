from django.apps import AppConfig


class SuggestionsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'suggestions'

    def ready(self):
        import suggestions.signals  # noqa: F401
