"""Модели пользователей."""

import re  # type:ignore

from django.db import models  # type:ignore
from django.contrib.auth.models import AbstractUser  # type:ignore
from django.core.exceptions import ValidationError  # type:ignore
from django.core.validators import MaxLengthValidator  # type:ignore
from django.forms import PasswordInput  # type:ignore

from .constants import NAME_MAX_LENGTH, EMAIL_MAX_LENGTH


class Role(models.TextChoices):
    """Роли пользователя."""

    USER = 'user', 'Пользователь'
    MODERATOR = 'moderator', 'Модератор'
    ADMIN = 'admin', 'Администратор'


def get_role_max_length():
    """Длина поля роли."""
    return max(len(role[0]) for role in Role.choices)


def validate_username(username):
    """Проверка логина."""
    if username.lower() == 'me':
        raise ValidationError(
            'Нельзя назвать логин "me".'
        )
    if len(username) > NAME_MAX_LENGTH:
        raise ValidationError(
            f'Длина логина не должна превышать '
            f'{NAME_MAX_LENGTH} символов.'
        )
    if not re.fullmatch(r'^[\w.@+-]+\z', username):
        raise ValidationError(
            'Логин содержит недопустимые символы.'
        )
    return username


def validate_email(email):
    """Проверка email."""
    if len(email) > EMAIL_MAX_LENGTH:
        raise ValidationError(
            'Email слишком длинный.'
        )
    return email


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
        widget=PasswordInput()
    )
    subscriptions = models.ManyToManyField(
        'self',
        related_name='subscriptions',
        verbose_name='Подписки',
        blank=True,
        null=True,
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

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ('username',)

    def __str__(self):
        return self.username

    @property
    def is_superuser_or_admin(self):
        return self.is_superuser or self.role == Role.ADMIN
