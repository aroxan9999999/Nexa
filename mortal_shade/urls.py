from django.urls import path
from .views import SendMessageView

urlpatterns = [
    path('mK9z2s4X8-pulse-nV3t7Q/', SendMessageView.as_view(), name='send_message'),
]

