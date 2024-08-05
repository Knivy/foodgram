"""Сериализаторы."""

import base64

from rest_framework import serializers  # type: ignore
from django.core.files.base import ContentFile  # type: ignore
from django.core.exceptions import ValidationError  # type: ignore

from recipes.models import Tag, Recipe, Ingredient, RecipeIngredient


class TagSerializer(serializers.ModelSerializer):
    """Сериализатор тегов."""

    class Meta:
        model = Tag
        fields = ('id',
                  'name',
                  'slug')


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]

            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)

        return super().to_internal_value(data)


class RecipeWriteSerializer(serializers.ModelSerializer):
    """Сериализатор рецептов на запись."""

    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = ('ingredients',
                  'tags',
                  'image',
                  'name',
                  'text',
                  'cooking_time')

    def create(self, validated_data):
        """Создание рецепта."""
        ingredients = validated_data.pop('ingredients')
        recipe = Recipe.objects.create(**validated_data)
        for ingredient in ingredients:
            amount = ingredient.pop('amount')
            ingredient_object, status = Ingredient.objects.get_or_create(
                **ingredient)
            RecipeIngredient.objects.create(
                ingredient=ingredient_object[0],
                amount=amount,
                recipe=recipe,
            )
        return recipe

    def update(self, instance, validated_data):
        instance.name = validated_data.get('name', instance.name)
        instance.image = validated_data.get('image', instance.image)
        instance.cooking_time = validated_data.get(
            'cooking_time', instance.bcooking_time
        )
        instance.text = validated_data.get('text', instance.text)

        ingredients_data = validated_data.pop('ingredients')
        ingredients_dict = {}
        for ingredient in ingredients_data:
            amount = ingredient.pop('amount')
            current_ingredient, status = Ingredient.objects.get_or_create(
                **ingredient
            )
            RecipeIngredient.objects.get_or_create(
                ingredient=current_ingredient[0],
                recipe=instance,
            )
            if current_ingredient in ingredients_dict:
                raise ValidationError('Ингредиенты не должны повторяться.')
            ingredients_dict[current_ingredient] = amount
        recipe_ingredients = instance.ingredients.all()    
        for recipe_ingredient in recipe_ingredients:
            if recipe_ingredient in ingredients_dict:
                recipe_ingredient.amount = ingredients_dict[recipe_ingredient]
                recipe_ingredient.save()
        for ingredient, amount in ingredients_dict.items():
            if ingredient not in recipe_ingredients:
                RecipeIngredient.objects.create(
                    ingredient=ingredient[0],
                    amount=amount,
                    recipe=instance,
                )
        instance.save()
        return instance


class RecipeReadSerializer(serializers.ModelSerializer):
    """Сериализатор рецептов на чтение."""

    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = ('id',
                  'tags',
                  'author',
                  'ingredients',
                  'is_favorited',
                  'is_in_shopping_cart',
                  'name',
                  'image',
                  'text',
                  'cooking_time',
                  )
        