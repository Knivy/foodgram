"""Контроллеры."""

import json

from rest_framework.permissions import (AllowAny,  # type: ignore
                                        IsAuthenticated)
from rest_framework import filters, viewsets, status  # type: ignore
from django.contrib.auth import get_user_model  # type: ignore
from rest_framework.decorators import action  # type: ignore
from rest_framework.response import Response  # type: ignore
from django.shortcuts import get_object_or_404  # type: ignore
from django.conf import settings  # type: ignore
from rest_framework.views import APIView  # type: ignore
from django.http import FileResponse, HttpResponse  # type: ignore
from django_filters.rest_framework import DjangoFilterBackend  # type: ignore
from django.db.models import (Case, When, BooleanField,  # type: ignore
                              Value, Sum)
from rest_framework.exceptions import NotFound  # type: ignore
from django.shortcuts import redirect  # type: ignore

from recipes.models import Tag, Recipe, Ingredient, RecipeIngredient
from users.models import Favorite, Subscription, ShoppingCart
from .serializers import (TagSerializer, RecipeWriteSerializer,
                          RecipeReadSerializer, IngredientSerializer,
                          UserReadSerializer, UserWriteSerializer,
                          PasswordSerializer, FavoriteCreateSerializer,
                          SubscriptionSerializer, ShoppingCreateSerializer,
                          AvatarSerializer, SubscriptionCreateSerializer)
from .permissions import AuthorOnly, ForbiddenPermission
from .filters import RecipeFilter
from .drf_cache import CacheResponseMixin

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
        query = self.request.query_params.get('name')
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

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if not user.is_authenticated:
            return queryset.annotate(
                is_favorited=Value(False),
                is_in_shopping_cart=Value(False),
            )
        return queryset.annotate(
            is_favorited=Case(
                When(favorites__in=(user,), then=True),
                default=False,
                output_field=BooleanField()
            ),
            is_in_shopping_cart=Case(
                When(shopping_cart__in=(user,), then=True),
                default=False,
                output_field=BooleanField()
            ),
        )

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
        favorite = get_object_or_404(Favorite, user=user, recipe__id=pk)
        favorite.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def convert_to_txt(self, recipes):
        """Конвертация в TXT."""
        if not recipes:
            return 'Нет рецептов в списке покупок.'
        recipe_ingredients = (RecipeIngredient.objects.
                              filter(recipe__in=recipes))
        ingredients = recipe_ingredients.values(
            'ingredient__name',
            'ingredient__measurement_unit').annotate(
            total_amount=Sum('amount'),
            ).order_by('ingredient__name')
        if not ingredients.exists():
            return 'Нет ингредиентов для покупки.'
        txt = ['Список покупок.\n\n']  # Дальше список изменяем.
        for ingredient in ingredients:
            name = ingredient.get('ingredient__name')
            unit = ingredient.get('ingredient__measurement_unit')
            amount = ingredient.get('total_amount')
            txt.append(f'{name}:  {unit} — {amount}\n')
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
        response = HttpResponse(txt, content_type='text/plain; charset=UTF-8')
        response['Content-Disposition'] = ('attachment; '
                                           'filename="shopping-list.txt"')
        return response

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
        shopping = get_object_or_404(ShoppingCart,
                                     user=user,
                                     recipe__id=pk)
        shopping.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=('get',),
        permission_classes=(AllowAny,),
        url_path='get-link',
        url_name='get_link',
    )
    def get_link(self, request, pk):
        """Получение короткой ссылки."""
        self.lookup_field = 'pk'
        recipe = self.get_object()
        return Response({
            'short-link':
            (f'{settings.CURRENT_HOST}:{settings.CURRENT_PORT}'
             f'/api/s/{recipe.short_url}'),
        })


class UserViewSet(viewsets.ModelViewSet):
    """Вьюсет пользователей."""

    http_method_names = ('get', 'post', 'put', 'delete')
    permission_classes = (AllowAny,)
    filter_backends = (DjangoFilterBackend, filters.OrderingFilter)
    queryset = User.objects.all()

    def get_queryset(self):
        """Получение списка пользователей."""
        queryset = super().get_queryset()
        query = self.request.query_params.get('limit')
        if query:
            queryset = queryset[:int(query)]
        return queryset

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
        return Response(status=status.HTTP_204_NO_CONTENT)

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
        return Response(status=status.HTTP_204_NO_CONTENT)

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
        subscription = get_object_or_404(Subscription,
                                         author__id=pk,
                                         user=user)
        subscription.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

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
        user = request.user
        queryset = User.objects.filter(user=user)
        if not queryset.exists() or not queryset:
            return Response([], status=status.HTTP_200_OK)
        query = self.request.query_params.get('limit')
        if query:
            queryset = queryset[:int(query)]
        pages = self.paginate_queryset(queryset)
        serializer = self.get_serializer(pages,
                                         many=True,
                                         context={'request': request})
        return self.get_paginated_response(serializer.data)


class ShortLinkView(APIView):
    """Класс коротких ссылок."""

    permission_classes = (AllowAny,)

    def get(self, request, short_link):
        """Получение рецепта по короткой ссылке."""
        recipe = get_object_or_404(Recipe, short_url=short_link)
        return redirect(f'/api/recipes/{recipe.id}')


class LoadDataView(APIView):
    """Класс загрузки данных."""

    permission_classes = (AllowAny,)

    def get(self, request):
        """Загрузка данных."""
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
        return Response(status=status.HTTP_204_NO_CONTENT)
