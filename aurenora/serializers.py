# aurenora/serializers.py
from rest_framework import serializers
from .models import Country, CyberXXBot

class TelegramMessageSerializer(serializers.Serializer):
    country = serializers.PrimaryKeyRelatedField(queryset=Country.objects.all())
    bot = serializers.PrimaryKeyRelatedField(queryset=CyberXXBot.objects.filter(active=True))
    button_text = serializers.CharField(max_length=100)
    text = serializers.CharField()
    file = serializers.FileField(required=False, allow_null=True)

class EmailMessageSerializer(serializers.Serializer):
    country = serializers.PrimaryKeyRelatedField(queryset=Country.objects.all())
    subject = serializers.CharField(max_length=150)
    message = serializers.CharField()

class SMSMessageSerializer(serializers.Serializer):
    country = serializers.PrimaryKeyRelatedField(queryset=Country.objects.all())
    text = serializers.CharField()
    sender_name = serializers.CharField(max_length=50, required=False, allow_blank=True)