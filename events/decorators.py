from __future__ import annotations

from functools import wraps
from typing import Callable, ParamSpec, TypeVar

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect

from accounts.models import User

P = ParamSpec("P")
R = TypeVar("R")


def role_required(*roles: str) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Restrict a view to one or more ``User.role`` values."""

    def decorator(view_func: Callable[P, R]) -> Callable[P, R]:
        @wraps(view_func)
        @login_required
        def _wrapped(request: HttpRequest, *args: P.args, **kwargs: P.kwargs) -> HttpResponse | R:
            user_role = getattr(request.user, "role", None)
            if user_role not in roles:
                return redirect("events:dashboard")
            return view_func(request, *args, **kwargs)

        return _wrapped  # type: ignore[return-value]

    return decorator


ADMIN = User.Role.ADMIN
FACULTY = User.Role.FACULTY
COORD = User.Role.STUDENT_COORDINATOR
VIEWER = User.Role.VIEWER

CREATOR_ROLES = (ADMIN, FACULTY, COORD)
STAFF_ROLES = (ADMIN, FACULTY, COORD)

# Department approval status: visible to admins, faculty coordinators, and student coordinators.
# Decisions remain admin-only in views.
APPROVAL_QUEUE_ROLES = (ADMIN, FACULTY, COORD)
