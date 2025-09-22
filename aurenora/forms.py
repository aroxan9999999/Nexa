# forms.py
from django import forms
from .models import Country, CyberXXBot

class AuraMessageForm(forms.Form):
    country = forms.ModelChoiceField(queryset=Country.objects.all(), label="Страна", required=True)
    bot = forms.ModelChoiceField(queryset=CyberXXBot.objects.filter(active=True), label="Бот", required=True)
    button_x = forms.CharField(max_length=100, label='Текст кнопки', widget=forms.TextInput(attrs={'placeholder': 'кнопка'}))
    text = forms.CharField(widget=forms.Textarea(attrs={'rows': 1, 'placeholder': 'Введите сообщение...'}), label="Сообщение", required=True)
    file = forms.FileField(label="Файл", required=False)


# ============= 1. рассылка по email ==================
class AuraEmailForm(forms.Form):
    country = forms.ModelChoiceField(queryset=Country.objects.all(), label="Страна", required=True)
    subject = forms.CharField(max_length=150, label="Тема письма", widget=forms.TextInput(attrs={'placeholder': 'Тема'}))
    message = forms.CharField(widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Введите текст письма...'}), label="Сообщение", required=True)


# ============= 2. рассылка по телефону (sms/whatsapp) ==================
class AuraPhoneForm(forms.Form):
    country = forms.ModelChoiceField(queryset=Country.objects.all(), label="Страна", required=True)
    text = forms.CharField(widget=forms.Textarea(attrs={'rows': 2, 'placeholder': 'Введите текст сообщения...'}), label="Сообщение", required=True)
    sender_name = forms.CharField(max_length=50, label="Имя отправителя", required=False, help_text="Опционально: будет отображаться как имя в SMS/WhatsApp", widget=forms.TextInput(attrs={"placeholder": "Введите имя отправителя..."}))
