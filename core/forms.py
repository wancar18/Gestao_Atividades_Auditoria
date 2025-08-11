from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import CustomUser

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ('nome', 'cargo', 'username', 'password1', 'password2', 'is_active')

class CustomUserChangeForm(UserChangeForm):
    password = None  # Remove o campo password
    class Meta:
        model = CustomUser
        fields = ('nome', 'cargo', 'username', 'is_active')
