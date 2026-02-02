from django.urls import path
from .views import (
    dashboard, profile_view, profile_edit, login_page, register_page, logout_view,
    token_balance, spend_tokens, payment_success,add_tokens_view,edit_skill,delete_skill,add_skill,
    public_profile, acknowledge_level_up
    # verify_otp,resend_otp
)
urlpatterns = [
    # Auth
    path('login/', login_page, name='login'),
    path('register/', register_page, name='register'),
    path('logout/', logout_view, name='logout'),
    # path('verify-otp/', verify_otp, name='verify_otp'),
    # path('resend-otp/', resend_otp, name='resend_otp'),

    # Profile
    path('profile/', profile_view, name='profile'),
    path('profile/edit/', profile_edit, name='profile_edit'),
    path("edit-skill/<int:pk>/", edit_skill, name="edit_skill"),
    path("delete-skill/<int:pk>/", delete_skill, name="delete_skill"),
    path("add-skill/", add_skill, name="add_skill"),

    # user profile
    path('profile/<str:username>/', public_profile, name='public_profile'),

    # user profile
    path('profile/<str:username>/', public_profile, name='public_profile'),

    # Dashboard
    path('dashboard/', dashboard, name='dashboard'),

    # Tokens
    path("tokens/", token_balance, name="token_balance"),
    path('tokens/spend/', spend_tokens, name='spend_tokens'),
    path('token-add/', add_tokens_view, name='add_tokens'),

    # Payment success callback
    path('token-payment/success/', payment_success, name='payment_success'),

    # Level Up Acknowledgment
    path('acknowledge-level-up/', acknowledge_level_up, name='acknowledge_level_up'),

    # Level Up Acknowledgment
    path('acknowledge-level-up/', acknowledge_level_up, name='acknowledge_level_up'),
]
