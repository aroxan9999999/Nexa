# aurenora/admin.py
import os
from django.contrib import admin
from django.contrib import messages
from django.core.files.storage import default_storage
from django.http import HttpResponseRedirect
from django.utils.html import format_html

from .models import CyberXXBot, LandingPage, Country, UserProfile, GeneralSetting
from .forms import AuraMessageForm, AuraEmailForm, AuraPhoneForm


# ===================== UserProfile =====================

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    change_list_template = "admin/aurenora/userprofile/change_list.html"

    list_display = (
        "id", "telegram_user_id", "username", "full_name", "email", "phone",
        "country", "telegram_language", "bot", "registration_date", "activate_start",
    )
    list_filter = ("telegram_language", "country", "bot")
    search_fields = ("telegram_user_id", "username", "full_name", "email", "phone")
    readonly_fields = ("registration_date", "activate_start")

    def changelist_view(self, request, extra_context=None):
        """Добавляет 3 формы на страницу списка."""
        extra_context = extra_context or {}
        extra_context["custom_form"] = AuraMessageForm()
        extra_context["email_form"] = AuraEmailForm()
        extra_context["phone_form"] = AuraPhoneForm()
        return super().changelist_view(request, extra_context=extra_context)

# ===================== Country =====================
@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "name")
    search_fields = ("code", "name")
    list_filter = ("code",)


# ===================== LandingPage =====================
@admin.register(LandingPage)
class LandingPageAdmin(admin.ModelAdmin):
    list_display = (
        "id", "name", "bot", "landing_type", "language",
        "subscriber_count", "created_at", "updated_at", "logo_preview",
    )
    list_filter = ("landing_type", "bot", "language")
    search_fields = ("name",)
    readonly_fields = ("created_at", "updated_at")

    def logo_preview(self, obj):
        if obj.logo:
            return format_html('<img src="{}" style="height: 24px;">', obj.logo.url)
        return "—"

    logo_preview.short_description = "Логотип"


# ===================== CyberXXBot =====================
@admin.register(CyberXXBot)
class CyberXXBotAdmin(admin.ModelAdmin):
    list_display = (
        "id", "name", "username", "api_key", "active", "process_id",
        "created_at", "updated_at", "base_url", "description_url", "open_delay",
    )
    list_filter = ("active", "created_at", "updated_at")
    search_fields = ("name", "username", "api_key", "base_url")
    readonly_fields = ("created_at", "updated_at")


# ===================== GeneralSetting =====================
@admin.register(GeneralSetting)
class GeneralSettingAdmin(admin.ModelAdmin):
    list_display = ("id", "key", "description")
    search_fields = ("key", "description")