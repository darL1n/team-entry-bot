# apps/bot/services/application.py
from apps.bot.models import TeamApplication
from apps.bot.enums import TeamApplicationStep, TeamApplicationStatus
from django.utils import timezone
from telebot.types import User


class ExistingFinalApplication(Exception):
    def __init__(self, status: str):
        self.status = status


def get_or_create_draft(user: User) -> TeamApplication:
    app = TeamApplication.objects.filter(user_id=user.id).order_by('-submitted_at').first()

    if app:
        if app.step != TeamApplicationStep.DONE:
            return app
        if app.status == TeamApplicationStatus.REJECTED:
            pass  # создадим новую
        elif app.status == TeamApplicationStatus.APPROVED:
            raise ExistingFinalApplication(status=TeamApplicationStatus.APPROVED)
        elif app.status == TeamApplicationStatus.PENDING or app.status == TeamApplicationStatus.NEW:
            return app

    return TeamApplication.objects.create(
        user_id=user.id,
        username=user.username,
        step=TeamApplicationStep.SOURCE,
        status=TeamApplicationStatus.NEW,
        submitted_at=timezone.now(),
    )

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
    app.save(update_fields=["has_experience", "status", "step", "submitted_at", "updated_at"])
    return app
