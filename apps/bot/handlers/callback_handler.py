# apps/bot/handlers/callbacks.py
from ..telebot_instance import bot
from telebot.types import CallbackQuery
from ..services import get_or_create_draft, save_availability_answer, save_experience_and_finalize
from ..keyboards.inline import get_experience_keyboard, get_availability_keyboard, get_start_inline
from ..enums import TeamApplicationStep, TeamApplicationStatus
from ..messages.texts import *
from ..enums import AvailabilityChoices
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from config.settings import TELEGRAM
from apps.bot.models import TeamApplication
print('apps/bot/handlers/callbacks.py')

REVIEW_GROUP_ID = TELEGRAM["REVIEW_GROUP_ID"]

@bot.callback_query_handler(func=lambda call: call.data == "start_form")
def handle_start_form(call: CallbackQuery):
    bot.send_message(call.message.chat.id, QUESTION_1_TEXT, parse_mode='HTML')
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "resume_form")
def handle_resume(call: CallbackQuery):
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass  # вдруг уже удалено
    app = get_or_create_draft(call.from_user)
    if app.step == TeamApplicationStep.AVAILABILITY:
        bot.send_message(call.message.chat.id, QUESTION_2_TEXT, reply_markup=get_availability_keyboard(), parse_mode='HTML')
    elif app.step == TeamApplicationStep.EXPERIENCE:
        bot.send_message(call.message.chat.id, QUESTION_3_TEXT, reply_markup=get_experience_keyboard(), parse_mode='HTML')
    else:
        bot.send_message(call.message.chat.id, WELCOME_TEXT, parse_mode="HTML", reply_markup=get_start_inline())
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "reset_form")
def handle_reset(call: CallbackQuery):
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass  # вдруг уже удалено

    app = get_or_create_draft(call.from_user)
    app.source = ""
    app.availability = None
    app.has_experience = None
    app.step = TeamApplicationStep.SOURCE
    app.status = TeamApplicationStatus.NEW
    app.save(update_fields=["source", "availability", "has_experience", "step", "status"])

    bot.send_message(call.message.chat.id, WELCOME_TEXT, parse_mode="HTML", reply_markup=get_start_inline())
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("avail:"))
def handle_availability(call: CallbackQuery):
    value = call.data.split(":", 1)[1]
    if value not in dict(AvailabilityChoices.choices):
        return bot.answer_callback_query(call.id, "Некорректный выбор", show_alert=True)

    app = get_or_create_draft(call.from_user)
    if app.step != TeamApplicationStep.AVAILABILITY:
        return

    save_availability_answer(app, value)
    bot.edit_message_text(
        QUESTION_3_TEXT,
        parse_mode='HTML',
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=get_experience_keyboard()
    )
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("exp:"))
def handle_experience(call: CallbackQuery):
    value = call.data.split(":", 1)[1]
    has_experience = value == "yes"

    app = get_or_create_draft(call.from_user)
    if app.step != TeamApplicationStep.EXPERIENCE:
        return

    app = save_experience_and_finalize(app, has_experience)

    bot.edit_message_text(
        SUBMITTED_TEXT,
        chat_id=call.message.chat.id,
        message_id=call.message.message_id
    )

    full_text = GROUP_REVIEW_TEMPLATE.format(
        username=app.username or app.user_id,
        source=app.source,
        availability=app.get_availability_display(),
        experience="Да" if app.has_experience else "Нет",
        timestamp=app.submitted_at.strftime("%Y-%m-%d %H:%M"),
        result="⏳ На рассмотрении"
    )

    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("Одобрить ✅", callback_data=f"review:{app.id}:approve"),
        InlineKeyboardButton("Отклонить ❌", callback_data=f"review:{app.id}:reject")
    )
    bot.send_message(REVIEW_GROUP_ID, full_text, reply_markup=markup, parse_mode="HTML")
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("review:"))
def handle_review_action(call: CallbackQuery):
    _, app_id, action = call.data.split(":")
    try:
        app = TeamApplication.objects.get(id=app_id)
    except TeamApplication.DoesNotExist:
        return bot.answer_callback_query(call.id, "Заявка не найдена", show_alert=True)

    if app.status != TeamApplicationStatus.PENDING:
        return bot.answer_callback_query(call.id, REVIEW_ALREADY_DONE, show_alert=True)

    if action == "approve":
        app.status = TeamApplicationStatus.APPROVED
        result_line = "Одобрено ✅"
        bot.send_message(app.user_id, REVIEW_APPROVED_TEXT)
        bot.send_message(app.user_id, REVIEW_APPROVED_LINK, parse_mode='HTML')
    else:
        app.status = TeamApplicationStatus.REJECTED
        result_line = "Отклонено ❌"
        bot.send_message(app.user_id, REVIEW_REJECTED_TEXT)

    app.save(update_fields=["status"])

    # Собираем сообщение заново
    updated_text = GROUP_REVIEW_TEMPLATE.format(
        username=app.username or app.user_id,
        source=app.source,
        availability=app.get_availability_display(),
        experience="Да" if app.has_experience else "Нет",
        timestamp=app.submitted_at.strftime("%Y-%m-%d %H:%M"),
        result=result_line
    )

    bot.edit_message_text(
        updated_text,
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        parse_mode="HTML"
    )
    bot.answer_callback_query(call.id, "Обновлено")

