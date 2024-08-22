"""Контроллеры."""

from rest_framework.permissions import (AllowAny,  # type: ignore
                                        IsAuthenticated)
from rest_framework import filters, viewsets  # type: ignore
from django.contrib.auth import get_user_model  # type: ignore
from rest_framework.decorators import action  # type: ignore
from rest_framework.response import Response  # type: ignore
from django.shortcuts import get_object_or_404  # type: ignore
from django.conf import settings  # type: ignore
from rest_framework.views import APIView  # type: ignore
from django.http import FileResponse  # type: ignore
from django_filters.rest_framework import DjangoFilterBackend  # type: ignore

from recipes.models import Tag, Recipe, Ingredient
from .serializers import (TagSerializer, RecipeWriteSerializer,
                          RecipeReadSerializer, IngredientSerializer,
                          UserReadSerializer, UserWriteSerializer,
                          PasswordSerializer, FavoriteCreateSerializer,
                          SubscriptionSerializer, ShoppingCreateSerializer,
                          AvatarSerializer, SubscriptionCreateSerializer)
from .permissions import AuthorOnly, ForbiddenPermission
from .filters import RecipeFilter
from .drf_cache import CacheResponseMixin

import json


User = get_user_model()


class BaseReadOnlyViewset(CacheResponseMixin, viewsets.ReadOnlyModelViewSet):
    """Базовый вьюсет для чтения."""

    permission_classes = (AllowAny,)
    pagination_class = None


class TagViewSet(BaseReadOnlyViewset):
    """Вьюсет тегов."""

    queryset = Tag.objects.all()
    serializer_class = TagSerializer


class IngredientViewSet(BaseReadOnlyViewset):
    """Вьюсет ингредиентов."""

    serializer_class = IngredientSerializer

    def get_queryset(self):
        """Поиск по вхождению в начало строки."""
        query = self.request.GET.get('name')
        if query:
            return Ingredient.objects.filter(name__istartswith=query)
        return Ingredient.objects.all()


