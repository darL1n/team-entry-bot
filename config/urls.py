from django.contrib import admin
from django.urls import path
from apps.bot.views import telegram_webhook

urlpatterns = [
    path('admin/', admin.site.urls),
    path("bot/webhook/", telegram_webhook),  # или любой путь по твоему выбору
]
