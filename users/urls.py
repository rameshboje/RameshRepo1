from django.urls import path
from .views import OneTimePasswordChange, change_one_time_password, LoginView,generate_aside_menu

urlpatterns = [
    path('change-password-one-time', change_one_time_password, name='change_password_one_time'),
    path('menu', generate_aside_menu, name='menu'),
]