"""Загрузка данных в базу."""

import json
import os

from recipes.models import Ingredient, Tag  # type: ignore

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'foodgram_backend.settings')

with open('data/ingredients.json', 'r', encoding='utf-8') as file:
    ingredients = json.load(file)
    for ingredient in ingredients:
        Ingredient.objects.get_or_create(
            name=ingredient['name'],
            measurement_unit=ingredient['measurement_unit']
        )

with open('data/tags.json', 'r', encoding='utf-8') as file:
    tags = json.load(file)
    for tag in tags:
        Tag.objects.get_or_create(
            name=tag['name'],
            slug=tag['slug']
        )
