import logging
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from telebot.types import Update
from .telebot_instance import bot

logger = logging.getLogger(__name__)

@csrf_exempt
def telegram_webhook(request):
    print(request)
    if request.method == "POST":
        try:
            json_str = request.body.decode("utf-8")
            logger.info("✅ RAW update: %s", json_str)

            update = Update.de_json(json_str)
            logger.info("✅ Parsed update: %s", update)

            bot.process_new_updates([update])

            logger.info("✅ Update passed to bot.process_new_updates")
        except Exception as e:
            logger.exception("❌ Error while processing update")
            return HttpResponse(status=500)
        return HttpResponse(status=200)
    return HttpResponse("Method not allowed", status=405)
