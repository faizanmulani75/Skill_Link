from django.urls import path
from .views import index, submit_platform_review

urlpatterns = [
    path('', index, name='index'),
    path('submit_review/', submit_platform_review, name='submit_platform_review'),
]
