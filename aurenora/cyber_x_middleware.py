from datetime import datetime
from django.http import HttpResponse
from django.shortcuts import render
from django.core.cache import cache
from django.conf import settings
from .models import CyberXXBot, Country
from .ip_xx import get_country_from_ip, get_client_ip
from .lxx import lxx
from mortal_shade.zombie_error import zombie
import random
import string
import os
# aurenora/middleware.py
from django.http import HttpResponse
from django.conf import settings

from .models import CyberXXBot
from .lxx import lxx
from mortal_shade.zombie_error import zombie


LANDING_PREFIX = "landing"   # 👈 меняешь тут на что угодно


class CyberDomainMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def _log_message(self, msg: str) -> str:
        return f"[middleware] {msg}"

    def __call__(self, request):
        current_domain = request.get_host().split(":")[0]
        lxx.info(self._log_message(f"Запрос с домена: {current_domain}"))
        lxx.info(f"Полный URL запроса: {request.build_absolute_uri()}")



        parts = [p for p in request.path.strip("/").split("/") if p]

        if len(parts) >= 2 and parts[0] == LANDING_PREFIX:
            username = parts[1]
            bot = CyberXXBot.objects.filter(username=username, active=True).first()
            if not bot:
                lxx.error(self._log_message(f"Бот не найден по username: {username}"))
                zombie.error(f"[zombie] Бот не найден по username: {username}")
                return HttpResponse(status=404)

            # Пробрасываем найденного бота
            request.bot = bot
            request.bot_id = bot.pk

            lxx.info(self._log_message(f"Лендинг: найден бот {username} (id={bot.pk})"))
            return self.get_response(request)

        # ===== все остальные урлы пропускаем =====
        return self.get_response(request)
