"""Модели."""

import re

from django.db import models  # type: ignore
from django.contrib.auth import get_user_model  # type: ignore
from django.core.validators import (MaxValueValidator,  # type: ignore
                                    MaxLengthValidator,
                                    MinValueValidator)
from django.core.exceptions import ValidationError  # type: ignore

from .constants import (MAX_NAME_LENGTH, MAX_SLUG_LENGTH, MAX_UNIT_LENGTH,
                        MAX_INGREDIENT_AMOUNT, MIN_INGREDIENT_AMOUNT,
                        MAX_COOKING_TIME, MIN_COOKING_TIME)

User = get_user_model()


def validate_slug(slug):
    """Проверка слага."""
    if len(slug) > MAX_SLUG_LENGTH:
        raise ValidationError(
            f'Длина слага не должна превышать '
            f'{MAX_SLUG_LENGTH} символов.'
        )
    if not re.fullmatch(r'^[-a-zA-Z0-9_]+$', slug):
        raise ValidationError(
            'Слаг содержит недопустимые символы.'
        )
    return slug


class BaseNameModel(models.Model):
    """Базовая модель с именем."""

    name = models.CharField(max_length=MAX_NAME_LENGTH,
                            validators=(MaxLengthValidator,),
                            verbose_name='Название',
                            unique=True)

    class Meta:
        abstract = True
        ordering = ('name',)

    def __str__(self):
        return self.name


class Ingredient(BaseNameModel):
    """Модель ингредиента."""

    units = models.CharField(max_length=MAX_UNIT_LENGTH,
                             validators=(MaxLengthValidator,),
                             verbose_name='Единицы измерения')


class Tag(BaseNameModel):
    """Модель тега."""

    slug = models.SlugField(unique=True, max_length=MAX_SLUG_LENGTH,
                            validators=(MaxLengthValidator,
                                        validate_slug),
                            verbose_name='Слаг',
                            unique=True)


class Recipe(BaseNameModel):
    """Модель рецепта."""

    author = models.ForeignKey(User, on_delete=models.CASCADE,
                               related_name='recipes',
                               verbose_name='Автор')
    image = models.ImageField(
        upload_to='recipes/images/',
    )
    text = models.TextField(verbose_name='Текст рецепта')
    ingredients = models.ManyToManyField(Ingredient, null=True,
                                         through='RecipeIngredient',
                                         verbose_name='Ингредиенты')
    tags = models.ManyToManyField(Tag, related_name='recipes',
                                  verbose_name='Теги')
    cooking_time = models.PositiveSmallIntegerField(
        validators=(
                    MaxValueValidator(MAX_COOKING_TIME),
                    MinValueValidator(MIN_COOKING_TIME)),
        verbose_name='Время приготовления в минутах',
    )
    pub_date = models.DateTimeField(verbose_name='Дата публикации',
                                    auto_now_add=True,
                                    db_index=True)

    class Meta:
        ordering = ('-pub_date',)


class RecipeIngredient(models.Model):
    """Промежуточная таблица с указанием количества ингредиентов."""

    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE,
                               related_name='ingredients')
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE,
                                   related_name='recipes')
    amount = models.PositiveSmallIntegerField(validators=(
        MaxValueValidator(MAX_INGREDIENT_AMOUNT),
        MinValueValidator(MIN_INGREDIENT_AMOUNT)),
        verbose_name='Количество')

    def __str__(self):
        return f'{self.ingredient.name}: {self.amount} {self.ingredient.units}'