class RecipeViewSet(viewsets.ModelViewSet):
    """Вьюсет рецептов."""

    http_method_names = ('get', 'post', 'patch', 'delete')
    filter_backends = (DjangoFilterBackend, filters.OrderingFilter)
    filterset_class = RecipeFilter
    queryset = Recipe.objects.all()

    def get_permissions(self):
        """Разрешения."""
        if self.action in {'list', 'retrieve', 'get_link'}:
            self.permission_classes = (AllowAny,)
        elif self.action in {'create',
                             'download_shopping_cart',
                             'favorite',
                             'delete_favorite',
                             'shopping_cart',
                             'delete_shopping_cart'}:
            self.permission_classes = (IsAuthenticated,)
        elif self.action in {'partial_update', 'destroy'}:
            self.permission_classes = (AuthorOnly,)
        else:
            self.permission_classes = (ForbiddenPermission,)
        return super().get_permissions()

    def get_serializer_class(self):
        """Выбор сериализатора."""
        if self.action in {'list', 'retrieve'}:
            return RecipeReadSerializer
        if self.action == 'favorite':
            return FavoriteCreateSerializer
        if self.action == 'shopping_cart':
            return ShoppingCreateSerializer
        return RecipeWriteSerializer

    @action(
        detail=True,
        methods=('post',),
        permission_classes=(IsAuthenticated,)
    )
    def favorite(self, request, pk):
        """Добавление в избранное."""
        recipe = get_object_or_404(Recipe, id=pk)
        serializer = self.get_serializer(recipe,
                                         data={'id': pk},
                                         context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @favorite.mapping.delete
    def delete_favorite(self, request, pk):
        """Удалить из избранного."""
        user = request.user
        recipe = get_object_or_404(Recipe, id=pk)
        if user.favorites.filter(id=pk).exists():
            user.favorites.remove(recipe)
            return Response(status=204)
        return Response(status=404)

    def convert_to_txt(self, recipes):
        """Конвертация в TXT."""
        if not recipes:
            return 'Нет рецептов в списке покупок.'
        ingredients = {}
        for recipe in recipes:
            for recipe_ingredient in recipe.ingredients.through.objects.all():
                ingredient = recipe_ingredient.ingredient
                name = ingredient.name
                amount = recipe_ingredient.amount
                unit = ingredient.measurement_unit
                if name not in ingredients:
                    ingredients[name] = {}
                    ingredients[name][unit] = amount
                else:
                    if unit not in ingredients[name]:
                        ingredients[name][unit] = amount
                    elif unit == 'г' and 'кг' in ingredients[name]:
                        ingredients[name]['кг'] += amount / 1000
                    elif unit == 'кг' and 'г' in ingredients[name]:
                        ingredients[name]['г'] += amount * 1000
                    elif unit == 'л' and 'мл' in ingredients[name]:
                        ingredients[name]['мл'] += amount * 1000
                    elif unit == 'мл' and 'л' in ingredients[name]:
                        ingredients[name]['л'] += amount / 1000
                    else:
                        ingredients[name][unit] += amount
        if not ingredients:
            return 'Нет ингредиентов для покупки.'
        ingredients = dict(sorted(ingredients.items()))
        txt = ['Список покупок.\n\n']
        for name, units in ingredients.items():
            if len(units) == 1:
                unit, amount = next(iter(units.items()))
                txt.append(f'{name} ({unit}) — {amount}\n')
            else:
                txt.append(f'{name}:\n')
                for unit, amount in units.items():
                    txt.append(f'  {unit} — {amount}\n')
        return ''.join(txt)

    @action(
        detail=False,
        methods=('get',),
        permission_classes=(IsAuthenticated,)
    )
    def download_shopping_cart(self, request):
        """Получение списка покупок в формате PDF."""
        user = request.user
        recipes = user.shopping_cart.all()
        txt = self.convert_to_txt(recipes)
        return FileResponse(txt, as_attachment=True,
                            filename='Список покупок.txt')

    @action(
        detail=True,
        methods=('post',),
        permission_classes=(IsAuthenticated,)
    )
    def shopping_cart(self, request, pk):
        """Добавление рецепта в список покупок."""
        recipe = get_object_or_404(Recipe, id=pk)
        serializer = self.get_serializer(recipe,
                                         data={'id': pk},
                                         context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @shopping_cart.mapping.delete
    def delete_shopping_cart(self, request, pk):
        """Удаление из списка покупок."""
        user = request.user
        recipe = get_object_or_404(Recipe, id=pk)
        if user.shopping_cart.filter(id=pk).exists():
            user.shopping_cart.remove(recipe)
            return Response(status=204)
        return Response(status=404)

    @action(
        detail=True,
        methods=('get',),
        permission_classes=(AllowAny,),
        url_path='get-link',
        url_name='get_link',
    )
    def get_link(self, request, pk):
        """Получение короткой ссылки."""
        recipe = get_object_or_404(Recipe, id=pk)
        return Response({
            'short-link':
            f'{settings.CURRENT_HOST}/api/s/{recipe.short_url}',
        })


class UserViewSet(viewsets.ModelViewSet):
    """Вьюсет пользователей."""

    http_method_names = ('get', 'post', 'put', 'delete')
    permission_classes = (AllowAny,)

    def get_queryset(self):
        """Получение списка пользователей."""
        query = self.request.GET.get('limit')
        if query:
            return User.objects.all()[:int(query)]
        return User.objects.all()

    @action(
        detail=False,
        methods=('put',),
        permission_classes=(IsAuthenticated,),
        url_path='me/avatar',
        url_name='user_avatar',
    )
    def put_user_avatar(self, request):
        """Изменение аватара."""
        user = request.user
        serializer = self.get_serializer(user, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @put_user_avatar.mapping.delete
    def delete_user_avatar(self, request):
        """Удаление аватара."""
        user = request.user
        user.avatar.delete()
        user.avatar = settings.DEFAULT_AVATAR
        user.save()
        return Response(status=204)

    @action(
        detail=False,
        methods=('get',),
        permission_classes=(IsAuthenticated,)
    )
    def me(self, request):
        """Страница пользователя."""
        user = request.user
        serializer = self.get_serializer(user)
        return Response(serializer.data)

    @action(
        detail=False,
        methods=('post',),
        permission_classes=(IsAuthenticated,)
    )
    def set_password(self, request):
        """Установка пароля."""
        user = request.user
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        password = serializer.validated_data['new_password']
        user.set_password(password)
        user.save()
        return Response(status=204)

    def get_serializer_class(self):
        """Выбор сериализатора."""
        if self.action in {'me', 'list', 'retrieve'}:
            return UserReadSerializer
        if self.action == 'set_password':
            return PasswordSerializer
        if self.action == 'subscribe':
            return SubscriptionCreateSerializer
        if self.action == 'put_user_avatar':
            return AvatarSerializer
        if self.action == 'delete_user_avatar':
            return None
        if self.action == 'subscriptions':
            return SubscriptionSerializer
        return UserWriteSerializer

    @action(
        detail=True,
        methods=('post',),
        permission_classes=(IsAuthenticated,)
    )
    def subscribe(self, request, pk):
        """Подписка."""
        user = request.user
        serializer = self.get_serializer(user,
                                         data={'id': pk},
                                         context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @subscribe.mapping.delete
    def delete_subscribe(self, request, pk):
        """Удалить из подписок."""
        user = request.user
        subscription = get_object_or_404(User, id=pk)
        if user.subscriptions.filter(id=pk).exists():
            user.subscriptions.remove(subscription)
            return Response(status=204)
        return Response(status=404)

    def get_permissions(self):
        if self.action in {'partial_update', 'destroy'}:
            self.permission_classes = (ForbiddenPermission,)
        return super().get_permissions()

    @action(
        detail=False,
        methods=('get',),
        permission_classes=(IsAuthenticated,)
    )
    def subscriptions(self, request):
        """Список подписок."""
        serializer = self.get_serializer(self.get_subscriptions_queryset(),
                                         many=True,
                                         context={'request': request})
        return Response(serializer.data)

    def get_subscriptions_queryset(self):
        """Подписки."""
        user = self.request.user
        queryset = user.subscriptions.all()
        query = self.request.GET.get('limit')
        if query:
            queryset = queryset[:int(query)]
        return queryset


class ShortLinkView(APIView):
    """Класс коротких ссылок."""

    permission_classes = (AllowAny,)

    def get(self, request, short_link):
        """Получение рецепта по короткой ссылке."""
        recipe = get_object_or_404(Recipe, short_url=short_link)
        serializer = RecipeReadSerializer(recipe,
                                          context={'request': request})
        return Response(serializer.data)


class LoadDataView(APIView):
    """Класс загрузки данных."""

    permission_classes = (AllowAny,)

    def get(self, request):
        """Загрузка данных."""
        # with open('data/ingredients.json', 'r', encoding='utf-8') as file:
        #     ingredients = json.load(file)
        #     for ingredient in ingredients:
        #         Ingredient.objects.get_or_create(
        #             name=ingredient['name'],
        #             measurement_unit=ingredient['measurement_unit']
        #         )

        with open('data/tags.json', 'r', encoding='utf-8') as file:
            tags = json.load(file)
            for tag in tags:
                Tag.objects.get_or_create(
                    name=tag['name'],
                    slug=tag['slug']
                )
        return Response(status=204)
