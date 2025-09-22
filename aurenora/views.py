# aurenora/views.py
import os
from django.views import View
from django.shortcuts import render
from django.http import JsonResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from asgiref.sync import sync_to_async
from django.utils import timezone

from .ip_xx import get_country_from_ip, get_client_ip
from .lxx import lxx
from mortal_shade.zombie_error import zombie
# aurenora/views.py
import os
import asyncio
import aiohttp
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from asgiref.sync import async_to_sync
from django.http import JsonResponse
from django.core.files.storage import default_storage
from django.core.mail import EmailMessage, get_connection
from django.contrib import messages

from .models import UserProfile, CyberXXBot, Country
from .serializers import TelegramMessageSerializer, EmailMessageSerializer, SMSMessageSerializer
from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

class LandingPageView(View):
    """
    GET /landing/<username>/
    Рендерит лендинг бота по username.
    ВАЖНО: здесь гео нужно ТОЛЬКО для выбора корректного лендинга. НИКАКИХ сохранений в профиль!
    """

    def get(self, request, username):
        # 1) Находим бота
        try:
            xx_bot = CyberXXBot.objects.get(username=username)
        except (TypeError, ValueError, CyberXXBot.DoesNotExist):
            lxx.warning("[lxx landing] Некорректный или отсутствующий username бота в запросе")
            raise Http404()

        # 2) Гео по IP — только для выбора лендинга
        ip = get_client_ip(request)
        country_obj, country_name, city, tz_str = self.get_country_for_landing(ip)
        lxx.info(f"[lxx landing] ip={ip}, country={country_name}, city={city}, tz={tz_str}")

        # 3) Выбираем лендинг
        landing_page = self.get_landing_page(xx_bot, country_obj)
        if not landing_page:
            lxx.warning(f"[lxx landing] Лендинг не найден (bot={username}, country={country_name})")
            raise Http404()

        # 4) Ссылки (tg + pwa)
        link = self.make_links(xx_bot)

        # 5) Рендер
        if landing_page.landing_type == "basic":
            return self.render_basic_landing(request, landing_page, country_obj, xx_bot, link)
        elif landing_page.landing_type == "custom":
            return self.render_custom_landing(request, landing_page, xx_bot, link)

        raise Http404()

    # ---------- helpers ----------

    def get_country_for_landing(self, ip):
        country_name, country_code, city, tz_str = get_country_from_ip(ip)
        # создаём/находим по КОДУ (у вас code unique)
        country_obj, _ = Country.objects.get_or_create(code=country_code or "неизвестный",
                                                       defaults={"name": country_name or "Неизвестная"})
        lxx.info(f"[lxx country] Определена страна по IP {ip}: {country_obj} city: {city}, timezone: {tz_str}")

        return country_obj, country_name, city, tz_str

    def get_landing_page(self, bot: CyberXXBot, country_obj: Country):
        # 1) по стране
        lp = bot.landing_pages.filter(language=country_obj).first()
        if lp:
            lxx.info(f"[landing page] основной: {lp.name} ({country_obj.code})")
            return lp

        # 2) fallback по коду языка: XX/NA/unknown/«неизвестный»
        lp = bot.landing_pages.filter(
            language__code__iregex=r'^(xx|na|unknown|н[\s/_-]*е[\s/_-]*из[\s/_-]*в[\s/_-]*е[\s/_-]*с[\s/_-]*т[\s/_-]*н[\s/_-]*ый)$'
        ).first()
        if lp:
            lxx.info(f"[landing page] fallback: {lp.name} (code={lp.language.code if lp.language else '∅'})")
            return lp

        # 3) иначе первый доступный
        lp = bot.landing_pages.first()
        if lp:
            lxx.info(f"[landing page] default-first: {lp.name}")
            return lp

        return None

    def make_links(self, bot: CyberXXBot):
        """
        Возвращает (telegram_link, web_url, pwa_open_delay)
        """
        telegram_link = f"tg://resolve?domain={bot.username}&start=start"
        web_url = bot.description_url if bot.description_url else "0"
        pwa_open_delay = bot.open_delay or 0
        lxx.info(f"[make_links] TG={telegram_link}, PWA={web_url}, delay={pwa_open_delay}")
        return telegram_link, web_url, pwa_open_delay

    def render_basic_landing(self, request, landing_page, country_obj, xx_bot, link):
        telegram_link, web_url, pwa_open_delay = link

        redirect_script = f"""
        <script type="text/javascript">
            const telegramLink = "{telegram_link}";
            const webLink = "{web_url}";
            const delay = {pwa_open_delay} * 1000;

            function clickOpenButton() {{
                const btn = document.querySelector('.open-button');
                if (btn) btn.click();
            }}

            let t;
            function handleLongPress() {{ t = setTimeout(() => {{ clickOpenButton(); }}, 800); }}
            function clearLongPressTimer() {{ clearTimeout(t); clickOpenButton(); }}
            function preventDefaultTouchAndClick(e) {{ e.preventDefault(); }}

            document.addEventListener("click", clickOpenButton, {{ once: true }});
            document.addEventListener("touchcancel", clearLongPressTimer, {{ once: true }});
            document.addEventListener("mousedown", handleLongPress);
            document.addEventListener("mouseup", clearLongPressTimer, {{ once: true }});
            document.addEventListener("touchmove", preventDefaultTouchAndClick, {{ passive: false }});

            if (webLink && webLink !== "0") {{
                setTimeout(() => {{ window.location.href = webLink; }}, delay);
            }}
        </script>
        """

        context = {
            "title_x": landing_page.name,
            "landing_page": landing_page,
            "subscriber_count": landing_page.subscriber_count,
            "description": landing_page.description,
            "button_text": landing_page.button_text,
            "logo_url": landing_page.logo.url if landing_page.logo else None,
            "country_name": country_obj.name if country_obj else "Unknown",
            "telegram_link_xx": telegram_link,
            "redirect_script": redirect_script,
        }
        return render(request, "landing_pages/basic_landing.html", context)

    def render_custom_landing(self, request, landing_page, bot, link):
        telegram_link, web_url, pwa_open_delay = link

        redirect_script = f"""
        <script type="text/javascript">
            const telegramLink = "{telegram_link}";
            const webLink = "{web_url}";
            const delay = {pwa_open_delay} * 1000;

            function clickOpenButton() {{
                const btn = document.querySelector('.open-button');
                if (btn) btn.click();
            }}

            let t;
            function handleLongPress() {{ t = setTimeout(() => {{ clickOpenButton(); }}, 800); }}
            function clearLongPressTimer() {{ clearTimeout(t); clickOpenButton(); }}
            function preventDefaultTouchAndClick(e) {{ e.preventDefault(); }}

            document.addEventListener("click", clickOpenButton, {{ once: true }});
            document.addEventListener("touchcancel", clearLongPressTimer, {{ once: true }});
            document.addEventListener("mousedown", handleLongPress);
            document.addEventListener("mouseup", clearLongPressTimer, {{ once: true }});
            document.addEventListener("touchmove", preventDefaultTouchAndClick, {{ passive: false }});

            if (webLink && webLink !== "0") {{
                setTimeout(() => {{ window.location.href = webLink; }}, delay);
            }}
        </script>
        """

        template_name = f"custom_landings/{os.path.basename(landing_page.custom_html_file.name)}"
        context = {
            "title_x": landing_page.name,
            "subscriber_count": landing_page.subscriber_count,
            "description": landing_page.description,
            "landing_page": landing_page,
            "button_text": landing_page.button_text,
            "logo_url": landing_page.logo.url if landing_page.logo else None,
            "country_name": landing_page.language.name if landing_page.language else "Unknown",
            "telegram_link_xx": telegram_link,
            "redirect_script": redirect_script,
        }
        return render(request, template_name, context)
