import asyncio
from django.core.management.base import BaseCommand
from aurenora.pulsar import pulsar
import logging


class Command(BaseCommand):
    help = "Запуск всех активных ботов"

    def handle(self, *args, **options):
        self.stdout.write("Запуск всех активных ботов...")
        try:
            asyncio.run(self.start_bots())
            self.stdout.write(self.style.SUCCESS("Боты успешно запущены."))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Ошибка при запуске ботов: {e}"))

    async def start_bots(self):
        self.stdout.write("Инициализация запуска ботов...")
        await pulsar.scan_and_activate_bots()
        self.stdout.write("Процессы для всех ботов инициализированы.")



