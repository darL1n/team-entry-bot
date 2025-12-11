# TEAM-ENTRY-BOT

Telegram-бот на Django для сбора заявок в команду.

Бот реализует многошаговую анкету в Telegram, сохраняет ответы в базу данных и отправляет итоговую заявку в ревью-группу. Модераторы могут одобрять или отклонять заявки прямо в Telegram, а пользователь получает уведомление о результате.

---

## Возможности

* Многошаговая форма с черновиком заявки.
* Продолжение анкеты с того шага, на котором пользователь остановился.
* Возможность сбросить текущую заявку и пройти заново.
* Отправка финальной заявки в отдельную Telegram-группу для модераторов.
* Инлайн-кнопки в группе: «Одобрить» и «Отклонить».
* Уведомление пользователю о результате рассмотрения.
* Работа через Django webhook (без polling в продакшене).

---

## Технологии

* Python 3.10+
* Django
* pyTelegramBotAPI (telebot)
* SQLite или PostgreSQL
* Django management-команды (запуск бота, установка/удаление вебхука)
* Gunicorn + Nginx + systemd (для продакшн-деплоя)

---

## Структура проекта

```text
TEAM-ENTRY-BOT/
│
├── apps/
│   └── bot/
│       ├── handlers/
│       │   ├── callbacks.py         # callback_query_handler-ы и inline-кнопки
│       │   └── messages.py          # message_handler-ы (команды, текстовые шаги)
│       │
│       ├── keyboards/               # инлайн/реплай-клавиатуры
│       ├── management/
│       │   └── commands/
│       │       ├── runbot.py        # локальный запуск бота (polling)
│       │       ├── setwebhook.py    # установка вебхука в Telegram
│       │       └── removewebhook.py # удаление вебхука
│       ├── messages/                # тексты сообщений и шаблоны
│       ├── enums.py                 # перечисления: статусы, шаги, варианты
│       ├── models.py                # модель TeamApplication
│       ├── services/
│       │   └── application.py       # бизнес-логика работы с заявками
│       ├── telebot_instance.py      # инициализация bot = TeleBot(...)
│       └── views.py                 # Django view для webhook-а
│
├── config/
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
│
├── manage.py
├── requirements.txt
└── .env
```

---

## Модель TeamApplication

Файл: `apps/bot/models.py`

```python
class TeamApplication(models.Model):
    # Telegram user
    user_id = models.BigIntegerField()
    username = models.CharField(max_length=255, blank=True, null=True)
    full_name = models.CharField(max_length=255, blank=True, null=True)

    # Ответы анкеты
    source = models.TextField(null=True, blank=True)
    availability = models.CharField(
        max_length=10,
        choices=AvailabilityChoices.choices,
        null=True,
        blank=True,
    )
    has_experience = models.BooleanField(null=True, blank=True)
    additional_info = models.TextField(null=True, blank=True)

    # Служебные поля
    status = models.CharField(
        max_length=20,
        choices=TeamApplicationStatus.choices,
        default=TeamApplicationStatus.NEW,
    )

    step = models.CharField(
        max_length=20,
        choices=TeamApplicationStep.choices,
        default=TeamApplicationStep.SOURCE,
    )

    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"Заявка @{self.username or self.user_id} [{self.get_status_display()}]"

    def approve(self, reviewer=None):
        self.status = TeamApplicationStatus.APPROVED
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.save()

    def reject(self, reviewer=None):
        self.status = TeamApplicationStatus.REJECTED
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.save()
```

Ключевые моменты:

* `step` отражает, на каком шаге находится пользователь.
* `status` показывает состояние заявки: NEW, PENDING, APPROVED, REJECTED.
* `submitted_at` задаётся при создании и обновляется при финализации анкеты.

---

## Бизнес-логика заявок (services/application.py)

Файл: `apps/bot/services/application.py`

### Получение/создание черновика

