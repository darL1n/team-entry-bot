from django.core.management.base import BaseCommand, CommandError
from apps.bot.telebot_instance import bot
from config.settings import TELEGRAM
from time import sleep


class Command(BaseCommand):
    def handle(self, *args, **options):
        bot.remove_webhook()
        sleep(5)
        bot.set_webhook(url=TELEGRAM["WEBHOOK_URL"])