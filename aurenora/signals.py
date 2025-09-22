import asyncio
import logging
import os
from logging.handlers import RotatingFileHandler
import httpx
from asgiref.sync import async_to_sync
from aurenora.pulsar import pulsar
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import CyberXXBot
import requests
from mortal_shade.zombie_error import zombie
# Настройка логгера для сигналов
plinko_signal = logging.getLogger("plinko_signal")
plinko_signal.setLevel(logging.INFO)

# Обработчик файлового логгера с ротацией файлов по 3 МБ, до 3 файлов
signal_file_handler = RotatingFileHandler("[specter]/plinko_signal.log", maxBytes=3 * 1024 * 1024, backupCount=3)
signal_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
signal_file_handler.setFormatter(signal_formatter)

plinko_signal.addHandler(signal_file_handler)

@receiver(post_save, sender=CyberXXBot)
def activate_bot(sender, instance, created, **kwargs):
    """Срабатывает после создания нового бота и отправляет запрос на активацию."""
    if created:
        try:
            plinko_signal.info(f"[plinko_signal] Попытка активации нового бота: {instance.username}")
            async_to_sync(pulsar.activate_new_bot)(instance.username, instance.api_key)
            plinko_signal.info(f"[plinko_signal] Бот {instance.username} успешно активирован.")
        except Exception as e:
            plinko_signal.error(f"[plinko_signal] Ошибка при активации бота {instance.username}: {e}")
            zombie.error(f"[zombie] Ошибка при активации бота {instance.username}: {e}")


@receiver(post_delete, sender=CyberXXBot)
async def delete_bot_from_system(sender, instance, **kwargs):
    """Обработчик, который срабатывает после удаления бота и завершает процесс бота."""
    try:
        plinko_signal.info(f"[plinko_signal] Попытка завершения работы бота с username {instance.username}.")

        # Передаем process_id напрямую, избегая поиска в базе данных
        await pulsar.shutdown_node(instance.username, instance.process_id)

        plinko_signal.info(f"[plinko_signal] Бот с username {instance.username} успешно завершен.")
    except Exception as e:
        plinko_signal.error(f"[plinko_signal] Ошибка при завершении работы бота с username {instance.username}: {e}")
        zombie.error(f"[zombie] Ошибка при завершении работы бота с username {instance.username}: {e}")


"""
    ---
    ### Сигналы для модели `CyberXXBot`
    
    #### Основное:
    - **`activate_bot`**: Активирует процесс бота при создании новой записи.
    - **`delete_bot_from_system`**: Завершает процесс бота при удалении записи.
    
    #### Логирование:
    - **Логгер**: `plinko_signal` (файл `[specter]/plinko_signal.log`).
    - **Ошибки**: Записываются в `plinko_signal` и `zombie`.
    
    ---
    
    ### Описание сигналов:
    
    #### `activate_bot`
    - Срабатывает после создания объекта.
    - Использует `pulsar.activate_new_bot` для запуска процесса.
    
    #### `delete_bot_from_system`
    - Срабатывает после удаления объекта.
    - Завершает процесс бота через `pulsar.shutdown_node`.
    
    ---
    
    ### Пример:
    1. **Создание**: Активирует бота и записывает PID в базу.
    2. **Удаление**: Завершает процесс по PID.
    
    ---
"""
