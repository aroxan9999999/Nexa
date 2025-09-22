import time
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from asgiref.sync import async_to_sync, sync_to_async
from .serializers import SendMessageSerializer
from aurenora.models import CyberXXBot
from django.db.models import Q
from .plinko_data_x import plinko_data
from aurenora.pulsar import pulsar
from .zombie_error import zombie


class SendMessageView(APIView):
    def post(self, request):
        plinko_data.info(f"Получен POST-запрос на отправку сообщения: {request.data}")

        serializer = SendMessageSerializer(data=request.data)
        if serializer.is_valid():
            node_id = serializer.validated_data['node_id']
            api_key = serializer.validated_data['api_key']
            text = serializer.validated_data['text']
            media_url = serializer.validated_data.get('media_url')
            media_type = serializer.validated_data.get('media_type')
            button_text = serializer.validated_data.get('button_text')
            button_url = serializer.validated_data.get('button_url')
            chat_ids = serializer.validated_data.get('chat_ids', [])

            try:
                # Проверяем, существует ли бот с указанными данными
                bot_exists = CyberXXBot.objects.filter(username=node_id, api_key=api_key, active=True).exists()
                if not bot_exists:
                    error_msg = "Доступ к боту с указанными данными невозможен."
                    plinko_data.error(f"[plinko message] {error_msg}")
                    zombie.error(f"[zombie] {error_msg}")
                    return Response({"message": error_msg}, status=status.HTTP_403_FORBIDDEN)
                async_to_sync(pulsar.xx_pulse)(
                    node_id, chat_ids, text, media_url, media_type, button_text, button_url
                )
                plinko_data.info(f"[plinko message] Сообщение успешно отправлено для бота {node_id}.")
                return Response({"message": "Сообщение успешно отправлено!"}, status=status.HTTP_200_OK)

            except Exception as e:
                error_msg = f"Ошибка при отправке сообщения для бота с ID {node_id}: {str(e)}"
                plinko_data.error(f"[plinko message] {error_msg}")
                zombie.error(f"[zombie] {error_msg}")
                return Response({"error": error_msg}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            plinko_data.error(f"[plinko message] Ошибка сериализатора: {serializer.errors}")
            zombie.error(f"[zombie] Ошибка сериализатора: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


"""
### Класс SendMessageView

Предназначен для обработки POST-запросов на отправку сообщений через API.

#### Основные функции:
1. **Валидация данных запроса**:
   - Проверяет данные, используя сериализатор `SendMessageSerializer`.
   - Убедитесь, что переданы корректные параметры (`node_id`, `api_key`, `text` и т. д.).

2. **Проверка существования бота**:
   - Убедитесь, что бот с заданным `node_id` и `api_key` существует и активен.

3. **Отправка сообщения**:
   - Использует метод `xx_pulse` из класса `Pulsar` для отправки текстового сообщения или медиафайла.

4. **Обработка ошибок**:
   - Логирует ошибки сериализатора, проверки или отправки сообщений.
   - Возвращает соответствующие HTTP-статусы и сообщения об ошибках.

#### Методы:
- `post(self, request)`: 
  - Обрабатывает POST-запросы для отправки сообщения.
  - Валидация данных и вызов метода отправки сообщения.

#### Логирование:
- **Логгер `plinko_data`**:
  - Логирует успешные операции и общую информацию о запросах.
- **Логгер `zombie`**:
  - Логирует ошибки и проблемы при работе с запросами.

#### Возвращаемые статусы:
- **200 OK**:
  - Успешная отправка сообщения.
- **400 Bad Request**:
  - Ошибка валидации данных запроса.
- **403 Forbidden**:
  - Недопустимый доступ к боту.
- **500 Internal Server Error**:
  - Ошибка во время отправки сообщения.

#### Пример данных запроса:
```json
{
    "node_id": "bot_username",
    "api_key": "bot_api_key",
    "text": "Привет!",
    "media_url": "https://example.com/image.jpg",
    "media_type": "photo",
    "button_text": "Нажми сюда",
    "button_url": "https://example.com",
    "chat_ids": [123456789, 987654321]
}
"""