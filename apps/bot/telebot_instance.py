from telebot import TeleBot
from config.settings import TELEGRAM

bot = TeleBot(TELEGRAM["BOT_TOKEN"])


