"""Разрешения."""

from rest_framework.permissions import IsAuthenticated  # type: ignore
from rest_framework.exceptions import MethodNotAllowed  # type: ignore


class AuthorOnly(IsAuthenticated):
    """Доступно только автору."""

    def has_object_permission(self, request, view, recipe):
        """Проверка авторства."""
        return recipe.author == request.user


class ForbiddenPermission(IsAuthenticated):
    """Доступ запрещен."""

    def has_permission(self, request, view):
        """Запрет доступа."""
        raise MethodNotAllowed(request.method)
