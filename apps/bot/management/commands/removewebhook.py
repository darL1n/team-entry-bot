from django.core.management.base import BaseCommand, CommandError
from apps.bot.telebot_instance import bot


class Command(BaseCommand):
    def handle(self, *args, **options):
        bot.remove_webhook()