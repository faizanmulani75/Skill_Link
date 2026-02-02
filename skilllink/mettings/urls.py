from django.urls import path
from .views import create_booking, booking_list, booking_update_status, schedule_meeting, booking_success,complete_meeting,schedule_meeting,start_meeting, booking_details, send_message, get_messages, submit_review, rate_booking, submit_report, user_reports

urlpatterns = [
    path('reports/', user_reports, name='user_reports'),
    path('create/<int:skill_id>/<int:provider_id>/', create_booking, name='create_booking'),
    path('', booking_list, name='booking_list'),
    path('<int:booking_id>/update/<str:action>/', booking_update_status, name='booking_update_status'),
    path('<int:booking_id>/schedule/', schedule_meeting, name='schedule_meeting'),
    path('success/', booking_success, name='booking_success'),
    path('<int:booking_id>/complete/', complete_meeting, name='complete_meeting'),
    path('booking/<int:booking_id>/', booking_details, name='booking_details'),
    path('<int:booking_id>/start/', start_meeting, name='start_meeting'),
    path('<int:booking_id>/send_message/', send_message, name='send_message'),
    path('<int:booking_id>/get_messages/', get_messages, name='get_messages'),
    path('<int:booking_id>/submit_review/', submit_review, name='submit_review'),
    path('<int:booking_id>/report/', submit_report, name='submit_report'),
    path('<int:booking_id>/rate/', rate_booking, name='rate_booking'),
]
