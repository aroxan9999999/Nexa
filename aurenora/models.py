import logging
import subprocess
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.contrib.auth.models import Group, User
import os
import shutil
from django.utils import timezone
from datetime import datetime


User._meta.verbose_name = "👻 Пользователь"
User._meta.verbose_name_plural = "👻 Пользователи"

Group._meta.verbose_name = "⚔️ Группа"
Group._meta.verbose_name_plural = "⚔️ Группы"



class CyberXXBot(models.Model):
    name = models.CharField(max_length=255, verbose_name="Название бота",help_text="Название, введенное в Father Bot, для идентификации бота")
    username = models.CharField(max_length=255, unique=True, verbose_name="Username бота", help_text="Уникальный username, созданный в Father Bot")
    api_key = models.CharField(max_length=255, unique=True, verbose_name="API ключ бота", help_text="Уникальный API-ключ, выданный при создании бота в Father Bot")
    base_url = models.URLField(verbose_name="Базовая ссылка", max_length=5000, help_text="Ссылка трекера на продукт, которая открывается у пользователя при активации бота")
    description_url = models.URLField(verbose_name="Ссылка на PWA", max_length=1000, blank=True, null=True, help_text="Ссылка")
    open_delay = models.IntegerField(verbose_name="Время до открытия сылки", default=10)
    active = models.BooleanField(default=True, verbose_name="Активен")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    process_id = models.IntegerField(null=True, blank=True)


    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "🌍 Телеграм Бот"
        verbose_name_plural = "🌍 Боты"

        # Настройки индексации
        indexes = [
            models.Index(fields=['username'], name='idx_username'),
            models.Index(fields=['api_key'], name='idx_api_key'),
            models.Index(fields=['active'], name='idx_active'),
        ]

        # Порядок сортировки
        ordering = ['-created_at', 'username']


class LandingPage(models.Model):
    LANDING_TYPES = [('basic', 'Базовый'), ('custom', 'Кастомный')]
    bot = models.ForeignKey('CyberXXBot', on_delete=models.CASCADE, related_name='landing_pages', verbose_name="Бот")
    landing_type = models.CharField(max_length=10, choices=LANDING_TYPES, default='basic', verbose_name="Тип лендинга", help_text="Выберите тип лендинга: 'Базовый' или 'Кастомный'.")
    name = models.CharField(max_length=255, verbose_name="Название", help_text="Введите название лендинга.")
    subscriber_count = models.CharField(max_length=50, verbose_name="К-во подписчиков", blank=True, null=True, help_text="Введите количество подписчиков (опционально).")
    description = models.TextField(verbose_name="Описание", blank=True, null=True, help_text="Добавьте описание лендинга (опционально).")
    button_text = models.CharField(max_length=100, verbose_name="Название кнопки", blank=True, null=True, help_text="Введите текст, который будет отображаться на кнопке (опционально).")
    logo = models.ImageField(upload_to='logos/', verbose_name="Логотип бота", help_text="Загрузите логотип для бота (опционально).")
    language = models.ForeignKey('Country', on_delete=models.SET_NULL, verbose_name="Язык", blank=True, null=True, help_text="Выберите язык лендинга (если применимо).")
    custom_html_file = models.FileField(upload_to='custom_landings/', verbose_name="HTML файл", blank=True, null=True, help_text="Загрузите HTML файл для кастомного лендинга (обязательно для кастомного типа).")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания", help_text="Дата и время создания лендинга.")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления", help_text="Дата и время последнего обновления лендинга.")
    google_analytics_id = models.CharField(max_length=20, blank=True, null=True, verbose_name="Google Analytics ID", help_text="Идентификатор Google Analytics для отслеживания.")
    yandex_metrika_id = models.CharField(max_length=20, blank=True, null=True, verbose_name="Яндекс.Метрика ID", help_text="Идентификатор Яндекс.Метрики для отслеживания.")
    google_analytics_full_script = models.TextField(blank=True, null=True,verbose_name="Полный скрипт Google Analytics", help_text="Полный код скрипта для Google Analytics, если требуется настроить кастомно.")
    yandex_metrika_full_script = models.TextField(blank=True, null=True, verbose_name="Полный скрипт Яндекс.Метрики", help_text="Полный код скрипта для Яндекс.Метрики, если требуется настроить кастомно.")

    def clean(self):
        """Проверка на обязательность HTML файла для кастомного лендинга."""
        if self.landing_type == 'custom' and not self.custom_html_file:
            raise ValidationError({'custom_html_file': 'HTML файл обязателен для кастомного лендинга.'})

        if not self.bot.active:
            raise ValidationError(
                f"Бот {self.bot.username} неактивен. Невозможно создать лендинг для неактивного бота.")

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if self.custom_html_file:
            source_path = self.custom_html_file.path
            destination_dir = os.path.join(settings.BASE_DIR, self._meta.app_label, 'templates', 'custom_landings')
            os.makedirs(destination_dir, exist_ok=True)  # Создаём папку, если её нет
            destination_path = os.path.join(destination_dir, os.path.basename(source_path))

            shutil.copy(source_path, destination_path)
            super().save(*args, **kwargs)




    def __str__(self):
        """Возвращает название лендинга и язык, если он указан, иначе 'Неизвестный'."""
        language_name = self.language.name if self.language else 'Неизвестный'
        return f"{self.name} ({language_name})"

    class Meta:
        verbose_name = "🌐 Лендинг"
        verbose_name_plural = "🌐 Лендинги"

        # Индексы для оптимизации запросов
        indexes = [
            models.Index(fields=['bot', 'landing_type'], name='idx_bot_landing_type'),
            models.Index(fields=['name'], name='idx_name'),
        ]

        # Сортировка по умолчанию
        ordering = ['-created_at', 'name']


