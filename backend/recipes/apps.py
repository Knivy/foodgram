"""Настройки приложения."""

from django.apps import AppConfig  # type:ignore


class RecipesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'recipes'
    verbose_name = 'Рецепты'
