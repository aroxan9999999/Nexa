from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

# Устанавливаем переменную окружения для конфигурации Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'luminix_x.settings')

# Создаем экземпляр приложения Celery
app = Celery('luminix_x')

# Загружаем настройки из Django settings с префиксом CELERY
app.config_from_object('django.conf:settings', namespace='CELERY')

# Автоматически находит и регистрирует задачи, определенные в приложениях Django
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