class Country(models.Model):
    code = models.CharField(max_length=20, unique=True, verbose_name="Код страны", help_text="Уникальный код страны (например, 'US' для США или 'RU' для России).")
    name = models.CharField(max_length=100, verbose_name="Название страны", help_text="Полное название страны (например, 'США' или 'Россия').")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "🗺️ Страна"
        verbose_name_plural = "🗺️ Страны"

        indexes = [
            models.Index(fields=['code'], name='country_code_idx'),
            models.Index(fields=['name'], name='country_name_idx'),
        ]

        ordering = ['name']

class UserProfile(models.Model):
    telegram_user_id = models.CharField(max_length=50, blank=True, null=True, verbose_name="Telegram user id", help_text="Уникальный идентификатор пользователя в Telegram.")
    node_id = models.CharField(max_length=100, null=True, blank=True)
    username = models.CharField(max_length=100, blank=True, null=True, verbose_name="Username", help_text="Имя пользователя в Telegram.")
    full_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="ФИО", help_text="Полное имя пользователя.")
    telegram_language = models.CharField(max_length=100, blank=True, null=True, verbose_name="Язык", help_text="Код языка, используемого пользователем в Telegram (например, 'ru', 'en').")
    email = models.EmailField(max_length=254, blank=True, null=True, verbose_name="Email",help_text="Email пользователя.")
    phone = models.CharField(max_length=16, blank=True, null=True, verbose_name="Телефон", help_text="Телефон пользователя в формате +79991234567.")
    is_active_in_telegram = models.BooleanField(default=False, verbose_name="Пользователь активный в телеграм?", help_text="Отметьте, если пользователь активен в Telegram.")
    bot = models.ForeignKey('CyberXXBot', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Бот", help_text="бот, с которым связан пользователь.")
    cyber_link = models.URLField(max_length=5000, blank=True, null=True, verbose_name="Ссылка для кнопки", help_text="Ссылка, которая будет открываться при нажатии на кнопку.")
    ip_address = models.GenericIPAddressField(blank=True, null=True, verbose_name="IP", help_text="IP-адрес пользователя.")
    user_agent = models.TextField(blank=True, null=True, verbose_name="User Agent", help_text="Информация о браузере и устройстве пользователя.")
    country = models.ForeignKey(Country, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Страна", help_text="Страна пользователя.")
    city = models.CharField(max_length=100, blank=True, null=True, verbose_name="Город", help_text="Город пользователя.")
    timezone = models.CharField(max_length=50, blank=True, null=True, verbose_name="Таймзона", help_text="Таймзона пользователя (например, 'UTC+3').")
    registration_date = models.DateTimeField(auto_now_add=True, verbose_name="Дата регистрации", help_text="Дата и время регистрации пользователя в системе.")
    activate_start = models.DateTimeField(null=True, blank=True, verbose_name="Дата начала взаимодействия", help_text="Дата и время, когда пользователь начал взаимодействие с ботом.")



    def __str__(self):
        return f"TG: {self.telegram_user_id} - {self.username if self.username else 'Неизвестный'}"

    class Meta:
        verbose_name = "️☠️ Пользователь"
        verbose_name_plural = "☠️ Пользователи"

        indexes = [
            models.Index(fields=['telegram_user_id'], name='idx_telgrm_uid'),
            models.Index(fields=['node_id'], name='idx_nodeid'),
            models.Index(fields=['is_active_in_telegram'], name='idx_is_active'),
            models.Index(fields=['bot'], name='idx_bot'),
            models.Index(fields=['country'], name='idx_country'),
            models.Index(fields=['registration_date'], name='idx_reg_date'),
        ]

        ordering = ['-registration_date', 'username']



class GeneralSetting(models.Model):
    key = models.CharField(max_length=255, unique=True, verbose_name="Переменная", help_text="Уникальный ключ настройки.")
    value = models.TextField(verbose_name="Значение", help_text="Значение настройки.")
    description = models.CharField(max_length=255, verbose_name="Для чего", help_text="Описание настройки, для чего она предназначена.", blank=True, null=True)

    class Meta:
        verbose_name = "⚙️ Настройки"
        verbose_name_plural = "⚙️ Настройки"

        indexes = [
            models.Index(fields=['key'], name='idx_key')
        ]

        ordering = ['key']

    def __str__(self):
        return self.key
