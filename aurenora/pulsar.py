import os
import re
import signal
import uuid
import time
import asyncio
import logging
import multiprocessing
from logging.handlers import RotatingFileHandler

from asgiref.sync import sync_to_async
from django.core.cache import cache

import httpx

from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import Command
from aiogram.types import (
    Message,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    MenuButtonWebApp,
)
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from mortal_shade.zombie_error import zombie
from aurenora.models import CyberXXBot  # UserProfile напрямую здесь не нужен
from django.conf import settings

# ============================ ЛОГИ ============================
plinko = logging.getLogger("plinko")
plinko.setLevel(logging.INFO)
file_handler = RotatingFileHandler("[specter]/plinko.log", maxBytes=10 * 1024 * 1024, backupCount=4)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
file_handler.setFormatter(formatter)
plinko.addHandler(file_handler)

# ============================ ВАЛИДАЦИЯ ЕMAIL/PHONE ============================
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
PHONE_RE = re.compile(r"^\+?\d{7,15}$")  # цифры, опц. '+', длина 7-15

def is_email(s: str) -> bool:
    return bool(EMAIL_RE.match((s or "").strip()))

def is_phone(s: str) -> bool:
    return bool(PHONE_RE.match((s or "").strip()))

# ============================ FSM для контактов ============================
class ContactFSM(StatesGroup):
    email = State()
    phone = State()

