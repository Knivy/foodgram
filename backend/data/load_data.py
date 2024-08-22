"""Загрузка данных в базу."""

import json

from recipes.models import Ingredient, Tag  # type: ignore

with open('ingredients.json', 'r', encoding='utf-8') as file:
    ingredients = json.load(file)
    for ingredient in ingredients:
        Ingredient.objects.get_or_create(
            name=ingredient['name'],
            measurement_unit=ingredient['measurement_unit']
        )

with open('tags.json', 'r', encoding='utf-8') as file:
    tags = json.load(file)
    for tag in tags:
        Tag.objects.get_or_create(
            name=tag['name'],
            slug=tag['slug']
        )
