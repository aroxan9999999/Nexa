from rest_framework import serializers
import os
from urllib.parse import urlparse
import os
import logging
from logging.handlers import RotatingFileHandler
from urllib.parse import urlparse
from rest_framework import serializers
from .plinko_data_x import plinko_data
from .zombie_error import zombie

plinko_data = logging.getLogger("plinko_data")
plinko_data.setLevel(logging.INFO)

handler = RotatingFileHandler("[specter]/plinko_data.log", maxBytes=10 * 1024 * 1024, backupCount=2)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
plinko_data.addHandler(handler)

class CreateBotSerializer(serializers.Serializer):
    node_id = serializers.CharField(max_length=255)
    api_key = serializers.CharField(max_length=255)
    activate = serializers.BooleanField(default=False)


class DeleteBotSerializer(serializers.Serializer):
    node_id = serializers.CharField(max_length=255)
    api_key = serializers.CharField(max_length=255)


class SendMessageSerializer(serializers.Serializer):
    node_id = serializers.CharField(max_length=255)
    api_key = serializers.CharField(max_length=255)
    text = serializers.CharField(max_length=500)
    media_url = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    media_type = serializers.ChoiceField(choices=[('photo', 'photo'), ('video', 'video')], required=False, allow_null=True)
    button_text = serializers.CharField(max_length=100)
    button_url = serializers.URLField()
    chat_ids = serializers.ListField(child=serializers.IntegerField())

    def validate(self, data):
        media_url = data.get('media_url')
        media_type = data.get('media_type')
        button_text = data.get('button_text')
        button_url = data.get('button_url')

        plinko_data.info(f"Получены данные для валидации: {data}")

        if not media_url:
            plinko_data.warning("[plinko_data] Отсутствует media_url - медиа не будет отправлено.")
        if not media_type:
            plinko_data.warning("[plinko_data] Отсутствует media_type - медиа не будет отправлено.")

        check_media = lambda url, m_type: (
            (m_type and not url) or (url and not m_type),
            "Если указан media_url, необходимо указать тип медиа (media_type) и наоборот."
        )

        check_buttons = lambda btn_text, btn_url: (
            (btn_text and not btn_url) or (btn_url and not btn_text),
            "Если указано одно из полей button_text или button_url, необходимо указать оба."
        )

        if check_media(media_url, media_type)[0]:
            error_msg = check_media(media_url, media_type)[1]
            plinko_data.error(f"[plinko_data] Ошибка валидации: {error_msg}")
            zombie.error(f"[zombie] Ошибка валидации: {error_msg}")
            raise serializers.ValidationError(error_msg)

        if check_buttons(button_text, button_url)[0]:
            error_msg = check_buttons(button_text, button_url)[1]
            plinko_data.error(f"[plinko_data] Ошибка валидации: {error_msg}")
            zombie.error(f"[zombie] Ошибка валидации: {error_msg}")
            raise serializers.ValidationError(error_msg)

        if media_url:
            parsed_url = urlparse(media_url)
            is_local_file = not parsed_url.scheme or parsed_url.scheme not in ['http', 'https']
            if is_local_file and not os.path.isfile(media_url):
                error_msg = "Файл не найден или к нему нет доступа по указанному пути."
                plinko_data.error(f"[plinko_data] Ошибка валидации: {error_msg}")
                zombie.error(f"[zombie] Ошибка валидации: {error_msg}")
                raise serializers.ValidationError(error_msg)

        plinko_data.info("[plinko_data] Данные успешно прошли валидацию.")
        return data