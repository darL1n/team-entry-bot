from django.db.models import TextChoices


class TeamApplicationStatus(TextChoices):
    NEW = "new", "Черновик"
    PENDING = "pending", "На рассмотрении"
    APPROVED = "approved", "Одобрена"
    REJECTED = "rejected", "Отклонена"

class AvailabilityChoices(TextChoices):
    ONE_TWO_HOURS = "1-2", "1–2 часа в день"
    THREE_FOUR_HOURS = "3-4", "3–4 часа в день"
    FIVE_PLUS_HOURS = "5+", "Более 5 часов в день"

class TeamApplicationStep(TextChoices):
    SOURCE = 'source', 'Ожидается ответ на вопрос 1'
    AVAILABILITY = 'availability', 'Ожидается выбор времени'
    EXPERIENCE = 'experience', 'Ожидается выбор опыта'
    DONE = 'done', 'Завершено'