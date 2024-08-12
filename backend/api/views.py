"""Контроллеры."""

from rest_framework.permissions import (AllowAny,  # type: ignore
                                        IsAuthenticated)
from rest_framework import viewsets  # type: ignore
from django.contrib.auth import get_user_model  # type: ignore
from rest_framework.decorators import action  # type: ignore
from rest_framework.response import Response  # type: ignore

from recipes.models import Tag, Recipe, Ingredient
from .serializers import (TagSerializer, RecipeWriteSerializer,
                          RecipeReadSerializer, IngredientSerializer,
                          UserReadSerializer, UserWriteSerializer,
                          PasswordSerializer, FavoriteSerializer,
                          SubscriptionSerializer, ShoppingSerializer)
from .permissions import AuthorOnly, ForbiddenPermission


User = get_user_model()


class BaseReadOnlyViewset(viewsets.ReadOnlyModelViewSet):
    """Базовый вьюсет для чтения."""

    permission_classes = (AllowAny,)
    pagination_class = None


class TagViewSet(BaseReadOnlyViewset):
    """Вьюсет тегов."""

    queryset = Tag.objects.all()
    serializer_class = TagSerializer


class IngredientViewSet(BaseReadOnlyViewset):
    """Вьюсет ингредиентов."""

    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    search_fields = ('^name',)


class RecipeViewSet(viewsets.ModelViewSet):
    """Вьюсет рецептов."""

    http_method_names = ('get', 'post', 'patch', 'delete')
    queryset = Recipe.objects.all()

    def get_permissions(self):
        """Разрешения."""
        if self.action in {'list', 'retrieve'}:
            self.permission_classes = (AllowAny,)
        elif self.action == 'create':
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
            return FavoriteSerializer
        if self.action == 'shopping_cart':
            return ShoppingSerializer
        return RecipeWriteSerializer

    @action(
        detail=True,
        methods=('post',),
        permission_classes=(IsAuthenticated,)
    )
    def favorite(self, request):
        """Добавление в избранное."""
        serializer = self.get_serializer()
        serializer.save()
        return Response(serializer.data)

    @favorite.mapping.delete
    def delete_favorite(self, request):
        """Удалить из избранного."""
        user = request.user
        favorite_recipes = user.favorites.filter(recipe=self.get_object())
        if favorite_recipes.exists():
            for recipe in favorite_recipes:
                recipe.delete()
            return Response(status=204)
        return Response(status=404)

    @action(
        detail=False,
        methods=('get',),
        permission_classes=(IsAuthenticated,)
    )
    def download_shopping_cart(self, request):
        """Получение списка покупок в формате TXT."""
        # serializer = self.get_serializer()
        # serializer.save()
        # return Response(serializer.data)

    @action(
        detail=True,
        methods=('post',),
        permission_classes=(IsAuthenticated,)
    )
    def shopping_cart(self, request):
        """Добавление рецепта в список покупок."""
        user = request.user
        serializer = self.get_serializer(user, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @shopping_cart.mapping.delete
    def delete_shopping_cart(self, request):
        """Удаление из списка покупок."""
        user = request.user
        shopping_cart = user.shopping_cart.filter(recipe=self.get_object())
        if shopping_cart.exists():
            for shopping_recipe in shopping_cart:
                shopping_recipe.delete()
            return Response(status=204)
        return Response(status=404)


class UserViewSet(viewsets.ModelViewSet):
    """Вьюсет пользователей."""

    http_method_names = ('get', 'post')
    queryset = User.objects.all()
    permission_classes = (AllowAny,)

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
        serializer = self.get_serializer(user, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def get_serializer_class(self):
        """Выбор сериализатора."""
        if self.action in {'me', 'list', 'retrieve'}:
            return UserReadSerializer
        if self.action == 'set_password':
            return PasswordSerializer
        if self.action == 'subscribe':
            return SubscriptionSerializer
        return UserWriteSerializer
    
    @action(
        detail=True,
        methods=('post',),
        permission_classes=(IsAuthenticated,)
    )
    def subscribe(self, request):
        """Подписка."""
        user = request.user
        serializer = self.get_serializer(user, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @subscribe.mapping.delete
    def delete_subscribe(self, request):
        """Удалить из подписок."""
        user = request.user
        subscriptions = user.subscriptions.filter(id=request.data['id'])
        if subscriptions.exists():
            for subscription in subscriptions:
                subscription.delete()
            return Response(status=204)
        return Response(status=404)


class SubscriptionViewSet(viewsets.ReadOnlyModelViewSet):
    """Вьюсет подписок."""

    sserializer_class = SubscriptionSerializer

    def get_permissions(self):
        """Разрешения."""
        if self.action == 'list':
            self.permission_classes = (AllowAny,)
        else:
            self.permission_classes = (ForbiddenPermission,)
        return super().get_permissions()

    def get_queryset(self):
        """Подписки."""
        user = self.request.user
        return user.subscriptions.all()
