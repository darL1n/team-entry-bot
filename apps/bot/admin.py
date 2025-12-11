from django.contrib import admin
from .models import TeamApplication


@admin.register(TeamApplication)
class TeamApplicationAdmin(admin.ModelAdmin):
    list_display = (
        "user_id",
        "username",
        "status",
        "step",
        "availability",
        "has_experience",
        "submitted_at",
        "reviewed_at",
    )
    list_filter = (
        "status",
        "step",
        "availability",
        "has_experience",
        "submitted_at",
    )
    search_fields = (
        "username",
        "user_id",
        "source",
        "additional_info",
    )
    readonly_fields = ("submitted_at", "reviewed_at", "updated_at")
    ordering = ("-submitted_at",)

    fieldsets = (
        ("Пользователь", {
            "fields": ("user_id", "username", "full_name")
        }),
        ("Ответы", {
            "fields": ("source", "availability", "has_experience", "additional_info")
        }),
        ("Служебное", {
            "fields": ("status", "step", "submitted_at", "reviewed_at", "updated_at")
        }),
    )
