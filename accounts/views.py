from __future__ import annotations

from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy

from .forms import CyberLoginForm


class DepartmentLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = CyberLoginForm
    redirect_authenticated_user = True
    success_url = reverse_lazy("events:dashboard")


class DepartmentLogoutView(LogoutView):
    next_page = reverse_lazy("accounts:login")
