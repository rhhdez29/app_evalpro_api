from django.contrib import admin
from django.utils.html import format_html
from app_evalpro_api.models import Profiles


@admin.register(Profiles)

class ProfilesAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "creation", "update")
    search_fields = ("user__username", "user__email", "user__first_name", "user__last_name")

