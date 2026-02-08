from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'^ws/user/$', consumers.UserConsumer.as_asgi()),
    re_path(r'^ws/meet/(?P<booking_id>\d+)/$', consumers.MeetingConsumer.as_asgi()),
]
