"""Сериализаторы."""

import base64
from collections import deque

from rest_framework import serializers  # type: ignore
from django.core.files.base import ContentFile  # type: ignore
from django.core.exceptions import ValidationError  # type: ignore
from django.contrib.auth import get_user_model  # type: ignore
from django.shortcuts import get_object_or_404  # type: ignore

from recipes.models import Tag, Recipe, Ingredient, RecipeIngredient

User = get_user_model()


# def convert_to_image(data):
#     """Преобразование в картинку."""
#     if isinstance(data, str) and data.startswith('data:image'):
#         format, imgstr = data.split(';base64,')
#         ext = format.split('/')[-1]
#         data = base64.b64decode(imgstr)
#         return data, ext
#     raise ValidationError('Неверный формат изображения.')


class TagSerializer(serializers.ModelSerializer):
    """Сериализатор тегов."""

    class Meta:
        """Настройки сериализатора."""

        model = Tag
        fields = ('id',
                  'name',
                  'slug')


class Base64ImageField(serializers.ImageField):
    """Поле для картинки."""

    def to_internal_value(self, data):
        """Преобразование в картинку."""
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]

            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)

        return super().to_internal_value(data)


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор ингредиентов."""

    class Meta:
        """Настройки сериализатора."""

        model = Ingredient
        fields = ('id',
                  'name',
                  'measurement_unit')


class IngredientWriteSerializer(serializers.Serializer):
    """Сериализатор ингредиентов на запись."""

    id = serializers.IntegerField(min_value=1)
    amount = serializers.IntegerField(min_value=1)


# class RecipeIngredientSerializer(serializers.ModelSerializer):
#     """Сериализатор ингредиентов в рецепте."""

#     id = serializers.SerializerMethodField()
#     name = serializers.SerializerMethodField()
#     measurement_unit = serializers.SerializerMethodField()

#     class Meta:
#         """Настройки сериализатора."""

#         model = RecipeIngredient
#         fields = ('id',
#                   'name',
#                   'measurement_unit',
#                   'amount')

#     def get_id(self, data):
#         """Поле, id ингредиента."""
#         return data.ingredient.id

#     def get_name(self, data):
#         """Поле, название ингредиента."""
#         return data.ingredient.name

#     def get_measurement_unit(self, data):
#         """Поле, единица измерения ингредиента."""
#         return data.ingredient.measurement_unit


class UserReadSerializer(serializers.ModelSerializer):
    """Сериализатор пользователя."""

    is_subscribed = serializers.SerializerMethodField()
    avatar = Base64ImageField()

    class Meta:
        """Настройки сериализатора."""

        model = User
        fields = ('email',
                  'id',
                  'username',
                  'first_name',
                  'last_name',
                  'is_subscribed',
                  'avatar')

    def get_is_subscribed(self, data):
        """Поле, подписан ли текущий пользователь на этого пользователя."""
        request = self.context.get('request')
        if not request:
            raise serializers.ValidationError('Нет данных запроса')
        user = request.user
        if user.is_authenticated:
            username = data.username
            return user.subscriptions.filter(username=username).exists()
        return False


class RecipeReadSerializer(serializers.ModelSerializer):
    """Сериализатор рецептов на чтение."""

    image = Base64ImageField()
    tags = TagSerializer(many=True)
    ingredients = IngredientSerializer(many=True)
    author = serializers.SerializerMethodField()
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        """Настройки сериализатора."""

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

    def get_is_favorited(self, data):
        """Поле, добавлен ли рецепт в избранное."""
        request = self.context.get('request')
        if not request:
            raise serializers.ValidationError('Нет данных запроса.')
        user = request.user
        if not user.is_authenticated:
            return False
        return (user.favorites.
                filter(id=data.id).exists())

    def get_author(self, data):
        """Поле, автор рецепта."""
        # if isinstance(self.instance, list):
        #     return [UserReadSerializer(recipe.author).data
        #             for recipe in self.instance]
        return UserReadSerializer(data.author,
                                  context=self.context).data

    def get_is_in_shopping_cart(self, data):
        """Поле, добавлен ли рецепт в список покупок."""
        request = self.context.get('request')
        if not request:
            raise serializers.ValidationError('Нет данных запроса.')
        user = request.user
        if not user.is_authenticated:
            return False
        return (user.shopping_cart.
                filter(id=data.id).exists())


class RecipeWriteSerializer(serializers.ModelSerializer):
    """Сериализатор рецептов на запись."""

    image = Base64ImageField()
    tags = serializers.ListField(child=serializers.IntegerField())
    ingredients = IngredientWriteSerializer(many=True)

    class Meta:
        """Настройки сериализатора."""

        model = Recipe
        fields = ('ingredients',
                  'tags',
                  'image',
                  'name',
                  'text',
                  'cooking_time')

    def convert_to_short_link(self, recipe_id):
        """
        Конвертация в короткую ссылку.

        Используется преобразование id из 10тичной системы в 23-ричную.
        """
        number = deque()
        while recipe_id:
            number.appendleft(recipe_id % 23)
            recipe_id //= 23
        number = ''.join(map(str, number))
        return f'{number}'

    def create(self, validated_data):
        """Создание рецепта."""
        request = self.context.get('request')
        if not request:
            raise serializers.ValidationError('Нет данных запроса.')
        ingredients = validated_data.pop('ingredients')
        if not ingredients:
            raise serializers.ValidationError(
                {'ingredients': ['Не указаны ингредиенты.']})
        tags = validated_data.pop('tags')
        if not tags:
            raise serializers.ValidationError(
                {'tags': ['Не указаны теги.']})
        image = validated_data.pop('image')
        recipe = Recipe.objects.create(
            author=request.user, **validated_data)
        recipe.short_url = self.convert_to_short_link(recipe.id)
        tags_set = set()
        for tag_id in tags:
            if tag_id in tags_set:
                raise serializers.ValidationError(
                    {'tags': ['Теги не должны повторяться.']})
            tags_set.add(tag_id)
            tag = get_object_or_404(Tag, id=tag_id)
            recipe.tags.add(tag)
        ingredients_set = set()
        for ingredient in ingredients:
            amount = ingredient.get('amount')
            if not amount:
                raise serializers.ValidationError(
                    {'amount': ['Не указано количество.']})
            ingredient_id = ingredient.get('id')
            if not ingredient_id:
                raise serializers.ValidationError(
                    {'ingredients': ['Не указан ингредиент.']})
            ingredient_object = get_object_or_404(
                Ingredient,
                id=ingredient_id)
            if ingredient_object.id in ingredients_set:
                to_delete = RecipeIngredient.objects.filter(
                    recipe=recipe)
                to_delete.delete()
                raise serializers.ValidationError(
                    {'ingredients': ['Ингредиенты не должны повторяться.']})
            ingredients_set.add(ingredient_object.id)
            RecipeIngredient.objects.create(
                ingredient=ingredient_object,
                amount=amount,
                recipe=recipe,
            )
        # data, ext = convert_to_image(image.data)
        # recipe.image.save(image_name, ContentFile(data, name=image_name))
        recipe.image = image
        recipe.save()
        return recipe

    def update(self, instance, validated_data):
        """Обновление рецепта."""
        instance.name = validated_data.get('name', instance.name)
        instance.cooking_time = validated_data.get(
            'cooking_time', instance.cooking_time
        )
        instance.text = validated_data.get('text', instance.text)
        instance.image = validated_data.get('image', instance.image)
        # if image:
        #     data, ext = convert_to_image(image)
        #     image_name = f'recipes/{instance.id}.{ext}'
        #     instance.image.save(image_name, ContentFile(data, name=image_name))
        ingredients_data = validated_data.get('ingredients')
        if not ingredients_data:
            raise serializers.ValidationError(
                {'ingredients': ['Не указаны ингредиенты.']})
        ingredients_dict = {}
        for ingredient in ingredients_data:
            amount = ingredient.get('amount')
            if not amount:
                raise serializers.ValidationError(
                    {'amount': ['Не указано количество.']})
            ingredient_id = ingredient.get('id')
            if not ingredient_id:
                raise serializers.ValidationError(
                    {'ingredients': ['Не указан ингредиент.']})
            current_ingredient = get_object_or_404(Ingredient,
                                                   id=ingredient_id)
            if current_ingredient.id in ingredients_dict:
                raise serializers.ValidationError(
                    {'ingredients': ['Ингредиенты не должны повторяться.']})
            ingredients_dict[current_ingredient.id] = amount
        recipe_ingredients = instance.ingredients.all()
        recipe_ingredients_ids = set()
        for recipe_ingredient in recipe_ingredients:
            if recipe_ingredient.id in ingredients_dict:
                recipe_ingredient.amount = (
                    ingredients_dict[recipe_ingredient.id])
                recipe_ingredient.save()
            recipe_ingredients_ids.add(recipe_ingredient.id)
        for ingredient_id, amount in ingredients_dict.items():
            if ingredient_id not in recipe_ingredients_ids:
                RecipeIngredient.objects.create(
                    ingredient=ingredient,
                    amount=amount,
                    recipe=instance,
                )
        tags = validated_data.get('tags')
        if not tags:
            raise serializers.ValidationError(
                {'tags': ['Не указаны теги.']})
        tags_set = set()
        for tag_id in tags:
            if tag_id in tags_set:
                raise serializers.ValidationError(
                    {'tags': ['Теги не должны повторяться.']})
            tags_set.add(tag_id)
            tag = get_object_or_404(Tag, id=tag_id)
            instance.tags.add(tag)
        instance.save()
        return instance

    def to_representation(self, instance):
        """Представление рецепта."""
        return RecipeReadSerializer(instance, context=self.context).data


class UserWriteSerializer(serializers.ModelSerializer):
    """Сериализатор пользователя."""

    class Meta:
        """Настройки сериализатора."""

        model = User
        fields = ('email',
                  'username',
                  'first_name',
                  'last_name',
                  'password')
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        """Создание пользователя."""
        password = validated_data.pop('password')
        user = User.objects.create(**validated_data)
        user.set_password(password)
        user.save()
        return user

    def to_representation(self, instance):
        return UserGetSerializer(instance).data


class UserGetSerializer(serializers.ModelSerializer):
    """Сериализатор пользователя при ответе на регистрацию."""

    class Meta:
        """Настройки сериализатора."""

        model = User
        fields = ('email',
                  'id',
                  'username',
                  'first_name',
                  'last_name')


class PasswordSerializer(serializers.Serializer):
    """Сериализатор пароля."""

    new_password = serializers.CharField()
    current_password = serializers.CharField()

    def validate(self, attrs):
        """Валидация пароля."""
        user = self.context.get('request').user
        if not user.check_password(attrs['current_password']):
            raise serializers.ValidationError(
                {'current_password': ['Неверный пароль.']})
        return attrs

    # def save(self):
    #     """Смена пароля."""
    #     user = self.context.get('request').user
    #     user.set_password(self.validated_data['new_password'])
    #     user.save()


class FavoriteSerializer(serializers.ModelSerializer):
    """Сериализатор для избранного."""

    image = Base64ImageField()

    class Meta:
        """Настройки сериализатора."""

        model = Recipe
        fields = ('id',
                  'name',
                  'image',
                  'cooking_time')
        read_only_fields = ('name',
                            'image',
                            'cooking_time')

    def save(self):
        """Добавление в избранное."""
        user = self.context.get('request').user
        recipe_id = self.validated_data.get('id')
        recipe = get_object_or_404(Recipe, id=recipe_id)
        if (not user.favorites or
           not user.favorites.filter(id=recipe_id).exists()):
            user.favorites.create(id=recipe_id)
        return recipe


class SubscriptionSerializer(serializers.ModelSerializer):
    """Сериализатор подписок."""

    recipes = serializers.SerializerMethodField()
    is_subscribed = serializers.SerializerMethodField()
    avatar = Base64ImageField()
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        """Настройки сериализатора."""

        model = User
        fields = ('email',
                  'id',
                  'username',
                  'first_name',
                  'last_name',
                  'is_subscribed',
                  'recipes',
                  'recipes_count',
                  'avatar')
        read_only_fields = (
            'email',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'recipes',
            'recipes_count',
            'avatar')

    def get_recipes(self, user):
        """Получение рецептов пользователя."""
        request = self.context.get('request')
        if not request:
            raise serializers.ValidationError('Нет данных запроса.')
        recipes = user.recipes.all()
        recipes_limit = request.GET.get('recipes_limit')
        if recipes_limit:
            recipes = recipes[:recipes_limit]
        return RecipeReadSerializer(recipes, many=True).data

    def get_is_subscribed(self, user):
        """Поле, подписан ли текущий пользователь на этого пользователя."""
        request = self.context.get('request')
        if not request:
            raise serializers.ValidationError('Нет данных запроса.')
        user = request.user
        if user.is_authenticated:
            username = user.username
            return user.subscriptions.filter(username=username).exists()
        return False

    def get_recipes_count(self, user):
        """Получение количества рецептов пользователя."""
        # view = self.context.get('view')
        # if not view:
        #     raise serializers.ValidationError('Нет view.')
        return user.recipes.count()


class SubscriptionCreateSerializer(serializers.Serializer):
    """Сериализатор создания подписки."""

    id = serializers.IntegerField(min_value=1)

    def save(self):
        """Создание подписки."""
        request = self.context.get('request')
        if not request:
            raise serializers.ValidationError('Нет данных запроса.')
        user = request.user
        if not user.is_authenticated:
            raise serializers.ValidationError(
                'Пользователь не аутентифицирован.')
        subscription_user_id = self.validated_data.get('id')
        if not subscription_user_id:
            raise serializers.ValidationError('Нет id пользователя.')
        if user.id == subscription_user_id:
            raise serializers.ValidationError(
                'Нельзя подписаться на самого себя.')
        if user.subscriptions.filter(id=subscription_user_id).exists():
            raise serializers.ValidationError(
                'Пользователь уже подписан.')
        subscription_user = get_object_or_404(User, id=subscription_user_id)
        query = request.GET.get('recipes_limit')
        if query:
            num_recipes = subscription_user.recipes.count()
            if int(query) < num_recipes:
                raise serializers.ValidationError(
                    'У того пользователя слишком много рецептов.')
        return user.subscriptions.add(subscription_user)

    def to_representation(self, instance):
        return SubscriptionSerializer(instance, context=self.context).data


class ShoppingSerializer(serializers.ModelSerializer):
    """Сериализатор рецептов в списке покупок."""

    image = Base64ImageField()

    class Meta:
        """Настройки сериализатора."""

        model = Recipe
        fields = ('id',
                  'name',
                  'image',
                  'cooking_time')
        read_only_fields = ('name',
                            'image',
                            'cooking_time')


class AvatarSerializer(serializers.ModelSerializer):
    """Сериализатор для аватара."""

    avatar = Base64ImageField()

    class Meta:
        """Настройки сериализатора."""

        model = User
        fields = ('avatar',)

    def partial_update(self, request, *args, **kwargs):
        """Обновление аватара."""
        kwargs['partial'] = True
        user = self.context.get('request').user
        avatar = request.data.get('avatar')
        if not avatar:
            raise serializers.ValidationError(
                {'avatar': ['Нет данных аватара.']})
        # data, ext = convert_to_image(avatar)
        # image_name = f'users/{user.id}.{ext}'
        # user.avatar.save(image_name, ContentFile(data, name=image_name))
        user.avatar = avatar
        user.save()
        return user
