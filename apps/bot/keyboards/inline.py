# apps/bot/keyboards/inline.py
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from ..enums import AvailabilityChoices

def get_start_inline() -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("📝 Пройти анкету", callback_data="start_form"))
    return markup

def get_resume_or_reset_keyboard() -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("✅ Продолжить", callback_data="resume_form"),
        InlineKeyboardButton("🔁 Начать заново", callback_data="reset_form")
    )
    return markup

def get_availability_keyboard() -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup()
    for value, label in AvailabilityChoices.choices:
        markup.add(InlineKeyboardButton(label, callback_data=f"avail:{value}"))
    return markup

def get_experience_keyboard() -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("Да", callback_data="exp:yes"),
        InlineKeyboardButton("Нет", callback_data="exp:no")
    )
    return markup