# ============================ ОСНОВНОЙ КЛАСС ============================
class Pulsar:

    async def scan_and_activate_bots(self):
        """Метод для активации и запуска всех ботов из базы данных."""
        plinko.info("[plinko] Метод scan_and_activate_bots начат.")

        bots = await sync_to_async(list)(CyberXXBot.objects.all())
        plinko.info(f"[plinko] Найдено {len(bots)} ботов для запуска.")

        for bot in bots:
            try:
                if bot.process_id:
                    plinko.info(f"[plinko] Завершаем процесс с PID {bot.process_id} для бота с ID {bot.id}.")
                    await self.kill_process(bot.process_id)
            except Exception as e:
                plinko.warning(f"[plinko] Не удалось завершить процесс с PID {bot.process_id}: {e}")
                zombie.warning(f"[zombie] Не удалось завершить процесс с PID {bot.process_id}: {e}")

            plinko.info(f"[plinko] Подготовка к запуску процесса для бота с ID {bot.id}.")
            process = multiprocessing.Process(target=self.start_bot_process, args=(bot.username, bot.api_key))
            process.start()

            bot.process_id = process.pid
            await sync_to_async(bot.save)()
            plinko.info(f"[plinko] Процесс для бота с ID {bot.id} запущен с PID {process.pid}.")

        plinko.info("[plinko] Метод scan_and_activate_bots завершен. Все процессы запущены.")

    def is_process_running(self, pid):
        """Проверяет, активен ли процесс с данным PID."""
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False

    async def kill_process(self, pid):
        """Убивает процесс с указанным PID."""
        try:
            os.kill(pid, signal.SIGKILL)
            plinko.info(f"[plinko-process] Процесс с PID {pid} успешно завершен.")
        except OSError as e:
            plinko.error(f"[plinko-process] Ошибка при завершении процесса с PID {pid}: {e}")
            zombie.error(f"[zombie] Ошибка при завершении процесса с PID {pid}: {e}")

    async def activate_new_bot(self, node_id, api_key):
        """Метод для активации и запуска нового бота."""
        plinko.info(f"Подготовка к запуску нового бота с node_id {node_id}.")
        process = multiprocessing.Process(target=self.start_bot_process, args=(node_id, api_key))
        process.daemon = False
        process.start()

        bot = await sync_to_async(CyberXXBot.objects.get)(username=node_id)
        bot.process_id = process.pid
        await sync_to_async(bot.save)()
        plinko.info(f"[plinko-activate] Новый бот с node_id {node_id} успешно запущен с PID {process.pid}.")

    async def shutdown_node(self, node_id, process_id):
        """Метод для остановки бота по его process_id."""
        plinko.info(f"[plinko kill] Подготовка к завершению бота с node_id {node_id}.")

        if process_id:
            try:
                os.kill(process_id, 9)
                plinko.info(f"[plinko kill] Процесс с PID {process_id} для бота с node_id {node_id} успешно завершен.")
            except OSError as e:
                plinko.error(f"[plinko kill] Ошибка при завершении процесса с PID {process_id} для бота с node_id {node_id}: {e}")
                zombie.error(f"[zombie] Ошибка при завершении процесса с PID {process_id} для бота с node_id {node_id}: {e}")
        else:
            plinko.warning(f"[plinko kill] У бота с node_id {node_id} отсутствует process_id. Завершение невозможно.")

    @staticmethod
    def start_bot_process(node_id, api_key):
        """Функция для запуска бота в отдельном процессе."""
        try:
            plinko.info(f"[plinko-start] Запуск процесса для бота с node_id {node_id} начат.")
            asyncio.run(Pulsar.run_bot(node_id, api_key))
            plinko.info(f"[plinko-start] Процесс для бота с node_id {node_id} успешно завершен.")
        except Exception as e:
            plinko.error(f"[plinko-start] Ошибка при запуске процесса для бота с node_id {node_id}: {e}")
            zombie.error(f"[zombie] Ошибка при запуске процесса для бота с node_id {node_id}: {e}")

    @staticmethod
    async def run_bot(node_id: str, api_key: str):
        """Запускает бота и обновляет данные в StatusX."""
        bot_instance = Bot(token=api_key)
        dp = Dispatcher()

        Pulsar.register_handlers(dp, node_id, bot_instance)

        await dp.start_polling(bot_instance, skip_updates=True)
        plinko.info(f"[plinko-pool] Бот с ID {node_id} успешно запущен.")

    # ============================ ОТПРАВКА ПРОФИЛЯ (1 РАЗ, БЕЗ source_id) ============================
    @staticmethod
    async def send_profile_data(
        full_name: str | None,
        username: str | None,
        telegram_language: str | None,
        is_active_in_telegram: bool,
        node_id: str,
        telegram_user_id: str,
        email: str | None = None,
        phone: str | None = None,
    ):
        """Асинхронный метод для отправки данных профиля на сервер через API (ровно 1 раз)."""
        url = f"{settings.IP_SX}/save_profile_data/"
        data = {
            "full_name": full_name,
            "username": username,
            "telegram_language": telegram_language,
            "is_active_in_telegram": str(is_active_in_telegram).lower(),
            "node_id": node_id,
            "telegram_user_id": telegram_user_id,
        }
        if email:
            data["email"] = email
        if phone:
            data["phone"] = phone

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, data=data)
                if response.status_code == 200:
                    plinko.info("[save-profile] Data sent successfully.")
                else:
                    plinko.error(f"[save-profile] Failed to send data: {response.status_code} {response.text}")
                    zombie.error(f"[zombie] Failed to send data:{data} {response.status_code} {response.text}")
        except httpx.RequestError as exc:
            plinko.error(f"[save-profile] Network error occurred: {exc}")
            zombie.error(f"[zombie] Network error occurred: {exc}")

    # ============================ ХЭНДЛЕРЫ ============================
    @staticmethod
    def register_handlers(dp: Dispatcher, node_id: str, bot_instance: Bot):
        """Регистрирует хэндлеры для команды /start и сбор контактов (email/phone) единоразово."""
        router = Router()

        @router.message(Command("start"))
        async def start_command_handler(message: Message, state: FSMContext):
            try:
                chat_id = message.chat.id
                telegram_user_id = str(chat_id)
                full_name = message.from_user.full_name
                username = message.from_user.username
                telegram_language = message.from_user.language_code

                plinko.info(f"[plinko-register] /start от {telegram_user_id}")

                if not bot_instance or not node_id:
                    plinko.error(f"[plinko-register] bot_instance или node_id не инициализированы для бота {node_id}")
                    zombie.error(f"[zombie] bot_instance или node_id не инициализированы для бота {node_id}")
                    return

                # уже отправляли? — прекращаем
                submitted_key = f"profile_submitted:{telegram_user_id}"
                if cache.get(submitted_key):
                    await message.answer("Профиль уже сохранён ✅")
                    return

                # сохраняем базу в кэш (без source_id!)
                base_key = f"profile_base:{telegram_user_id}"
                cache.set(
                    base_key,
                    {
                        "full_name": full_name,
                        "username": username,
                        "telegram_language": telegram_language,
                        "is_active_in_telegram": True,
                        "node_id": node_id,
                        "telegram_user_id": telegram_user_id,
                    },
                    timeout=60 * 30,  # 30 минут
                )

                # стартуем FSM: запрос email
                await state.set_state(ContactFSM.email)
                await message.answer("Укажи, пожалуйста, свой email:")
            except Exception as e:
                plinko.error(f"[plinko-register] Общая ошибка в /start для node_id {node_id}: {e}")
                zombie.error(f"[zombie] Общая ошибка в /start для node_id {node_id}: {e}")

        # ===== шаг 1: email =====
        @router.message(ContactFSM.email)
        async def on_email(message: Message, state: FSMContext):
            uid = str(message.chat.id)

            # если уже отправлено — выходим
            if cache.get(f"profile_submitted:{uid}"):
                await state.clear()
                await message.answer("Профиль уже сохранён ✅")
                return

            email = (message.text or "").strip()
            if not is_email(email):
                await message.answer("Некорректный email. Пример: user@example.com\nВведите ещё раз:")
                return

            await state.update_data(email=email)
            await state.set_state(ContactFSM.phone)
            await message.answer("Теперь номер телефона (например, +79991234567):")

        # ===== шаг 2: phone =====
        @router.message(ContactFSM.phone)
        async def on_phone(message: Message, state: FSMContext):
            uid = str(message.chat.id)

            if cache.get(f"profile_submitted:{uid}"):
                await state.clear()
                await message.answer("Профиль уже сохранён ✅")
                return

            phone = (message.text or "").strip()
            if not is_phone(phone):
                await message.answer("Некорректный номер. Разрешены только цифры и опционально '+', длина 7–15. Введите ещё раз:")
                return

            base_key = f"profile_base:{uid}"
            base = cache.get(base_key) or {}
            if not base:
                await state.clear()
                await message.answer("Сессия устарела. Нажмите /start, чтобы начать заново.")
                return

            data = await state.get_data()
            email = data.get("email")

            try:
                await Pulsar.send_profile_data(
                    full_name=base["full_name"],
                    username=base["username"],
                    telegram_language=base["telegram_language"],
                    is_active_in_telegram=base["is_active_in_telegram"],
                    node_id=base["node_id"],
                    telegram_user_id=base["telegram_user_id"],
                    email=email,
                    phone=phone,
                )
                plinko.info(f"[plinko-register] Профиль отправлен (1 раз): {uid} email={email} phone={phone}")
                await message.answer("Спасибо! Профиль сохранён ✅")

                # помечаем, чтобы не повторять
                cache.set(f"profile_submitted:{uid}", True, timeout=60 * 60 * 24 * 365)  # 1 год
            except Exception as e:
                plinko.error(f"[plinko-register] Ошибка при отправке профиля {uid}: {e}")
                await message.answer("Упс, не удалось сохранить. Попробуйте /start позже.")
                return
            finally:
                cache.delete(base_key)
                await state.clear()

        # (опционально) коллбэк «Начать» — перезапуск формы
        @router.callback_query(F.data == "start")
        async def cb_start(call, state: FSMContext):
            uid = str(call.from_user.id)
            if cache.get(f"profile_submitted:{uid}"):
                await call.message.answer("Профиль уже сохранён ✅")
                return
            await state.set_state(ContactFSM.email)
            await call.message.answer("Укажи, пожалуйста, свой email:")

        dp.include_router(router)
        plinko.info(f"[plinko-register] Хэндлеры успешно зарегистрированы для бота с ID {node_id}.")

    # ============================ МАССОВАЯ РАССЫЛКА ============================
    async def xx_pulse(
        self,
        node_id,
        chat_ids,
        text,
        media_url=None,
        media_type=None,
        button_text=None,
        button_url=None,
    ):
        if not node_id or not chat_ids or not text:
            plinko.error(f"[xx_pulse] Отсутствуют обязательные параметры: node_id={node_id}, chat_ids={chat_ids}, text={text}")
            zombie.error(f"[zombie] Отсутствуют обязательные параметры: node_id={node_id}, chat_ids={chat_ids}, text={text}")
            return
        try:
            bot_status = await sync_to_async(CyberXXBot.objects.get)(username=node_id)
            async with Bot(token=bot_status.api_key) as bot_instance:
                plinko.info(f"[xx_pulse] Бот с ID {node_id} успешно инициализирован.")

                keyboard = None
                if button_text and button_url:
                    keyboard = InlineKeyboardMarkup(
                        inline_keyboard=[[InlineKeyboardButton(text=button_text, web_app={"url": button_url})]]
                    )
                    try:
                        menu_button = MenuButtonWebApp(text="Play", web_app={"url": button_url})
                        await bot_instance.set_chat_menu_button(menu_button=menu_button)
                        plinko.info(f"[xx_pulse] Кнопка Play успешно добавлена в меню: {button_url}")
                    except Exception as e:
                        plinko.error(f"[xx_pulse] Ошибка при добавлении кнопки Play в меню: {e}")

                tasks = []
                if media_type in ["photo", "video"] and media_url:
                    plinko.info(f"[xx_pulse] Начата отправка медиа {media_type} с URL: {media_url}")
                    for chat_id in chat_ids:
                        if media_type == "photo":
                            tasks.append(
                                bot_instance.send_photo(chat_id=chat_id, photo="https://sonicliine.com/media/resumes/photos/sonuc_fEi9MiH.png", caption=text, reply_markup=keyboard)
                            )
                        elif media_type == "video":
                            tasks.append(
                                bot_instance.send_video(
                                    chat_id=chat_id,
                                    video=media_url,
                                    caption=text,
                                    supports_streaming=True,
                                    reply_markup=keyboard,
                                )
                            )
                    await asyncio.gather(*tasks)
                    plinko.info(f"[xx_pulse] Медиа успешно отправлено в чаты {chat_ids}")
                else:
                    tasks = [bot_instance.send_message(chat_id=chat_id, text=text, reply_markup=keyboard) for chat_id in chat_ids]
                    await asyncio.gather(*tasks)
                    plinko.info(f"[xx_pulse] Текстовое сообщение успешно отправлено в чаты {chat_ids}")
        except Exception as e:
            plinko.error(f"[xx_pulse] Ошибка в xx_pulse для node_id {node_id}: {e}")
            zombie.error(f"[zombie] Ошибка в xx_pulse для node_id {node_id}: {e}")


pulsar = Pulsar()


"""
Модуль для управления ботами Telegram через библиотеку Aiogram.

Основные компоненты:
--------------------
1. Класс Pulsar:
   - Управляет активацией, запуском и остановкой ботов.
   - Обрабатывает команду `/start` и собирает контакты через FSM.
   - Поддерживает отправку сообщений с медиа через метод `xx_pulse`.

2. Логирование:
   - Логгеры `plinko` и `zombie` обеспечивают детализированное логирование.

3. Асинхронные API-запросы:
   - `send_profile_data` отправляет профиль пользователя единоразово (с email/phone), БЕЗ source_id.

4. Управление процессами:
   - Управляет процессами ботов (запуск/остановка).

Хэндлеры:
---------
- `/start`: кладёт базовые данные в кэш, затем спрашивает email и телефон.
- После получения телефона — единоразовая отправка профиля и установка флага `profile_submitted:{uid}`.
"""