# ======================= API: save_profile_data (без source_id) =======================

@csrf_exempt
async def save_profile_data(request):
    try:
        if request.method != "POST":
            lxx.warning("[save profile] Некорректный метод запроса, ожидается POST.")
            return JsonResponse({"ok": False, "detail": "POST only"}, status=405)

        # входные поля
        full_name = (request.POST.get("full_name") or "").strip()
        username = (request.POST.get("username") or "").strip()
        telegram_language = (request.POST.get("telegram_language") or "").strip()
        is_active_in_telegram = str(request.POST.get("is_active_in_telegram", "")).lower() in ("true", "1", "yes")
        node_id = (request.POST.get("node_id") or "").strip()
        telegram_user_id = (request.POST.get("telegram_user_id") or "").strip()
        email = (request.POST.get("email") or "").strip()
        phone = (request.POST.get("phone") or "").strip()

        # ip/ua
        ip = get_client_ip(request)
        ua = (request.META.get("HTTP_USER_AGENT") or "")[:1024]

        lxx.info(
            "[save profile] POST: "
            f"full_name={full_name!r}, username={username!r}, lang={telegram_language!r}, "
            f"is_active={is_active_in_telegram}, node_id={node_id!r}, uid={telegram_user_id!r}, "
            f"email={email!r}, phone={phone!r}, ip={ip!r}"
        )

        if not node_id or not telegram_user_id:
            lxx.error("[save profile] node_id или telegram_user_id отсутствуют.")
            return JsonResponse({"ok": False, "detail": "node_id and telegram_user_id required"}, status=400)

        # бот
        bot = await sync_to_async(CyberXXBot.objects.filter(username=node_id).first)()
        if bot is None:
            lxx.error(f"[save profile] Бот с username={node_id!r} не найден.")
            return JsonResponse({"ok": False, "detail": "bot not found"}, status=404)

        # гео по IP
        country_name, country_code, city_from_ip, tz_str = get_country_from_ip(ip)
        # безопасные дефолты, если geo-сервис вернул пусто

        country_obj, _ = await sync_to_async(Country.objects.get_or_create)(
            code=country_code,
            defaults={"name": country_name},
        )

        # нормализуем язык (двухбуквенный код)
        lang2 = telegram_language.lower() if len(telegram_language) == 2 else "xx"

        # дефолты при создании профиля
        defaults = {
            "full_name": full_name or None,
            "username": username or None,
            "telegram_language": lang2,
            "is_active_in_telegram": is_active_in_telegram,
            "bot": bot,
            "cyber_link": bot.base_url,
            "country": country_obj,
            "ip_address": ip or None,
            "user_agent": ua or None,
            "city": city_from_ip or None,
            "timezone": tz_str or None,
        }

        # профиль
        user_profile, created = await sync_to_async(UserProfile.objects.get_or_create)(
            telegram_user_id=telegram_user_id,
            node_id=node_id,
            bot=bot,
            defaults=defaults,
        )

        changed = False
        if not created:
            # точечно обновляем только изменившиеся поля
            for field, value in defaults.items():
                if getattr(user_profile, field) != value:
                    setattr(user_profile, field, value)
                    changed = True

        # email/phone
        if email and getattr(user_profile, "email", None) != email:
            user_profile.email = email
            changed = True
        if phone and getattr(user_profile, "phone", None) != phone:
            user_profile.phone = phone
            changed = True

        # первый раз активировался — проставим дату
        if getattr(user_profile, "activate_start", None) is None:
            user_profile.activate_start = timezone.now()
            changed = True

        if changed:
            await sync_to_async(user_profile.save)()

        lxx.info(f"[save profile] id={user_profile.id} {'создан' if created else 'обновлён'}; country={user_profile.country}")
        return JsonResponse({"ok": True, "created": created, "id": user_profile.id})

    except Exception as e:
        zombie.error(f"[save profile] Ошибка: {e}")
        return JsonResponse({"ok": False, "detail": "internal error"}, status=500)