```python
def get_or_create_draft(user: User) -> TeamApplication:
    app = TeamApplication.objects.filter(user_id=user.id).order_by("-submitted_at").first()

    if app:
        if app.step != TeamApplicationStep.DONE:
            return app
        if app.status == TeamApplicationStatus.REJECTED:
            # старая отклонена – создаём новую
            pass
        elif app.status == TeamApplicationStatus.APPROVED:
            # уже одобренная финальная заявка – не даём создать ещё одну
            raise ExistingFinalApplication(status=TeamApplicationStatus.APPROVED)
        elif app.status in (TeamApplicationStatus.PENDING, TeamApplicationStatus.NEW):
            # заявка на рассмотрении или только создана – продолжаем её
            return app

    return TeamApplication.objects.create(
        user_id=user.id,
        username=user.username,
        step=TeamApplicationStep.SOURCE,
        status=TeamApplicationStatus.NEW,
        submitted_at=timezone.now(),
    )
```

Поведение:

* Если есть незавершённая заявка → продолжаем её.
* Если заявка отклонена → разрешаем создать новую.
* Если заявка одобрена → выбрасывается `ExistingFinalApplication`, чтобы не было дублей.
* Если заявка на рассмотрении → продолжаем существующую.

### Сохранение ответов по шагам

```python
def save_source_answer(app: TeamApplication, text: str):
    app.source = text
    app.step = TeamApplicationStep.AVAILABILITY
    app.save(update_fields=["source", "step", "updated_at"])


def save_availability_answer(app: TeamApplication, value: str):
    app.availability = value
    app.step = TeamApplicationStep.EXPERIENCE
    app.save(update_fields=["availability", "step", "updated_at"])


def save_experience_and_finalize(app: TeamApplication, has_experience: bool):
    app.has_experience = has_experience
    app.status = TeamApplicationStatus.PENDING
    app.step = TeamApplicationStep.DONE
    app.submitted_at = timezone.now()
    app.save(update_fields=[
        "has_experience",
        "status",
        "step",
        "submitted_at",
        "updated_at",
    ])
    return app
```

Каждая функция:

* Обновляет конкретное поле.
* Переводит заявку на следующий шаг.
* Обновляет `updated_at`.
* Финальная функция также переводит статус в `PENDING` и фиксирует время `submitted_at`.

---

## Обработчики сообщений (handlers/messages.py)

Файл: `apps/bot/handlers/messages.py`

Основные обработчики:

* `/start`

  * Пытается удалить исходное сообщение пользователя.
  * Получает/создаёт черновик через `get_or_create_draft`.
  * Если уже одобрена финальная заявка → отправляет текст `ALREADY_APPROVED_TEXT`.
  * Если заявка в статусе `PENDING` → отвечает `ALREADY_SENT_TEXT`.
  * Если заявка отклонена → показывает `REJECTED_CAN_RETRY_TEXT`.
  * Если `step == SOURCE` → отправляет приветствие `WELCOME_TEXT` с кнопкой начать.
  * Иначе → предлагает продолжить или сбросить заявку.

* Обработчик всех остальных текстовых сообщений:

  * Если заявка на шаге `SOURCE`:

    * Проверяет минимальную длину ответа.
    * Сохраняет ответ через `save_source_answer`.
    * Отправляет второй вопрос с inline-клавиатурой `get_availability_keyboard()`.

---

## Обработчики callback-ов (handlers/callbacks.py)

Файл: `apps/bot/handlers/callbacks.py`

Основные сценарии:

* `start_form`

  * Отправляет первый вопрос `QUESTION_1_TEXT` и ждёт текстовый ответ.

* `resume_form`

  * Загружает черновик через `get_or_create_draft`.
  * В зависимости от `step` отправляет следующий вопрос или приветствие.

* `reset_form`

  * Очищает поля заявки и возвращает её на шаг `SOURCE` со статусом `NEW`.

* `avail:<value>`

  * Проверяет допустимость значения по `AvailabilityChoices`.
  * Сохраняет ответ `save_availability_answer`.
  * Показывает третий вопрос `QUESTION_3_TEXT` с клавиатурой `get_experience_keyboard()`.

