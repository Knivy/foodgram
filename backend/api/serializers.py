"""Сериализаторы."""

import base64

from rest_framework import serializers  # type: ignore
from django.core.files.base import ContentFile  # type: ignore
from django.core.exceptions import ValidationError  # type: ignore
from django.contrib.auth import get_user_model  # type: ignore

from recipes.models import Tag, Recipe, Ingredient, RecipeIngredient

User = get_user_model()


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


class RecipeWriteSerializer(serializers.ModelSerializer):
    """Сериализатор рецептов на запись."""

    image = Base64ImageField()
    tags = TagSerializer(many=True)
    ingredients = IngredientSerializer(many=True)

    class Meta:
        """Настройки сериализатора."""

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
        """Обновление рецепта."""
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
            raise ValidationError('Нет данных запроса.')
        user = request.user
        if user.is_authenticated:
            username = self.instance.username
            return user.subscriptions.filter(username=username).exists()
        return False


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


class PasswordSerializer(serializers.Serializer):
    """Сериализатор пароля."""

    new_password = serializers.CharField()
    current_password = serializers.CharField()

    def validate(self, attrs):
        """Валидация пароля."""
        user = self.context.get('request').user
        if not user.check_password(attrs['current_password']):
            raise ValidationError('Неверный пароль.')
        return attrs

    def save(self):
        """Смена пароля."""
        user = self.context.get('request').user
        user.set_password(self.validated_data['new_password'])
        user.save()


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
        recipe = self.instance
        if not user.favorites.filter(recipe=recipe).exists():
            user.favorites.create(recipe=recipe)
        return recipe


class SubscriptionSerializer(serializers.ModelSerializer):
    """Сериализатор подписок."""

    recipes = serializers.SerializerMethodField()
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
        view = self.context.get('view')
        if not view:
            raise serializers.ValidationError('Нет view.')
        recipes = user.recipes.all()
        recipes_limit = view.kwargs.get('recipes_limit')
        if recipes_limit:
            recipes = recipes[:recipes_limit]
        return RecipeReadSerializer(recipes, many=True).data

    def get_is_subscribed(self, data):
        """Поле, подписан ли текущий пользователь на этого пользователя."""
        request = self.context.get('request')
        if not request:
            raise ValidationError('Нет данных запроса.')
        user = request.user
        if user.is_authenticated:
            username = self.instance.username
            return user.subscriptions.filter(username=username).exists()
        return False

    def get_recipes_count(self, user):
        """Получение количества рецептов пользователя."""
        view = self.context.get('view')
        if not view:
            raise serializers.ValidationError('Нет view.')
        recipes = user.recipes.all()
        return recipes.count()

    def create(self, validated_data):
        """Создание подписки."""
        return User.subscriptions.create(**validated_data)


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