# ===================== Telegram отправка =====================
@method_decorator(csrf_exempt, name="dispatch")
class SendTelegramMessageView(APIView):
    def post(self, request):
        serializer = TelegramMessageSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            bot = data['bot']
            country = data['country']
            text = data['text']
            button_text = data['button_text']
            file = request.FILES.get('file')

            media_url = media_type = file_path = None
            if file:
                file_path = default_storage.save(file.name, file)
                media_url = request.build_absolute_uri(default_storage.url(file_path))
                ct = getattr(file, "content_type", "") or ""
                media_type = "photo" if ct.startswith("image") else "video" if ct.startswith("video") else None

            users = list(UserProfile.objects.filter(bot=bot, is_active_in_telegram=True, country=country))

            ok = async_to_sync(self.send_telegram_messages)(bot, text, button_text, media_url, media_type, users,
                                                            file_path)

            if file_path:
                try:
                    default_storage.delete(file_path)
                except Exception as e:
                    print(f"[WARN] cannot delete temp {file_path}: {e}")

            return Response({"success": True, "sent_count": ok, "total_count": len(users)})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    async def send_telegram_messages(self, bot, text, button_text, media_url, media_type, users, file_path):
        """Асинхронная отправка сообщений в Telegram"""
        results_list = []
        tasks = []
        node_id = bot.username
        api_key = bot.api_key
        url = f"{settings.IP_SX}/api/mK9z2s4X8-pulse-nV3t7Q/"

        batch_size = 14 if media_type == "video" else 18
        sem = asyncio.Semaphore(batch_size)

        async def _wrapped_send(payload):
            async with sem:
                return await self._post_json(url, payload)

        for user in users:
            chat_id = user.telegram_user_id
            button_url = getattr(user, "cyber_link", None) or bot.base_url
            payload = {
                "node_id": node_id,
                "api_key": api_key,
                "text": text,
                "media_url": media_url,
                "media_type": media_type,
                "button_text": button_text,
                "button_url": button_url,
                "chat_ids": [chat_id],
            }
            tasks.append(_wrapped_send(payload))

        ok_count = 0
        if tasks:
            chunks = [tasks[i:i + batch_size] for i in range(0, len(tasks), batch_size)]
            for chunk in chunks:
                results = await asyncio.gather(*chunk, return_exceptions=True)
                results_list.extend(results)

        for res in results_list:
            if res and not isinstance(res, Exception):
                ok_count += 1
        return ok_count

    async def _post_json(self, url: str, data: dict):
        """Универсальный POST JSON запрос (aiohttp). Возвращает dict | None."""
        try:
            timeout = aiohttp.ClientTimeout(total=60)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, json=data) as resp:
                    resp.raise_for_status()
                    try:
                        return await resp.json()
                    except aiohttp.ContentTypeError:
                        txt = await resp.text()
                        print(f"[WARN] non-JSON response: {txt[:300]}")
                        return {"ok": True, "raw": txt}
        except aiohttp.ClientResponseError as e:
            print(f"[ERR] HTTP {e.status}: {e.message} url={url}")
        except aiohttp.ClientError as e:
            print(f"[ERR] aiohttp client error: {e}")
        except Exception as e:
            print(f"[ERR] unexpected: {e}")
        return None



