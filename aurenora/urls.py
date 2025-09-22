from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from . import views

urlpatterns = [
    path('lending/<str:username>/', views.LandingPageView.as_view(), name='lending_page'),
    path('save_profile_data/', views.save_profile_data, name='save_profile_data'),
    path('api/send-telegram/', views.SendTelegramMessageView.as_view(), name='send-telegram'),
    path('api/send-email/', views.SendEmailMessageView.as_view(), name='send-email'),
    path('api/send-sms/', views.SendSMSMessageView.as_view(), name='send-sms'),
]

