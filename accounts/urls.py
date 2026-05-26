from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.DepartmentLoginView.as_view(), name="login"),
    path("logout/", views.DepartmentLogoutView.as_view(), name="logout"),
]
