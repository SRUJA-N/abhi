from __future__ import annotations

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Department user with RBAC-aligned roles (3NF: role is atomic)."""

    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Administrator"
        FACULTY = "FACULTY", "Faculty"
        STUDENT_COORDINATOR = "STUDENT_COORDINATOR", "Student Coordinator"
        VIEWER = "VIEWER", "Viewer"

    role = models.CharField(max_length=32, choices=Role.choices, default=Role.VIEWER)

    class Meta:
        db_table = "cse_icb_users"

    def can_create_events(self) -> bool:
        return self.role in {
            User.Role.FACULTY,
            User.Role.STUDENT_COORDINATOR,
            User.Role.ADMIN,
        }

    def can_moderate_events(self) -> bool:
        return self.role == User.Role.ADMIN
