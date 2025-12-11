# apps/bot/handlers/messages.py
from telebot.types import Message
from ..telebot_instance import bot
from ..services import get_or_create_draft, ExistingFinalApplication, save_source_answer
from ..keyboards.inline import get_start_inline, get_availability_keyboard, get_resume_or_reset_keyboard
from ..enums import TeamApplicationStatus, TeamApplicationStep
from ..messages.texts import *

@bot.message_handler(commands=['start'])
def start_command(msg: Message):
    try:
        bot.delete_message(msg.chat.id, msg.message_id)
    except Exception:
        pass
    try:
        app = get_or_create_draft(msg.from_user)
    except ExistingFinalApplication as e:
        if e.status == TeamApplicationStatus.APPROVED:
            return bot.send_message(msg.chat.id, ALREADY_APPROVED_TEXT)

    if app.status == TeamApplicationStatus.PENDING:
        return bot.send_message(msg.chat.id, ALREADY_SENT_TEXT)

    if app.status == TeamApplicationStatus.REJECTED:
        bot.send_message(msg.chat.id, REJECTED_CAN_RETRY_TEXT)

    if app.step == TeamApplicationStep.SOURCE:
        return bot.send_message(msg.chat.id, WELCOME_TEXT, parse_mode="HTML", reply_markup=get_start_inline())
    else:
        return bot.send_message(msg.chat.id, RESUME_OR_RESET_TEXT, reply_markup=get_resume_or_reset_keyboard())

@bot.message_handler(func=lambda m: True)
def handle_step_message(msg: Message):
    app = get_or_create_draft(msg.from_user)

    if app.step == TeamApplicationStep.SOURCE:
        if len(msg.text.strip()) < 3:
            return bot.send_message(msg.chat.id, "⚠️ Пожалуйста, ответ должен содержать хотя бы 3 символа.")

        save_source_answer(app, msg.text.strip())
        bot.send_message(
            msg.chat.id,
            QUESTION_2_TEXT,
            parse_mode='HTML',
            reply_markup=get_availability_keyboard()
        )
