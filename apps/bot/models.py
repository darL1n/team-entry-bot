from django.db import models
from django.utils import timezone
from .enums import *



class TeamApplication(models.Model):
    # Telegram user
    user_id = models.BigIntegerField()
    username = models.CharField(max_length=255, blank=True, null=True)
    full_name = models.CharField(max_length=255, blank=True, null=True)  # если хочешь собирать отдельно

    # Вопросы
    source = models.TextField(verbose_name="Откуда узнали о нас", null=True, blank=True)
    availability = models.CharField(
        max_length=10,
        choices=AvailabilityChoices.choices,
        verbose_name="Сколько готовы уделять времени",
        null=True, 
        blank=True
    )
    has_experience = models.BooleanField(verbose_name="Есть ли опыт в проектах", null=True, blank=True)
    additional_info = models.TextField(blank=True, null=True, verbose_name="Доп. информация")

    # Служебное
    status = models.CharField(
        max_length=20,
        choices=TeamApplicationStatus.choices,
        default=TeamApplicationStatus.NEW
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(blank=True, null=True)

    step = models.CharField(
        max_length=20,
        choices=TeamApplicationStep.choices,
        default=TeamApplicationStep.SOURCE
    )

    updated_at = models.DateTimeField(auto_now=True)



    class Meta:
        ordering = ['-submitted_at']

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
