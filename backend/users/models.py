"""Модели пользователей."""

from django.db import models  # type:ignore
from django.contrib.auth.models import AbstractUser  # type:ignore
from django.core.validators import MaxLengthValidator  # type:ignore
from django.conf import settings  # type: ignore

from .validators import (validate_username, validate_email,
                         MaxLengthPasswordValidator)
from .constants import NAME_MAX_LENGTH, EMAIL_MAX_LENGTH, MAX_PASSWORD_LENGTH


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
        through='Subscription',
    )
    avatar = models.ImageField(
        verbose_name='Аватар',
        upload_to='users/',
        default=settings.DEFAULT_AVATAR,
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
        'recipes.Recipe',
        related_name='favorites',
        verbose_name='Избранное',
        blank=True,
        through='Favorite',
    )
    shopping_cart = models.ManyToManyField(
        'recipes.Recipe',
        related_name='shopping_cart',
        verbose_name='Список покупок',
        blank=True,
        through='ShoppingCart',
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


class Favorite(models.Model):
    """Модель избранного."""

    user = models.ForeignKey(
        UserWithSubscriptions,
        on_delete=models.CASCADE,
        related_name='user_favorite',
        verbose_name='Пользователь',
    )
    recipe = models.ForeignKey(
        'recipes.Recipe',
        on_delete=models.CASCADE,
        related_name='recipe_favorite',
        verbose_name='Рецепт',
    )

    class Meta:
        """Настройки модели."""

        constraints = (
            models.UniqueConstraint(fields=('user', 'recipe'),
                                    name='unique_favorite'),
        )
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранное'

    def __str__(self):
        """Строковое представление."""
        return f'Избранное: {self.user.username} - {self.recipe.name}'


class ShoppingCart(models.Model):
    """Модель списка покупок."""

    user = models.ForeignKey(
        UserWithSubscriptions,
        on_delete=models.CASCADE,
        related_name='user_shopping_cart',
        verbose_name='Пользователь',
    )
    recipe = models.ForeignKey(
        'recipes.Recipe',
        on_delete=models.CASCADE,
        related_name='recipe_shopping_cart',
        verbose_name='Рецепт',
    )

    class Meta:
        """Настройки модели."""

        constraints = (
            models.UniqueConstraint(fields=('user', 'recipe'),
                                    name='unique_shopping'),
        )
        verbose_name = 'Покупка'
        verbose_name_plural = 'Список покупок'

    def __str__(self):
        """Строковое представление."""
        return f'Список покупок: {self.user.username} - {self.recipe.name}'


class Subscription(models.Model):
    """Модель подписок."""

    user = models.ForeignKey(
        UserWithSubscriptions,
        on_delete=models.CASCADE,
        related_name='follower',
        verbose_name='Подписчик',
    )
    author = models.ForeignKey(
        UserWithSubscriptions,
        on_delete=models.CASCADE,
        related_name='following',
        verbose_name='Автор',
    )

    class Meta:
        """Настройки модели."""

        constraints = (
            models.UniqueConstraint(fields=('user', 'author'),
                                    name='unique_subscription'),
        )
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'

    def __str__(self):
        """Строковое представление."""
        return f'Подписка: {self.user.username} - {self.author.username}'
