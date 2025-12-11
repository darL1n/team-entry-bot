from django.apps import AppConfig


class BotConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.bot'

    def ready(self):
        print("BotConfig.ready()!")
        from .handlers import callback_handler, message_handler
