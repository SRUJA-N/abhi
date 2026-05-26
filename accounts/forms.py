from django import forms
from django.contrib.auth.forms import AuthenticationForm


class CyberLoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={"class": "cyber-input", "placeholder": "Username"}))
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "cyber-input", "placeholder": "Password"})
    )
