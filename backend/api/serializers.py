"""Сериализаторы."""

import base64

from rest_framework import serializers  # type: ignore
from django.core.files.base import ContentFile  # type: ignore
from django.contrib.auth import get_user_model  # type: ignore
from django.shortcuts import get_object_or_404  # type: ignore
from django.db.models import Case, When, BooleanField, Value  # type: ignore

from recipes.models import Tag, Recipe, Ingredient, RecipeIngredient
from users.models import Favorite, ShoppingCart

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

    def to_internal_value(self, image_data):
        """Преобразование в картинку."""
        if isinstance(image_data, str) and image_data.startswith('data:image'):
            format, imgstr = image_data.split(';base64,')
            ext = format.split('/')[-1]

            image_data = ContentFile(base64.b64decode(imgstr),
                                     name=f'temp.{ext}')

        return super().to_internal_value(image_data)


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор ингредиентов в списке ингредиентов."""

    class Meta:
        """Настройки сериализатора."""

        model = Ingredient
        fields = '__all__'


class IngredientWriteSerializer(serializers.Serializer):
    """Сериализатор ингредиентов на запись."""

    id = serializers.IntegerField(min_value=1)
    amount = serializers.IntegerField(min_value=1)


class IngredientInRecipeReadSerializer(serializers.ModelSerializer):
    """Сериализатор ингредиентов при чтении рецепта."""

    amount = serializers.SerializerMethodField()

    class Meta:
        """Настройки сериализатора."""

        model = Ingredient
        fields = ('id',
                  'name',
                  'measurement_unit',
                  'amount')

    def get_amount(self, ingredient):
        """Поле, количество ингредиента."""
        request = self.context.get('request')
        if not request:
            raise serializers.ValidationError('15. Нет данных запроса')
        recipe_id = self.context.get('recipe_id')
        try:
            recipe_ingredient = RecipeIngredient.objects.get(
                recipe__id=recipe_id,
                ingredient=ingredient,
            )
            return recipe_ingredient.amount
        except RecipeIngredient.DoesNotExist:
            raise serializers.ValidationError(
                f'Не найден ингредиент с id {recipe_id}')


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

    def get_is_subscribed(self, user_data):
        """Поле, подписан ли текущий пользователь на этого пользователя."""
        request = self.context.get('request')
        if not request:
            raise serializers.ValidationError('1. Нет данных запроса')
        user = request.user
        if user.is_authenticated:
            username = user_data.username
            return user.subscriptions.filter(username=username).exists()
        return False


class RecipeReadSerializer(serializers.ModelSerializer):
    """Сериализатор рецептов на чтение."""

    tags = TagSerializer(many=True)
    ingredients = serializers.SerializerMethodField()
    author = UserReadSerializer()
    is_favorited = serializers.BooleanField()
    is_in_shopping_cart = serializers.BooleanField()

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

    def get_ingredients(self, recipe):
        """Поле, ингредиенты рецепта."""
        return IngredientInRecipeReadSerializer(
            recipe.ingredients.all(),
            many=True,
            context={'recipe_id': recipe.id,
                     'request': self.context.get('request')}).data


class RecipeWriteSerializer(serializers.ModelSerializer):
    """Сериализатор рецептов на запись."""

    image = Base64ImageField()
    tags = serializers.ListField(child=serializers.IntegerField(
        min_value=1),
        allow_empty=False)
    ingredients = IngredientWriteSerializer(many=True,
                                            allow_empty=False)
    extra_kwargs = {
        'validate_tags': {
            'create': True,
            'update': True,
        },
        'validate_ingredients': {
            'create': True,
            'update': True,
        },
    }

    class Meta:
        """Настройки сериализатора."""

        model = Recipe
        fields = ('ingredients',
                  'tags',
                  'image',
                  'name',
                  'text',
                  'cooking_time')

    def validate(self, data):
        request = self.context.get('request')
        if not request:
            raise serializers.ValidationError('4. Нет данных запроса.')
        return data

    def validate_tags(self, tags):
        """Валидация тегов."""
        if not tags:
            raise serializers.ValidationError(
                'Не указаны теги.')
        len_set_tags = len(set(tags))
        if len(tags) != len_set_tags:
            raise serializers.ValidationError(
                'Теги не должны повторяться.')
        tag_objects = Tag.objects.filter(id__in=tags).order_by()
        if not tag_objects.exists() or tag_objects.count() != len_set_tags:
            raise serializers.ValidationError(
                'Не все указанные теги существуют.')
        return tags

    def validate_ingredients(self, ingredients):
        """Валидация ингредиентов."""
        if not ingredients:
            raise serializers.ValidationError(
                'Не указаны ингредиенты.')
        ingredient_ids = [ingredient.get('id') for ingredient in ingredients]
        if len(ingredients) != len(set(ingredient_ids)):
            raise serializers.ValidationError(
                'Ингредиенты не должны повторяться.')
        ingredient_objects = Ingredient.objects.filter(
            id__in=ingredient_ids).order_by()
        if (not ingredient_objects.exists()
           or len(ingredients) != ingredient_objects.count()):
            raise serializers.ValidationError(
                'Не все указанные ингредиенты существуют.')
        # i = 0
        # for ingredient_object in ingredient_objects:
        #     ingredient = ingredients[i]
        #     ingredient['object'] = ingredient_object
        #     i += 1
        return ingredients

    def create_recipe_ingredients(self, recipe, ingredients):
        """Создание ингредиентов рецепта."""
        try:
            RecipeIngredient.objects.bulk_create([
                RecipeIngredient(
                    ingredient__id=ingredient.get('id'),
                    amount=ingredient.get('amount'),
                    recipe=recipe,
                ) for ingredient in ingredients
            ])
        except Exception as err:
            recipe.text = 'Ошибка при создании ингредиентов'
            recipe.save()
            raise serializers.ValidationError(
                f'Ошибка при создании ингредиентов: {err}')

    def convert_to_short_link(self, recipe_id):
        """Конвертация в короткую ссылку."""
        number = []
        while recipe_id:
            number.append(chr(97 + recipe_id % 23))
            recipe_id //= 23
        return ''.join((str(digit) for digit in number))

    def create(self, validated_data):
        """Создание рецепта."""
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        recipe = Recipe.objects.create(
            author=self.context.get('request').user,
            **validated_data)
        recipe.short_url = self.convert_to_short_link(recipe.id)
        recipe.save()
        recipe.tags.clear()
        recipe.tags.set(tags)
        self.create_recipe_ingredients(recipe, ingredients)
        recipe.save()
        return recipe

    def update(self, instance, validated_data):
        """Обновление рецепта."""
        # instance.name = validated_data.get('name', instance.name)
        # instance.cooking_time = validated_data.get(
        #     'cooking_time', instance.cooking_time
        # )
        # instance.text = validated_data.get('text', instance.text)
        # instance.image = validated_data.get('image', instance.image)
        # tags = validated_data.get('tags')
        # #tags = self.validate_tags(tags)
        # ingredients = validated_data.get('ingredients')
        # ingredients = self.validate_ingredients(ingredients)
        tags = validated_data.pop('tags')
        ingredients = validated_data.pop('ingredients')
        instance = super().update(instance, validated_data)
        instance.tags.clear()
        instance.tags.set(tags)
        RecipeIngredient.objects.filter(recipe=instance).delete()
        self.create_recipe_ingredients(instance, ingredients)
        instance.save()
        return instance

    def to_representation(self, instance):
        """Представление рецепта."""
        request = self.context.get('request')
        if not request:
            raise serializers.ValidationError('13. Нет данных запроса.')
        if not request.user.is_authenticated:
            instance = Recipe.objects.filter(id=instance.id).annotate(
                is_favorited=Value(False),
                is_in_shopping_cart=Value(False),
            ).first()
        else:
            instance = Recipe.objects.filter(id=instance.id).annotate(
                is_favorited=Case(
                    When(favorites__in=(request.user,), then=True),
                    default=False,
                    output_field=BooleanField()
                ),
                is_in_shopping_cart=Case(
                    When(shopping_cart__in=(request.user,), then=True),
                    default=False,
                    output_field=BooleanField()
                ),
            ).first()
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
        if not user.check_password(attrs.get('current_password')):
            raise serializers.ValidationError(
                {'current_password': ['Неверный пароль.']})
        return attrs


class FavoriteSerializer(serializers.ModelSerializer):
    """Сериализатор для избранного и списка покупок для чтения."""

    image = Base64ImageField()

    class Meta:
        """Настройки сериализатора."""

        model = Recipe
        fields = ('id',
                  'name',
                  'image',
                  'cooking_time')


class FavoriteCreateSerializer(serializers.Serializer):
    """Сериализатор добавления в избранное."""

    id = serializers.IntegerField(min_value=1)

    def get_user(self):
        """Получение пользователя из запроса."""
        request = self.context.get('request')
        if not request:
            raise serializers.ValidationError('10. Нет данных запроса.')
        user = request.user
        if not user.is_authenticated:
            raise serializers.ValidationError(
                'Пользователь не аутентифицирован.')
        return request.user

    def validate(self, data_to_validate):
        """Валидация добавления в избранное."""
        user = self.get_user()
        recipe_id = data_to_validate.get('id')
        if not recipe_id:
            raise serializers.ValidationError('Нет id рецепта.')
        if Favorite.objects.filter(recipe__id=recipe_id,
                                   user=user).exists():
            raise serializers.ValidationError(
                'Рецепт уже добавлен в избранное.')
        recipe = get_object_or_404(Recipe, id=recipe_id)
        data_to_validate['user'] = user
        data_to_validate['recipe'] = recipe
        return data_to_validate

    def save(self):
        """Добавление в избранное."""
        # return Favorite.objects.create(
        #     user=self.validated_data.get('user'),
        #     recipe=self.validated_data.get('recipe'))
        return self.validated_data.get('user').favorites.add(
            self.validated_data.get('recipe'))

    def to_representation(self, instance):
        return FavoriteSerializer(instance,
                                  context=self.context).data


class SubscriptionSerializer(UserReadSerializer):
    """Сериализатор подписок."""

    recipes = serializers.SerializerMethodField()
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

    def check_recipes_limit(self, recipes_limit):
        """Проверка лимита рецептов."""
        if not recipes_limit:
            return recipes_limit
        try:
            recipes_limit = int(recipes_limit)
        except ValueError as err:
            raise serializers.ValidationError(
                'Лимит рецептов должен быть целым числом.') from err
        if recipes_limit < 1:
            raise serializers.ValidationError(
                'Лимит рецептов должен быть больше 0.')
        return recipes_limit

    def get_recipes(self, user):
        """Получение рецептов пользователя."""
        request = self.context.get('request')
        if not request:
            raise serializers.ValidationError('6. Нет данных запроса.')
        recipes = user.recipes.all()
        recipes_limit = request.query_params.get('recipes_limit')
        if recipes_limit:
            recipes_limit = self.check_recipes_limit(recipes_limit)
            recipes = recipes[:recipes_limit]
        if not request.user.is_authenticated:
            recipes = recipes.annotate(
                is_favorited=Value(False),
                is_in_shopping_cart=Value(False),
            )
        else:
            recipes = recipes.annotate(
                is_favorited=Case(
                    When(favorites__in=(request.user,), then=True),
                    default=False,
                    output_field=BooleanField()
                ),
                is_in_shopping_cart=Case(
                    When(shopping_cart__in=(request.user,), then=True),
                    default=False,
                    output_field=BooleanField()
                ),
            )
        return RecipeReadSerializer(recipes,
                                    many=True,
                                    context=self.context).data

    def get_recipes_count(self, user):
        """Получение количества рецептов пользователя."""
        return user.recipes.count()


class SubscriptionCreateSerializer(serializers.Serializer):
    """Сериализатор создания подписки."""

    id = serializers.IntegerField(min_value=1)

    def validate(self, data_to_validate):
        """Валидация подписки."""
        request = self.context.get('request')
        if not request:
            raise serializers.ValidationError('8. Нет данных запроса.')
        user = request.user
        if not user.is_authenticated:
            raise serializers.ValidationError(
                'Пользователь не аутентифицирован.')
        subscription_user_id = data_to_validate.get('id')
        if not subscription_user_id:
            raise serializers.ValidationError('Нет id пользователя.')
        if user.id == subscription_user_id:
            raise serializers.ValidationError(
                'Нельзя подписаться на самого себя.')
        if user.subscriptions.filter(
                id=subscription_user_id).exists():
            raise serializers.ValidationError(
                'Пользователь уже подписан.')
        subscription_user = get_object_or_404(User, id=subscription_user_id)
        data_to_validate['user'] = user
        data_to_validate['subscription_user'] = subscription_user
        return data_to_validate

    def save(self):
        """Создание подписки."""
        subscription_user = self.validated_data.get('subscription_user')
        user = self.validated_data.get('user')
        # return Subscription.objects.create(
        #     author=subscription_user,
        #     user=user)
        return user.subscriptions.add(subscription_user)

    def to_representation(self, instance):
        return SubscriptionSerializer(instance,
                                      context=self.context).data


class ShoppingCreateSerializer(FavoriteCreateSerializer):
    """Сериализатор добавления в список покупок."""

    def validate(self, data_to_validate):
        """Валидация добавления в список покупок."""
        user = self.get_user()
        recipe_id = data_to_validate.get('id')
        if not recipe_id:
            raise serializers.ValidationError('Нет id рецепта.')
        if ShoppingCart.objects.filter(
                recipe__id=recipe_id,
                user=user).exists():
            raise serializers.ValidationError(
                'Рецепт уже добавлен в список покупок.')
        recipe = get_object_or_404(Recipe, id=recipe_id)
        data_to_validate['user'] = user
        data_to_validate['recipe'] = recipe
        return data_to_validate

    def save(self):
        """Добавление рецепта в список покупок."""
        # return ShoppingCart.objects.create(
        #     user=self.validated_data.get('user'),
        #     recipe=self.validated_data.get('recipe'))
        return self.validated_data.get('user').shopping_cart.add(
            self.validated_data.get('recipe'))


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
        user.avatar = avatar
        user.save()
        return user
