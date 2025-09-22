from django.apps import AppConfig


class AurenoraConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'aurenora'
    verbose_name = "Меню"

    def ready(self):
        from . import signals