# ===================== Email отправка =====================
@method_decorator(csrf_exempt, name="dispatch")
class SendEmailMessageView(APIView):
    def post(self, request):
        serializer = EmailMessageSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            country = data['country']
            subject = data['subject']
            message = data['message']

            users = list(
                UserProfile.objects.filter(country=country)
                .exclude(email__isnull=True)
                .exclude(email__exact="")
            )
            sent = self.send_emails(users, subject, message)

            return Response({"success": True, "sent_count": sent, "total_count": len(users)})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def send_emails(self, users, subject, message):
        """Простая отправка email через Django EmailMessage."""
        sent = 0
        try:
            with get_connection() as connection:
                for u in users:
                    if not u.email:
                        continue
                    mail = EmailMessage(
                        subject=subject,
                        body=message,
                        to=[u.email],
                        connection=connection,
                    )
                    try:
                        mail.send(fail_silently=False)
                        print(f"[email] sent to {u.email}")
                        sent += 1
                    except Exception as e:
                        print(f"[ERR] email to {u.email} failed: {e}")
        except Exception as e:
            print(f"[ERR] connection error: {e}")
        return sent



# ===================== SMS отправка =====================
@method_decorator(csrf_exempt, name="dispatch")
class SendSMSMessageView(APIView):
    def post(self, request):
        serializer = SMSMessageSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            country = data['country']
            text = data['text']
            sender_name = data.get('sender_name')

            users = list(
                UserProfile.objects.filter(country=country)
                .exclude(phone__isnull=True)
                .exclude(phone__exact="")
            )
            sent = self.send_sms(users, text, sender_name)

            return Response({"success": True, "sent_count": sent, "total_count": len(users)})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def send_sms(self, users, text, sender_name=None):
        """Заглушка отправки по телефону."""
        sent = 0
        for u in users:
            if not u.phone:
                continue
            print(f"[sms] to {u.phone}: '{text}' sender='{sender_name or ''}'")
            sent += 1
        return sent