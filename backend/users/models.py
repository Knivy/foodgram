"""Модели пользователей."""

from django.db import models  # type:ignore
from django.contrib.auth.models import AbstractUser  # type:ignore
from django.core.validators import MaxLengthValidator  # type:ignore

from .validators import (validate_username, validate_email,
                         MaxLengthPasswordValidator)
from .constants import NAME_MAX_LENGTH, EMAIL_MAX_LENGTH, MAX_PASSWORD_LENGTH
from recipes.models import Recipe


class Role(models.TextChoices):
    """Роли пользователя."""

    USER = 'user', 'Пользователь'
    ADMIN = 'admin', 'Администратор'


def get_role_max_length():
    """Длина поля роли."""
    return max(len(role[0]) for role in Role.choices)


class UserWithSubscriptions(AbstractUser):
    """Модель пользователя с подписками."""

    username = models.CharField(
        verbose_name='Логин',
        max_length=NAME_MAX_LENGTH,
        validators=(MaxLengthValidator,
                    validate_username),
        unique=True,
    )
    email = models.EmailField(
        verbose_name='Емайл',
        max_length=EMAIL_MAX_LENGTH,
        validators=(MaxLengthValidator,
                    validate_email),
        unique=True,
    )
    first_name = models.CharField(
        verbose_name='Имя пользователя',
        max_length=NAME_MAX_LENGTH,
        validators=(MaxLengthValidator,),
    )
    last_name = models.CharField(
        verbose_name='Фамилия',
        max_length=NAME_MAX_LENGTH,
        validators=(MaxLengthValidator,),
    )
    password = models.CharField(
        max_length=MAX_PASSWORD_LENGTH,
        validators=(MaxLengthValidator,
                    MaxLengthPasswordValidator),
        verbose_name='Пароль',
    )
    subscriptions = models.ManyToManyField(
        'self',
        related_name='subscriptions',
        verbose_name='Подписки',
        blank=True,
    )
    avatar = models.ImageField(
        verbose_name='Аватар',
        upload_to='users/',
        default='users/default.png',
        blank=True,
    )
    role = models.CharField(
        verbose_name='Роль',
        choices=Role.choices,
        max_length=get_role_max_length(),
        validators=(MaxLengthValidator,),
        default=Role.USER,
    )
    favorites = models.ManyToManyField(
        Recipe,
        related_name='favourites',
        verbose_name='Избранное',
        blank=True,
    )
    shopping_cart = models.ManyToManyField(
        Recipe,
        related_name='shopping_cart',
        verbose_name='Список покупок',
        blank=True,
    )

    class Meta:
        """Настройки."""

        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ('username',)

    def __str__(self):
        """Строковое представление."""
        return self.username

    @property
    def is_superuser_or_admin(self):
        """Является ли пользователь суперпользователем или администратором."""
        self.refresh_from_db()
        return self.is_superuser or self.role == Role.ADMIN