* `exp:<yes|no>`

  * Преобразует ответ в `has_experience: bool`.
  * Вызывает `save_experience_and_finalize`.
  * Отправляет текст `SUBMITTED_TEXT` пользователю.
  * Формирует карточку заявки `GROUP_REVIEW_TEMPLATE` и отправляет её в ревью-группу `REVIEW_GROUP_ID` с кнопками:

    * «Одобрить ✅» (`review:<id>:approve`)
    * «Отклонить ❌» (`review:<id>:reject`)

* `review:<id>:approve|reject`

  * Проверяет, что заявка существует и всё ещё в статусе `PENDING`.
  * В зависимости от действия ставит статус `APPROVED` или `REJECTED`.
  * Редактирует сообщение в группе с обновлённой строкой `result`.
  * Отправляет пользователю текст `REVIEW_APPROVED_TEXT` / `REVIEW_REJECTED_TEXT` и ссылку `REVIEW_APPROVED_LINK` при одобрении.

---

## Webhook (Django view)

Файл: `apps/bot/views.py`

```python
@csrf_exempt
def telegram_webhook(request):
    if request.method == "POST":
        try:
            json_str = request.body.decode("utf-8")
            logger.info("RAW update: %s", json_str)

            update = Update.de_json(json_str)
            logger.info("Parsed update: %s", update)

            bot.process_new_updates([update])
            logger.info("Update passed to bot.process_new_updates")
        except Exception:
            logger.exception("Error while processing update")
            return HttpResponse(status=500)
        return HttpResponse(status=200)

    return HttpResponse("Method not allowed", status=405)
```

Задача вьюхи:

1. Принять POST-запрос от Telegram.
2. Распарсить тело в объект `Update`.
3. Отдать его в telebot через `bot.process_new_updates`.

Маршрут настраивается в `config/urls.py`, например:

```python
from apps.bot.views import telegram_webhook

urlpatterns = [
    ...,
    path("bot/webhook/", telegram_webhook, name="telegram_webhook"),
]
```

---

## Management-команды

Файлы: `apps/bot/management/commands/`

Примеры (идея, а не полный код):

```bash
python manage.py runbot        # локальный polling-запуск бота
python manage.py setwebhook    # установка webhook-URL в Telegram
python manage.py removewebhook # удаление webhook-а
```

Команды используют `TELEGRAM_BOT_TOKEN` и `WEBHOOK_URL` из настроек/окружения.

---

## Переменные окружения (.env)

Пример минимального `.env`:

```env
DEBUG=False
SECRET_KEY=your_django_secret_key
ALLOWED_HOSTS=your-domain.com

TELEGRAM_BOT_TOKEN=123456:ABC...
TELEGRAM_REVIEW_GROUP_ID=-1001234567890
TELEGRAM_WEBHOOK_URL=https://your-domain.com/bot/webhook/
```

Далее эти значения подтягиваются в `config/settings.py` и используются в `telebot_instance.py` и management-командах.

---

## Локальный запуск

1. Установка зависимостей:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. Миграции:

```bash
python manage.py migrate
```

3. Запуск Django dev-сервера:

```bash
python manage.py runserver
```

4. Запуск бота локально (polling, без вебхука):

```bash
python manage.py runbot
```

---

## Продакшн-сценарий (кратко)

1. Настроить сервер с Django (Gunicorn + Nginx).

2. Открыть HTTPS-домен, например `https://your-domain.com`.

3. Прописать маршрут `/bot/webhook/` на Django view `telegram_webhook`.

4. В .env указать `TELEGRAM_WEBHOOK_URL` вида:

   `https://your-domain.com/bot/webhook/`

5. Выполнить:

```bash
python manage.py setwebhook
```

6. Проверить логи Django/Gunicorn при первых апдейтах.

---

## Жизненный цикл заявки (коротко)

1. Пользователь отправляет `/start`.
2. Создаётся или загружается черновик `TeamApplication`.
3. Пользователь отвечает на вопросы:

   * Откуда узнал.
   * Сколько времени готов уделять.
   * Есть ли опыт.
4. После последнего ответа заявка получает статус `PENDING` и улетает в ревью-группу.
5. Модератор нажимает «Одобрить» или «Отклонить».
6. Статус заявки обновляется, сообщение в группе редактируется.
7. Пользователь получает уведомление о результате.


```
```
